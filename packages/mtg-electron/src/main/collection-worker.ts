/**
 * Worker thread for collection database queries.
 * Runs SQLite synchronously in a separate thread to avoid blocking main process.
 */
import { parentPort } from "worker_threads";
import Database from "better-sqlite3";
import { homedir } from "os";
import { join } from "path";
import { existsSync } from "fs";

// Database paths - all databases now live in ~/.mtg-spellbook/
const MTG_SPELLBOOK_DIR = join(homedir(), ".mtg-spellbook");
const USER_DB_PATH = join(MTG_SPELLBOOK_DIR, "user_data.sqlite");
const MTG_DB_PATH = join(MTG_SPELLBOOK_DIR, "mtg.sqlite");

function getMtgDbPath(): string {
  return MTG_DB_PATH;
}

let userDb: Database.Database | null = null;
let userDbWritable: Database.Database | null = null;
let mtgDb: Database.Database | null = null;

// Cache for card metadata (colors, type, rarity, etc.) - keyed by lowercase name
let cardDataCache: Map<
  string,
  {
    colors: string;
    type_line: string;
    rarity: string;
    cmc: number;
    keywords: string;
    artist: string;
  }
> | null = null;

// Cache for exact printing prices - keyed by "name|SET_CODE|collector_number"
let cardPriceCache: Map<
  string,
  {
    price_usd: number | null;
    price_usd_foil: number | null;
  }
> | null = null;

// Generate composite key for price lookup
function priceKey(
  cardName: string,
  setCode: string | null,
  collectorNumber: string | null,
): string {
  const name = cardName.toLowerCase();
  const set = setCode?.toUpperCase() || "";
  const num = collectorNumber || "";
  return `${name}|${set}|${num}`;
}

// Get price for exact printing, with fallback to any printing of same card
function getCardPrice(
  cardName: string,
  setCode: string | null,
  collectorNumber: string | null,
): { price_usd: number | null; price_usd_foil: number | null } {
  if (!cardPriceCache) return { price_usd: null, price_usd_foil: null };

  // Try exact match first
  const exactKey = priceKey(cardName, setCode, collectorNumber);
  const exactPrice = cardPriceCache.get(exactKey);
  if (exactPrice) return exactPrice;

  // Fallback: search for any printing of this card (for cards without set/collector info)
  const namePrefix = cardName.toLowerCase() + "|";
  for (const [key, price] of cardPriceCache) {
    if (key.startsWith(namePrefix) && price.price_usd !== null) {
      return price;
    }
  }

  return { price_usd: null, price_usd_foil: null };
}

// NOTE: Price history schema is now created via the mtg-core API
// Call POST /setup/ensure-price-history on app startup before using price features

function initDatabases(): boolean {
  if (userDb && mtgDb) return true;

  if (!existsSync(USER_DB_PATH)) {
    return false;
  }

  const mtgPath = getMtgDbPath();
  if (!existsSync(mtgPath)) {
    return false;
  }

  userDb = new Database(USER_DB_PATH, { readonly: true });
  mtgDb = new Database(mtgPath, { readonly: true });

  return true;
}

function getWritableUserDb(): Database.Database {
  if (!userDbWritable) {
    userDbWritable = new Database(USER_DB_PATH, { readonly: false });
    // Run one-time migration to fix value history data that was 100x too large
    // (prices were in cents but treated as dollars)
    runValueHistoryMigration(userDbWritable);
  }
  return userDbWritable;
}

