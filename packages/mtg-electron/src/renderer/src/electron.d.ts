/**
 * Type declarations for the Electron API exposed via preload.
 */

import type {
  SearchCardsInput,
  SearchResult as ApiSearchResult,
  CardDetail,
  RulingsResponse,
  PrintingsResponse,
  HealthResponse,
} from "../../shared/types/api";
import type { components } from "../../shared/types/api-generated";

// Types from generated OpenAPI schema
type DeckSummaryResponse = components["schemas"]["DeckSummaryResponse"];
type DeckResponse = components["schemas"]["DeckResponse"];
type SetsResponse = components["schemas"]["SetsResponse"];
type SetDetail = components["schemas"]["SetDetail"];
type SetCardsResponse = components["schemas"]["SetCardsResponse"];
type SetAnalysisResponse = components["schemas"]["SetAnalysisResponse"];

// Artists types from generated OpenAPI schema
type ArtistsListResponse = components["schemas"]["ArtistsListResponse"];
type ArtistCardsResult = components["schemas"]["ArtistCardsResult"];

// Synergy/Combo/Recommendation types
type FindSynergiesResult = components["schemas"]["FindSynergiesResult"];
type DetectCombosResult = components["schemas"]["DetectCombosResult"];
type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];
type DeckSuggestion = components["schemas"]["DeckSuggestion"];
type FilterOptionsResponse = components["schemas"]["FilterOptionsResponse"];

// Deck analysis types
type DeckHealthResult = components["schemas"]["DeckHealthResult"];
type ManaCurveResult = components["schemas"]["ManaCurveResult"];
type ColorAnalysisResult = components["schemas"]["ColorAnalysisResult"];
type DeckImpact = components["schemas"]["DeckImpact"];

// Setup types
type SetupStatus = components["schemas"]["SetupStatus"];

// Collection pricing types
type PriceCollectionResponse = components["schemas"]["PriceCollectionResponse"];
type ParseCollectionResponse = components["schemas"]["ParseCollectionResponse"];
type ParsedCard = components["schemas"]["ParsedCard"];
type ImportCollectionResponse =
  components["schemas"]["ImportCollectionResponse"];
type ListCollectionResponse = components["schemas"]["ListCollectionResponse"];
type CollectionCardResponse = components["schemas"]["CollectionCardResponse"];

interface CommanderMatch {
  name: string;
  colors: string[];
  archetype: string | null;
  completion_pct: number;
  reasons: string[];
}

interface CollectionCard {
  cardName: string;
  quantity: number;
  foilQuantity: number;
  setCode: string | null;
  setName: string | null;
  collectorNumber: string | null;
  addedAt: string;
  // Enriched data from card database
  colors: string[];
  typeLine: string | null;
  rarity: string | null;
  cmc: number;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

interface CollectionStats {
  unique: number;
  total: number;
  foils: number;
}

interface CollectionResult {
  cards: CollectionCard[];
  stats: CollectionStats;
  total: number;
  error?: string;
}

interface CollectionStatsDetailed {
  unique: number;
  total: number;
  foils: number;
  colors: Record<string, number>;
  types: Record<string, number>;
  rarities: Record<string, number>;
  manaCurve: Record<number, number>;
  topSets: Array<{ code: string; count: number }>;
  avgCmc: number;
  error?: string;
}

interface CollectionValueResult {
  totalValue: number;
  mostValuable: Array<{
    cardName: string;
    value: number;
    setCode: string | null;
    collectorNumber: string | null;
  }>;
  error?: string;
}

interface RecordPricesResult {
  success: boolean;
  cardsRecorded: number;
  error?: string;
}

interface PriceHistoryEntry {
  date: string;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

interface CollectionValueHistoryEntry {
  date: string;
  totalValue: number;
  cardCount: number;
}

// Valid channels for IPC event listeners
type EventChannel = "navigate" | "action";

interface ElectronAPI {
  getVersion: () => Promise<string>;
  getPlatform: () => Promise<string>;

  // Shell operations
  openExternal: (url: string) => Promise<void>;

  // IPC event listeners for menu actions
  on: (channel: EventChannel, callback: (...args: unknown[]) => void) => void;
  off: (channel: EventChannel, callback: (...args: unknown[]) => void) => void;
  removeAllListeners: (channel: EventChannel) => void;

