/**
 * Collection Import Parser
 *
 * Parses card lists from various formats:
 * - Simple text: "4 Lightning Bolt"
 * - CSV: "quantity,name,set_code,collector_number,foil"
 * - Arena: "4 Lightning Bolt (LEA) 161"
 */

export interface ParsedCard {
  name: string;
  quantity: number;
  set_code?: string;
  collector_number?: string;
  is_foil?: boolean;
}

export interface ParseError {
  line: number;
  text: string;
  error: string;
}

export interface ParseResult {
  cards: ParsedCard[];
  errors: ParseError[];
}

export type ImportFormat = "simple" | "csv" | "arena";

/**
 * Detect the format of the input text.
 */
export function detectFormat(text: string): ImportFormat {
  const lines = text
    .trim()
    .split("\n")
    .filter((line) => line.trim());

  if (lines.length === 0) {
    return "simple";
  }

  // Check for CSV header
  const firstLine = lines[0].toLowerCase();
  if (
    firstLine.includes("quantity") ||
    firstLine.includes("name") ||
    (firstLine.includes(",") && lines.length > 1)
  ) {
    // Verify it looks like CSV data
    const commaCount = (lines[0].match(/,/g) || []).length;
    if (commaCount >= 1) {
      return "csv";
    }
  }

  // Check for Arena format: "4 Card Name (SET) 123"
  const arenaPattern = /^\d+\s+.+\s+\([A-Z0-9]+\)\s+\d+/;
  for (const line of lines.slice(0, 5)) {
    if (arenaPattern.test(line.trim())) {
      return "arena";
    }
  }

  return "simple";
}

/**
 * Parse a simple text format: "4 Lightning Bolt" or "4x Lightning Bolt"
 */
function parseSimpleLine(
  line: string,
  lineNumber: number,
): ParsedCard | ParseError {
  const trimmed = line.trim();

  if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("//")) {
    // Skip empty lines and comments - return as "skip" by returning a card with empty name
    return { name: "", quantity: 0 };
  }

  // Match: "4 Card Name", "4x Card Name", or just "Card Name"
  const match = trimmed.match(/^(\d+)x?\s+(.+)$/i);

  if (match) {
    const quantity = parseInt(match[1], 10);
    const name = match[2].trim();

    if (quantity <= 0 || quantity > 99) {
      return {
        line: lineNumber,
        text: trimmed,
        error: `Invalid quantity: ${quantity}`,
      };
    }

    if (!name) {
      return {
        line: lineNumber,
        text: trimmed,
        error: "Card name is empty",
      };
    }

    return { name, quantity };
  }

  // No quantity specified, assume 1
  if (trimmed.length > 0) {
    return { name: trimmed, quantity: 1 };
  }

  return {
    line: lineNumber,
    text: trimmed,
    error: "Could not parse line",
  };
}

/**
 * Parse Arena format: "4 Lightning Bolt (LEA) 161"
 */
function parseArenaLine(
  line: string,
  lineNumber: number,
): ParsedCard | ParseError {
  const trimmed = line.trim();

  if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("//")) {
    return { name: "", quantity: 0 };
  }

  // Match: "4 Card Name (SET) 123" or "4 Card Name (SET) 123 *F*" (foil)
  const match = trimmed.match(
    /^(\d+)\s+(.+?)\s+\(([A-Z0-9]+)\)\s+(\d+[a-z]?)(?:\s+\*F\*)?$/i,
  );

  if (match) {
    const quantity = parseInt(match[1], 10);
    const name = match[2].trim();
    const set_code = match[3].toUpperCase();
    const collector_number = match[4];
    const is_foil = trimmed.includes("*F*");

    if (quantity <= 0 || quantity > 99) {
      return {
        line: lineNumber,
        text: trimmed,
        error: `Invalid quantity: ${quantity}`,
      };
    }

    return { name, quantity, set_code, collector_number, is_foil };
  }

  // Try simpler Arena format without collector number: "4 Card Name (SET)"
  const simpleMatch = trimmed.match(/^(\d+)\s+(.+?)\s+\(([A-Z0-9]+)\)$/i);

  if (simpleMatch) {
    const quantity = parseInt(simpleMatch[1], 10);
    const name = simpleMatch[2].trim();
    const set_code = simpleMatch[3].toUpperCase();

    return { name, quantity, set_code };
  }

  // Fall back to simple format
  return parseSimpleLine(line, lineNumber);
}

/**
 * Parse CSV format with header row.
 */