// One-time migration to rebuild collection_value_history from card data
function runValueHistoryMigration(db: Database.Database): void {
  // Use v2 to force re-run with exact printing prices
  const MIGRATION_KEY = "value_history_rebuild_v2";

  // Ensure meta table exists
  db.exec(`
    CREATE TABLE IF NOT EXISTS collection_meta (
      key TEXT PRIMARY KEY,
      value TEXT
    )
  `);

  // Check if migration already ran
  const result = db
    .prepare(`SELECT value FROM collection_meta WHERE key = ? LIMIT 1`)
    .get(MIGRATION_KEY) as { value: string } | undefined;

  if (result) {
    return; // Already migrated
  }

  // Rebuild value history from collection cards by date added
  try {
    // Need mtgDb for prices
    if (!mtgDb) {
      console.log("MTG DB not available, skipping value history rebuild");
      return;
    }

    // Build price cache if not already built
    buildCardCache();

    if (!cardPriceCache) {
      console.log("Price cache not available, skipping value history rebuild");
      return;
    }

    // Get all collection cards with their added dates (include set/collector for exact pricing)
    const cards = db
      .prepare(
        `SELECT card_name, quantity, foil_quantity, set_code, collector_number, added_at
         FROM collection_cards
         ORDER BY added_at ASC`,
      )
      .all() as Array<{
      card_name: string;
      quantity: number;
      foil_quantity: number;
      set_code: string | null;
      collector_number: string | null;
      added_at: string;
    }>;

    if (cards.length === 0) {
      console.log("No collection cards, skipping value history rebuild");
      return;
    }

    // Group cards by date and calculate cumulative value
    const valueByDate = new Map<string, { value: number; count: number }>();
    let cumulativeValue = 0;
    let cumulativeCount = 0;

    for (const card of cards) {
      const date = card.added_at.split("T")[0]; // Get just the date part
      const cardPrice = getCardPrice(
        card.card_name,
        card.set_code,
        card.collector_number,
      );

      // Prices are in cents, convert to dollars
      if (cardPrice.price_usd) {
        cumulativeValue += (cardPrice.price_usd / 100) * card.quantity;
      }
      if (card.foil_quantity > 0) {
        const foilPrice = cardPrice.price_usd_foil ?? cardPrice.price_usd;
        if (foilPrice) {
          cumulativeValue += (foilPrice / 100) * card.foil_quantity;
        }
      }
      cumulativeCount += card.quantity + card.foil_quantity;

      // Update the running total for this date
      valueByDate.set(date, { value: cumulativeValue, count: cumulativeCount });
    }

    // Clear existing history and insert rebuilt data
    db.exec(`DELETE FROM collection_value_history`);

    const insertStmt = db.prepare(
      `INSERT INTO collection_value_history (recorded_at, total_value, card_count) VALUES (?, ?, ?)`,
    );

    for (const [date, data] of valueByDate) {
      insertStmt.run(date, data.value, data.count);
    }

    // Mark migration as complete
    db.prepare(
      `INSERT OR REPLACE INTO collection_meta (key, value) VALUES (?, ?)`,
    ).run(MIGRATION_KEY, new Date().toISOString());

    console.log(
      `Rebuilt collection_value_history: ${valueByDate.size} dates, final value $${cumulativeValue.toFixed(2)}`,
    );
  } catch (err) {
    console.error("Failed to rebuild collection_value_history:", err);
  }
}

function buildCardCache(): void {
  if (!mtgDb) return;

  // Build metadata cache (one entry per card name)
  if (!cardDataCache) {
    const metaRows = mtgDb
      .prepare(
        `
      SELECT
        LOWER(name) as name_lower,
        COALESCE(colors, '') as colors,
        COALESCE(type_line, '') as type_line,
        COALESCE(rarity, 'common') as rarity,
        COALESCE(cmc, 0) as cmc,
        COALESCE(keywords, '') as keywords,
        COALESCE(artist, '') as artist
      FROM cards
      WHERE is_token = 0 OR is_token IS NULL
      GROUP BY LOWER(name)
    `,
      )
      .all() as Array<{
      name_lower: string;
      colors: string;
      type_line: string;
      rarity: string;
      cmc: number;
      keywords: string;
      artist: string;
    }>;

    cardDataCache = new Map();
    for (const row of metaRows) {
      cardDataCache.set(row.name_lower, {
        colors: row.colors,
        type_line: row.type_line,
        rarity: row.rarity,
        cmc: row.cmc,
        keywords: row.keywords,
        artist: row.artist,
      });
    }
  }

  // Build price cache (one entry per printing: name + set + collector_number)
  if (!cardPriceCache) {
    const priceRows = mtgDb
      .prepare(
        `
      SELECT
        LOWER(name) as name_lower,
        UPPER(set_code) as set_code,
        collector_number,
        price_usd,
        price_usd_foil
      FROM cards
      WHERE (is_token = 0 OR is_token IS NULL)
        AND set_code IS NOT NULL
        AND collector_number IS NOT NULL
    `,
      )
      .all() as Array<{
      name_lower: string;
      set_code: string;
      collector_number: string;
      price_usd: number | null;
      price_usd_foil: number | null;
    }>;

    cardPriceCache = new Map();
    for (const row of priceRows) {
      const key = `${row.name_lower}|${row.set_code}|${row.collector_number}`;
      cardPriceCache.set(key, {
        price_usd: row.price_usd,
        price_usd_foil: row.price_usd_foil,
      });
    }
  }
}