  // HTTP API (mtg-core sidecar)
  api: {
    health: () => Promise<HealthResponse>;
    sidecarStatus: () => Promise<{
      status: string;
      isRunning: boolean;
      baseUrl: string;
    }>;
    setup: {
      getStatus: () => Promise<SetupStatus>;
      ensureUserDb: () => Promise<{ success: boolean }>;
      initDatabase: () => Promise<{
        success: boolean;
        message?: string;
        error?: string;
      }>;
      runUpdate: (
        force?: boolean,
      ) => Promise<{ success: boolean; message?: string; error?: string }>;
      getUpdateStreamUrl: (force?: boolean) => Promise<string>;
      runUpdateWithProgress: (
        force?: boolean,
      ) => Promise<{ success: boolean; message?: string; error?: string }>;
      onUpdateProgress: (
        callback: (data: {
          phase: string;
          progress: number;
          message: string;
          details?: string;
          combo_db_success?: boolean | null;
          gameplay_db_success?: boolean | null;
          themes_success?: boolean | null;
        }) => void,
      ) => void;
      removeUpdateProgressListener: () => void;
    };
    cards: {
      search: (filters: SearchCardsInput) => Promise<ApiSearchResult>;
      getByName: (name: string) => Promise<CardDetail>;
      getRulings: (name: string) => Promise<RulingsResponse>;
      getPrintings: (name: string) => Promise<PrintingsResponse>;
      random: () => Promise<ApiSearchResult>;
    };

    synergies: {
      find: (
        cardName: string,
        options?: { limit?: number; formatLegal?: string },
      ) => Promise<FindSynergiesResult>;
    };

    combos: {
      detect: (cardNames: string[]) => Promise<DetectCombosResult>;
      forCard: (cardName: string) => Promise<DetectCombosResult>;
    };

    recommendations: {
      getFilterOptions: () => Promise<FilterOptionsResponse>;
      suggestCards: (
        deckCards: string[],
        options?: {
          formatLegal?: string;
          budgetMax?: number;
          maxResults?: number;
          setCodes?: string[];
          themes?: string[];
          creatureTypes?: string[];
        },
      ) => Promise<SuggestCardsResult>;
      findCommanders: (options?: {
        collectionCards?: string[];
        useCollection?: boolean;
        colors?: string[];
        creatureType?: string;
        creatureTypes?: string[];
        theme?: string;
        themes?: string[];
        format?: string;
        setCodes?: string[];
        limit?: number;
      }) => Promise<CommanderMatch[]>;
      findDecks: (options?: {
        collectionCards?: string[];
        useCollection?: boolean;
        colors?: string[];
        creatureType?: string;
        creatureTypes?: string[];
        theme?: string;
        themes?: string[];
        format?: string;
        setCodes?: string[];
        minCompletion?: number;
        limit?: number;
      }) => Promise<DeckSuggestion[]>;
    };
  };

  store: {
    getRecentSearches: () => Promise<string[]>;
    clearRecentSearches: () => Promise<{ success: boolean }>;
    get: <T>(key: string) => Promise<T>;
    set: (key: string, value: unknown) => Promise<{ success: boolean }>;
  };
  collection: {
    list: (limit?: number, offset?: number) => Promise<CollectionResult>;
    listSorted: (options: {
      sortBy?: string;
      sortOrder?: "asc" | "desc";
      page?: number;
      pageSize?: number;
    }) => Promise<ListCollectionResponse>;
    stats: () => Promise<CollectionStatsDetailed>;
    value: () => Promise<CollectionValueResult>;
    parse: (
      text: string,
      defaultQuantity?: number,
    ) => Promise<ParseCollectionResponse>;
    price: (cards: ParsedCard[]) => Promise<PriceCollectionResponse>;
    import: (
      text: string,
      mode?: "add" | "replace",
    ) => Promise<ImportCollectionResponse>;
    update: (args: {
      cardName: string;
      setCode: string | null;
      collectorNumber: string | null;
      quantity: number;
      foilQuantity: number;
    }) => Promise<{ success: boolean; card?: CollectionCard; error?: string }>;
    delete: (args: {
      cardName: string;
      setCode: string | null;
      collectorNumber: string | null;
    }) => Promise<{ success: boolean; error?: string }>;
    recordPrices: () => Promise<RecordPricesResult>;
    priceHistory: (args: {
      cardName: string;
      setCode?: string;
      collectorNumber?: string;
      days?: number;
    }) => Promise<PriceHistoryEntry[]>;
    valueHistory: (days?: number) => Promise<CollectionValueHistoryEntry[]>;
    getValue: () => Promise<PriceCollectionResponse>;
  };