function parseCSV(text: string): ParseResult {
  const lines = text.trim().split("\n");
  const cards: ParsedCard[] = [];
  const errors: ParseError[] = [];

  if (lines.length === 0) {
    return { cards, errors };
  }

  // Parse header to find column indices
  const headerLine = lines[0].toLowerCase();
  const headers = parseCSVLine(headerLine);

  const colMap: Record<string, number> = {};
  headers.forEach((header, index) => {
    const h = header.trim().toLowerCase();
    if (h === "quantity" || h === "qty" || h === "count") {
      colMap.quantity = index;
    } else if (
      h === "name" ||
      h === "card" ||
      h === "card_name" ||
      h === "cardname"
    ) {
      colMap.name = index;
    } else if (
      h === "set_code" ||
      h === "set" ||
      h === "edition" ||
      h === "setcode"
    ) {
      colMap.set_code = index;
    } else if (
      h === "collector_number" ||
      h === "number" ||
      h === "collectornumber" ||
      h === "cn"
    ) {
      colMap.collector_number = index;
    } else if (h === "foil" || h === "is_foil" || h === "isfoil") {
      colMap.foil = index;
    }
  });

  // Validate required columns
  if (colMap.name === undefined) {
    errors.push({
      line: 1,
      text: headerLine,
      error: "CSV must have a 'name' or 'card' column",
    });
    return { cards, errors };
  }

  // Parse data rows
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith("#")) {
      continue;
    }

    const values = parseCSVLine(line);
    const lineNumber = i + 1;

    const name = values[colMap.name]?.trim();
    if (!name) {
      errors.push({
        line: lineNumber,
        text: line,
        error: "Card name is empty",
      });
      continue;
    }

    const quantityStr =
      colMap.quantity !== undefined ? values[colMap.quantity] : "1";
    const quantity = parseInt(quantityStr?.trim() || "1", 10);

    if (isNaN(quantity) || quantity <= 0 || quantity > 99) {
      errors.push({
        line: lineNumber,
        text: line,
        error: `Invalid quantity: ${quantityStr}`,
      });
      continue;
    }

    const card: ParsedCard = { name, quantity };

    if (colMap.set_code !== undefined && values[colMap.set_code]) {
      card.set_code = values[colMap.set_code].trim().toUpperCase();
    }

    if (
      colMap.collector_number !== undefined &&
      values[colMap.collector_number]
    ) {
      card.collector_number = values[colMap.collector_number].trim();
    }

    if (colMap.foil !== undefined && values[colMap.foil]) {
      const foilValue = values[colMap.foil].trim().toLowerCase();
      card.is_foil =
        foilValue === "true" || foilValue === "1" || foilValue === "yes";
    }

    cards.push(card);
  }

  return { cards, errors };
}

/**
 * Parse a single CSV line, handling quoted values.
 */
function parseCSVLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        // Escaped quote
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }

  values.push(current);
  return values.map((v) => v.trim());
}

/**
 * Parse collection text in the specified format.
 */
export function parseCollectionText(
  text: string,
  format?: ImportFormat,
): ParseResult {
  const detectedFormat = format || detectFormat(text);
  const cards: ParsedCard[] = [];
  const errors: ParseError[] = [];

  if (detectedFormat === "csv") {
    return parseCSV(text);
  }

  const lines = text.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNumber = i + 1;

    let result: ParsedCard | ParseError;

    if (detectedFormat === "arena") {
      result = parseArenaLine(line, lineNumber);
    } else {
      result = parseSimpleLine(line, lineNumber);
    }

    // Check if result is an error
    if ("error" in result) {
      errors.push(result);
    } else if (result.name && result.quantity > 0) {
      // Valid card
      cards.push(result);
    }
    // Skip empty/comment lines (quantity === 0)
  }

  return { cards, errors };
}

/**
 * Merge duplicate cards in the parsed list.
 */
export function mergeCards(cards: ParsedCard[]): ParsedCard[] {
  const cardMap = new Map<string, ParsedCard>();

  for (const card of cards) {
    // Create a unique key based on name and optionally set/number
    const key =
      card.set_code && card.collector_number
        ? `${card.name.toLowerCase()}|${card.set_code}|${card.collector_number}`
        : card.name.toLowerCase();

    const existing = cardMap.get(key);
    if (existing) {
      existing.quantity = Math.min(existing.quantity + card.quantity, 9999);
      // Keep foil status if any entry is foil
      if (card.is_foil) {
        existing.is_foil = true;
      }
    } else {
      cardMap.set(key, { ...card });
    }
  }

  return Array.from(cardMap.values());
}

/**
 * Get statistics about the parsed cards.
 */
export function getImportStats(cards: ParsedCard[]): {
  uniqueCards: number;
  totalCards: number;
  withSetInfo: number;
  foilCount: number;
} {
  return {
    uniqueCards: cards.length,
    totalCards: cards.reduce((sum, c) => sum + c.quantity, 0),
    withSetInfo: cards.filter((c) => c.set_code).length,
    foilCount: cards.filter((c) => c.is_foil).length,
  };
}