// Cache for set code -> set name mappings
let setNameCache: Map<string, string> | null = null;

function buildSetNameCache(): void {
  if (setNameCache || !mtgDb) return;

  const rows = mtgDb
    .prepare(
      `
      SELECT DISTINCT
        UPPER(set_code) as set_code,
        set_name
      FROM cards
      WHERE set_code IS NOT NULL AND set_name IS NOT NULL
    `,
    )
    .all() as Array<{ set_code: string; set_name: string }>;

  setNameCache = new Map();
  for (const row of rows) {
    setNameCache.set(row.set_code, row.set_name);
  }
}

function getCollectionList(limit: number, offset: number) {
  if (!userDb)
    return { cards: [], stats: { unique: 0, total: 0, foils: 0 }, total: 0 };

  // Build caches if needed
  buildCardCache();
  buildSetNameCache();

  const cards = userDb
    .prepare(
      `
      SELECT card_name, quantity, foil_quantity, set_code, collector_number, added_at
      FROM collection_cards
      ORDER BY added_at DESC
      LIMIT ? OFFSET ?
    `,
    )
    .all(limit, offset) as Array<{
    card_name: string;
    quantity: number;
    foil_quantity: number;
    set_code: string | null;
    collector_number: string | null;
    added_at: string;
  }>;

  const statsRow = userDb
    .prepare(
      `
      SELECT
        COUNT(*) as unique_count,
        COALESCE(SUM(quantity + foil_quantity), 0) as total_count,
        COALESCE(SUM(foil_quantity), 0) as foil_count
      FROM collection_cards
    `,
    )
    .get() as { unique_count: number; total_count: number; foil_count: number };

  return {
    cards: cards.map((c) => {
      // Enrich with card data from cache
      const cardData = cardDataCache?.get(c.card_name.toLowerCase());
      const setCode = c.set_code?.toUpperCase() || null;
      const setName = setCode ? setNameCache?.get(setCode) : null;
      const cardPrice = getCardPrice(
        c.card_name,
        c.set_code,
        c.collector_number,
      );

      // Parse colors from comma-separated string
      const colors = cardData?.colors
        ? cardData.colors.split(",").filter((x) => x)
        : [];

      return {
        cardName: c.card_name,
        quantity: c.quantity,
        foilQuantity: c.foil_quantity,
        setCode: setCode,
        setName: setName || null,
        collectorNumber: c.collector_number,
        addedAt: c.added_at,
        // Enriched data from card database
        colors: colors,
        typeLine: cardData?.type_line || null,
        rarity: cardData?.rarity || null,
        cmc: cardData?.cmc || 0,
        priceUsd: cardPrice.price_usd,
        priceUsdFoil: cardPrice.price_usd_foil,
      };
    }),
    stats: {
      unique: statsRow.unique_count,
      total: statsRow.total_count,
      foils: statsRow.foil_count,
    },
    total: statsRow.unique_count,
  };
}