  // Deck operations via HTTP API
  decks: {
    list: () => Promise<DeckSummaryResponse[]>;
    create: (request: {
      name: string;
      format?: string | null;
      commander?: string | null;
      description?: string | null;
    }) => Promise<{ id: number }>;
    get: (deckId: number) => Promise<DeckResponse>;
    update: (
      deckId: number,
      request: {
        name?: string | null;
        format?: string | null;
        commander?: string | null;
        description?: string | null;
      },
    ) => Promise<DeckResponse>;
    delete: (deckId: number) => Promise<{ deleted: boolean }>;
    addCard: (
      deckId: number,
      request: {
        card_name: string;
        quantity?: number;
        is_sideboard?: boolean;
        is_maybeboard?: boolean;
        is_commander?: boolean;
        set_code?: string | null;
        collector_number?: string | null;
      },
    ) => Promise<{ success: boolean }>;
    removeCard: (
      deckId: number,
      cardName: string,
      sideboard?: boolean,
      maybeboard?: boolean,
    ) => Promise<{ removed: boolean }>;
    updateCardQuantity: (
      deckId: number,
      cardName: string,
      quantity: number,
      sideboard?: boolean,
      maybeboard?: boolean,
    ) => Promise<{ success: boolean }>;

    // Deck analysis
    validate: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
      format: string;
      commander?: string | null;
    }) => Promise<{
      format: string;
      is_valid: boolean;
      total_cards: number;
      sideboard_count: number;
      issues: Array<{
        card_name: string;
        issue: string;
        details?: string | null;
      }>;
      warnings: string[];
    }>;
    analyzeManaCurve: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }) => Promise<{
      curve: Record<string, number>;
      average_cmc: number;
      median_cmc: number;
      land_count: number;
      nonland_count: number;
      x_spell_count: number;
    }>;
    analyzeColors: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }) => Promise<{
      colors: string[];
      color_identity: string[];
      breakdown: Array<{
        color: string;
        color_name: string;
        card_count: number;
        mana_symbols: number;
      }>;
      multicolor_count: number;
      colorless_count: number;
      mana_pip_totals: Record<string, number>;
      recommended_land_ratio: Record<string, number>;
    }>;
    analyzeComposition: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }) => Promise<{
      total_cards: number;
      types: Array<{ type: string; count: number; percentage: number }>;
      creatures: number;
      noncreatures: number;
      lands: number;
      spells: number;
      interaction: number;
      ramp_count: number;
    }>;
    analyzeDeckHealth: (
      input: {
        cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
      },
      deckFormat?: string | null,
    ) => Promise<{
      score: number;
      grade: "S" | "A" | "B" | "C" | "D" | "F";
      archetype: string;
      archetype_confidence: number;
      total_cards: number;
      expected_cards: number;
      land_count: number;
      land_percentage: number;
      average_cmc: number;
      interaction_count: number;
      card_draw_count: number;
      ramp_count: number;
      creature_count: number;
      instant_count: number;
      sorcery_count: number;
      artifact_count: number;
      enchantment_count: number;
      planeswalker_count: number;
      top_keywords: Array<{ keyword: string; count: number }>;
      issues: Array<{ message: string; severity: "warning" | "error" }>;
      archetype_traits: string[];
    }>;
    // Analyze by deck ID (fetches cards from database directly)
    analyzeDeckHealthById: (deckId: number) => Promise<DeckHealthResult>;
    analyzeDeckManaCurveById: (deckId: number) => Promise<ManaCurveResult>;
    analyzeDeckColorsById: (deckId: number) => Promise<ColorAnalysisResult>;
    // Analyze deck price by ID
    analyzeDeckPriceById: (deckId: number) => Promise<{
      total_price: number | null;
      mainboard_price: number | null;
      sideboard_price: number | null;
      average_card_price: number | null;
      most_expensive: Array<{ name: string; price: number }>;
      missing_prices: string[];
    }>;
    // Analyze impact of adding a card to a deck
    analyzeDeckImpact: (
      cardName: string,
      deckId: number,
      quantity?: number,
    ) => Promise<DeckImpact>;

    // Import deck from URL or text
    parseImport: (input: {
      url?: string | null;
      text?: string | null;
      name?: string | null;
      format?: string | null;
    }) => Promise<{
      name: string;
      format: string | null;
      commander: string | null;
      cards: Array<{
        name: string;
        quantity: number;
        is_sideboard: boolean;
        is_commander: boolean;
        set_code: string | null;
        collector_number: string | null;
      }>;
      sideboard: Array<{
        name: string;
        quantity: number;
        is_sideboard: boolean;
        is_commander: boolean;
        set_code: string | null;
        collector_number: string | null;
      }>;
      maybeboard: Array<{
        name: string;
        quantity: number;
        is_sideboard: boolean;
        is_commander: boolean;
        set_code: string | null;
        collector_number: string | null;
      }>;
      source_url: string | null;
      errors: string[];
    }>;
  };

  // Sets operations via HTTP API
  sets: {
    list: (params?: {
      name?: string;
      set_type?: string;
    }) => Promise<SetsResponse>;
    get: (code: string) => Promise<SetDetail>;
    getCards: (
      code: string,
      page?: number,
      pageSize?: number,
    ) => Promise<SetCardsResponse>;
    getAnalysis: (code: string) => Promise<SetAnalysisResponse>;
  };

  // Artists operations via HTTP API
  artists: {
    list: (params?: {
      query?: string;
      min_cards?: number;
      limit?: number;
      offset?: number;
    }) => Promise<ArtistsListResponse>;
    getCards: (name: string) => Promise<ArtistCardsResult>;
  };
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