function getCollectionStats() {
  if (!userDb) {
    return {
      unique: 0,
      total: 0,
      foils: 0,
      colors: {},
      types: {},
      rarities: {},
      manaCurve: {},
      topSets: [],
      avgCmc: 0,
      topKeywords: [],
      topArtists: [],
      legendaries: { creatures: 0, other: 0, total: 0 },
    };
  }

  buildCardCache();

  const basicStats = userDb
    .prepare(
      `
      SELECT
        COUNT(*) as unique_count,
        COALESCE(SUM(quantity + foil_quantity), 0) as total_count,
        COALESCE(SUM(foil_quantity), 0) as foil_count
      FROM collection_cards
    `,
    )
    .get() as { unique_count: number; total_count: number; foil_count: number };

  const collectionCards = userDb
    .prepare(
      `SELECT card_name, quantity + foil_quantity as total_qty, set_code FROM collection_cards`,
    )
    .all() as Array<{
    card_name: string;
    total_qty: number;
    set_code: string | null;
  }>;

  const colors: Record<string, number> = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 };
  const types: Record<string, number> = {};
  const rarities: Record<string, number> = {};
  const manaCurve: Record<number, number> = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
  };
  const setCounts: Record<string, number> = {};
  const keywordCounts: Record<string, number> = {};
  const artistCounts: Record<string, number> = {};
  let totalCmc = 0;
  let nonLandCount = 0;
  let legendaryCreatures = 0;
  let legendaryOther = 0;

  for (const row of collectionCards) {
    const qty = row.total_qty;
    const cardData = cardDataCache?.get(row.card_name.toLowerCase());
    if (!cardData) continue;

    const colorList = cardData.colors
      .replace(/[\[\]"]/g, "")
      .split(",")
      .filter(Boolean);
    if (colorList.length > 0) {
      for (const c of colorList) {
        const color = c.trim().toUpperCase();
        if (color in colors) colors[color] += qty;
      }
    } else {
      colors.C += qty;
    }

    const typeLine = cardData.type_line.toLowerCase();
    let cardType = "Other";
    for (const t of [
      "creature",
      "instant",
      "sorcery",
      "artifact",
      "enchantment",
      "planeswalker",
      "land",
    ]) {
      if (typeLine.includes(t)) {
        cardType = t.charAt(0).toUpperCase() + t.slice(1);
        break;
      }
    }
    types[cardType] = (types[cardType] || 0) + qty;

    const rarity =
      cardData.rarity.charAt(0).toUpperCase() + cardData.rarity.slice(1);
    rarities[rarity] = (rarities[rarity] || 0) + qty;

    if (!typeLine.includes("land")) {
      const cmcKey = Math.min(Math.floor(cardData.cmc), 7);
      manaCurve[cmcKey] = (manaCurve[cmcKey] || 0) + qty;
      totalCmc += cardData.cmc * qty;
      nonLandCount += qty;
    }

    if (row.set_code) {
      setCounts[row.set_code] = (setCounts[row.set_code] || 0) + qty;
    }

    // Keywords
    if (cardData.keywords) {
      const keywords = cardData.keywords
        .replace(/[\[\]"]/g, "")
        .split(",")
        .filter(Boolean);
      for (const kw of keywords) {
        const keyword = kw.trim();
        if (keyword) {
          keywordCounts[keyword] = (keywordCounts[keyword] || 0) + qty;
        }
      }
    }

    // Artists
    if (cardData.artist) {
      artistCounts[cardData.artist] =
        (artistCounts[cardData.artist] || 0) + qty;
    }

    // Legendaries - detect from type_line (e.g., "Legendary Creature — Human Wizard")
    if (typeLine.includes("legendary")) {
      if (typeLine.includes("creature")) {
        legendaryCreatures += qty;
      } else {
        legendaryOther += qty;
      }
    }
  }

  const topSets = Object.entries(setCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([code, count]) => ({ code, count }));

  const topKeywords = Object.entries(keywordCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([keyword, count]) => ({ keyword, count }));

  const topArtists = Object.entries(artistCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([artist, count]) => ({ artist, count }));

  return {
    unique: basicStats.unique_count,
    total: basicStats.total_count,
    foils: basicStats.foil_count,
    colors,
    types,
    rarities,
    manaCurve,
    topSets,
    avgCmc:
      nonLandCount > 0 ? Math.round((totalCmc / nonLandCount) * 100) / 100 : 0,
    topKeywords,
    topArtists,
    legendaries: {
      creatures: legendaryCreatures,
      other: legendaryOther,
      total: legendaryCreatures + legendaryOther,
    },
  };
}

function getCollectionValue() {
  if (!userDb) return { totalValue: 0, mostValuable: [] };

  buildCardCache();

  const rows = userDb
    .prepare(
      `SELECT card_name, quantity, foil_quantity, set_code, collector_number FROM collection_cards`,
    )
    .all() as Array<{
    card_name: string;
    quantity: number;
    foil_quantity: number;
    set_code: string | null;
    collector_number: string | null;
  }>;

  let totalValue = 0;
  const cardValues: Array<{
    cardName: string;
    value: number;
    setCode: string | null;
    collectorNumber: string | null;
  }> = [];

  for (const row of rows) {
    const cardPrice = getCardPrice(
      row.card_name,
      row.set_code,
      row.collector_number,
    );

    const usdPrice = cardPrice.price_usd ? cardPrice.price_usd / 100 : null;
    const foilPrice = cardPrice.price_usd_foil
      ? cardPrice.price_usd_foil / 100
      : null;

    let cardValue = 0;
    if (usdPrice && row.quantity > 0) cardValue += usdPrice * row.quantity;
    if (row.foil_quantity > 0) {
      const foil = foilPrice ?? usdPrice;
      if (foil) cardValue += foil * row.foil_quantity;
    }

    if (cardValue > 0) {
      totalValue += cardValue;
      cardValues.push({
        cardName: row.card_name,
        value: Math.round(cardValue * 100) / 100,
        setCode: row.set_code,
        collectorNumber: row.collector_number,
      });
    }
  }

  cardValues.sort((a, b) => b.value - a.value);

  return {
    totalValue: Math.round(totalValue * 100) / 100,
    mostValuable: cardValues.slice(0, 15),
  };
}

interface UpdateCollectionCardArgs {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
  quantity: number;
  foilQuantity: number;
}

function updateCollectionCard(args: UpdateCollectionCardArgs): {
  success: boolean;
  card?: ReturnType<typeof getCollectionList>["cards"][0];
} {
  const db = getWritableUserDb();

  // Use fully parameterized queries - no string interpolation
  // Two separate prepared statements based on identifier type
  let result: Database.RunResult;
  let card:
    | {
        card_name: string;
        quantity: number;
        foil_quantity: number;
        set_code: string | null;
        collector_number: string | null;
        added_at: string;
      }
    | undefined;

  if (args.setCode && args.collectorNumber) {
    // Update with set_code and collector_number
    const updateStmt = db.prepare(`
      UPDATE collection_cards
      SET quantity = ?, foil_quantity = ?
      WHERE card_name = ? AND set_code = ? AND collector_number = ?
    `);
    result = updateStmt.run(
      args.quantity,
      args.foilQuantity,
      args.cardName,
      args.setCode,
      args.collectorNumber,
    );

    if (result.changes > 0) {
      const selectStmt = db.prepare(`
        SELECT card_name, quantity, foil_quantity, set_code, collector_number, added_at
        FROM collection_cards
        WHERE card_name = ? AND set_code = ? AND collector_number = ?
      `);
      card = selectStmt.get(
        args.cardName,
        args.setCode,
        args.collectorNumber,
      ) as typeof card;
    }
  } else {
    // Update by card_name only
    const updateStmt = db.prepare(`
      UPDATE collection_cards
      SET quantity = ?, foil_quantity = ?
      WHERE card_name = ?
    `);
    result = updateStmt.run(args.quantity, args.foilQuantity, args.cardName);

    if (result.changes > 0) {
      const selectStmt = db.prepare(`
        SELECT card_name, quantity, foil_quantity, set_code, collector_number, added_at
        FROM collection_cards
        WHERE card_name = ?
      `);
      card = selectStmt.get(args.cardName) as typeof card;
    }
  }

  if (result.changes > 0 && card) {
    // Enrich with card data from cache
    buildCardCache();
    buildSetNameCache();
    const cardData = cardDataCache?.get(card.card_name.toLowerCase());
    const cardPrice = getCardPrice(
      card.card_name,
      card.set_code,
      card.collector_number,
    );
    const setCode = card.set_code?.toUpperCase() || null;
    const setName = setCode ? setNameCache?.get(setCode) : null;
    const colors = cardData?.colors
      ? cardData.colors.split(",").filter((x) => x)
      : [];

    return {
      success: true,
      card: {
        cardName: card.card_name,
        quantity: card.quantity,
        foilQuantity: card.foil_quantity,
        setCode: setCode,
        setName: setName || null,
        collectorNumber: card.collector_number,
        addedAt: card.added_at,
        colors: colors,
        typeLine: cardData?.type_line || null,
        rarity: cardData?.rarity || null,
        cmc: cardData?.cmc || 0,
        priceUsd: cardPrice.price_usd,
        priceUsdFoil: cardPrice.price_usd_foil,
      },
    };
  }

  return { success: false };
}

interface DeleteCollectionCardArgs {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
}

function deleteCollectionCard(args: DeleteCollectionCardArgs): {
  success: boolean;
} {
  const db = getWritableUserDb();

  // Use fully parameterized queries - no string interpolation
  let result: Database.RunResult;

  if (args.setCode && args.collectorNumber) {
    const stmt = db.prepare(`
      DELETE FROM collection_cards
      WHERE card_name = ? AND set_code = ? AND collector_number = ?
    `);
    result = stmt.run(args.cardName, args.setCode, args.collectorNumber);
  } else {
    const stmt = db.prepare(`
      DELETE FROM collection_cards
      WHERE card_name = ?
    `);
    result = stmt.run(args.cardName);
  }

  return { success: result.changes > 0 };
}

function recordPriceSnapshot(): { success: boolean; cardsRecorded: number } {
  if (!userDb || !mtgDb) {
    return { success: false, cardsRecorded: 0 };
  }

  buildCardCache();
  const db = getWritableUserDb();

  // Get current date as YYYY-MM-DD
  const today = new Date().toISOString().split("T")[0];

  // Get all collection cards
  const collectionCards = userDb
    .prepare(
      `SELECT card_name, quantity, foil_quantity, set_code, collector_number FROM collection_cards`,
    )
    .all() as Array<{
    card_name: string;
    quantity: number;
    foil_quantity: number;
    set_code: string | null;
    collector_number: string | null;
  }>;

  // Prepare insert statement (INSERT OR REPLACE to handle duplicates)
  const insertPrice = db.prepare(`
    INSERT OR REPLACE INTO price_history
    (card_name, set_code, collector_number, price_usd, price_usd_foil, recorded_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  let cardsRecorded = 0;
  let totalValue = 0;

  // Use transaction for bulk insert
  const insertMany = db.transaction(() => {
    for (const card of collectionCards) {
      const cardPrice = getCardPrice(
        card.card_name,
        card.set_code,
        card.collector_number,
      );

      insertPrice.run(
        card.card_name,
        card.set_code,
        card.collector_number,
        cardPrice.price_usd,
        cardPrice.price_usd_foil,
        today,
      );
      cardsRecorded++;

      // Calculate total value for collection history (prices are stored in cents)
      if (cardPrice.price_usd) {
        totalValue += (cardPrice.price_usd / 100) * card.quantity;
      }
      if (card.foil_quantity > 0) {
        const foilPrice = cardPrice.price_usd_foil ?? cardPrice.price_usd;
        if (foilPrice) {
          totalValue += (foilPrice / 100) * card.foil_quantity;
        }
      }
    }

    // Record collection value history
    db.prepare(
      `
      INSERT OR REPLACE INTO collection_value_history
      (total_value, card_count, recorded_at)
      VALUES (?, ?, ?)
    `,
    ).run(totalValue, collectionCards.length, today);
  });

  insertMany();

  return { success: true, cardsRecorded };
}

interface CardPriceHistoryArgs {
  cardName: string;
  setCode?: string;
  collectorNumber?: string;
  days?: number;
}

interface PriceHistoryEntry {
  date: string;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

function getCardPriceHistory(args: CardPriceHistoryArgs): PriceHistoryEntry[] {
  const db = getWritableUserDb();
  const days = args.days ?? 30;

  // Calculate cutoff date
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);
  const cutoffStr = cutoffDate.toISOString().split("T")[0];

  // Use fully parameterized queries - no string interpolation
  let rows: Array<{
    recorded_at: string;
    price_usd: number | null;
    price_usd_foil: number | null;
  }>;

  if (args.setCode && args.collectorNumber) {
    const stmt = db.prepare(`
      SELECT recorded_at, price_usd, price_usd_foil
      FROM price_history
      WHERE card_name = ? AND set_code = ? AND collector_number = ? AND recorded_at >= ?
      ORDER BY recorded_at ASC
    `);
    rows = stmt.all(
      args.cardName,
      args.setCode,
      args.collectorNumber,
      cutoffStr,
    ) as typeof rows;
  } else {
    const stmt = db.prepare(`
      SELECT recorded_at, price_usd, price_usd_foil
      FROM price_history
      WHERE card_name = ? AND recorded_at >= ?
      ORDER BY recorded_at ASC
    `);
    rows = stmt.all(args.cardName, cutoffStr) as typeof rows;
  }

  return rows.map((row) => ({
    date: row.recorded_at,
    priceUsd: row.price_usd,
    priceUsdFoil: row.price_usd_foil,
  }));
}

interface CollectionValueHistoryEntry {
  date: string;
  totalValue: number;
  cardCount: number;
}

function getCollectionValueHistory(
  days?: number,
): CollectionValueHistoryEntry[] {
  const db = getWritableUserDb();
  const numDays = days ?? 30;

  // Calculate cutoff date
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - numDays);
  const cutoffStr = cutoffDate.toISOString().split("T")[0];

  const rows = db
    .prepare(
      `
    SELECT recorded_at, total_value, card_count
    FROM collection_value_history
    WHERE recorded_at >= ?
    ORDER BY recorded_at ASC
  `,
    )
    .all(cutoffStr) as Array<{
    recorded_at: string;
    total_value: number;
    card_count: number;
  }>;

  return rows.map((row) => ({
    date: row.recorded_at,
    totalValue: row.total_value,
    cardCount: row.card_count,
  }));
}

// Handle messages from main thread
parentPort?.on(
  "message",
  (msg: { id: number; type: string; args?: unknown }) => {
    try {
      if (!initDatabases()) {
        parentPort?.postMessage({
          id: msg.id,
          error: "Database not available",
        });
        return;
      }

      let result: unknown;
      switch (msg.type) {
        case "list": {
          const args = msg.args as { limit: number; offset: number };
          result = getCollectionList(args.limit, args.offset);
          break;
        }
        case "stats":
          result = getCollectionStats();
          break;
        case "value":
          result = getCollectionValue();
          break;
        case "update": {
          const args = msg.args as UpdateCollectionCardArgs;
          result = updateCollectionCard(args);
          break;
        }
        case "delete": {
          const args = msg.args as DeleteCollectionCardArgs;
          result = deleteCollectionCard(args);
          break;
        }
        case "recordPrices":
          result = recordPriceSnapshot();
          break;
        case "priceHistory": {
          const args = msg.args as CardPriceHistoryArgs;
          result = getCardPriceHistory(args);
          break;
        }
        case "valueHistory": {
          const args = msg.args as { days?: number };
          result = getCollectionValueHistory(args?.days);
          break;
        }
        default:
          result = { error: `Unknown message type: ${msg.type}` };
      }

      parentPort?.postMessage({ id: msg.id, result });
    } catch (error) {
      parentPort?.postMessage({ id: msg.id, error: String(error) });
    }
  },
);
