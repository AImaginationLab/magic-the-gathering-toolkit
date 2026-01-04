/**
 * Preload script - exposes a safe API to the renderer.
 * Uses contextBridge for security isolation.
 */
import { contextBridge, ipcRenderer, shell } from "electron";

import type {
  SearchCardsInput,
  SearchResult as ApiSearchResult,
  CardDetail,
  RulingsResponse,
  PrintingsResponse,
  HealthResponse,
} from "../shared/types/api";
import type { components } from "../shared/types/api-generated";

// Types from generated schema
type DeckSummaryResponse = components["schemas"]["DeckSummaryResponse"];
type DeckResponse = components["schemas"]["DeckResponse"];
type SetsResponse = components["schemas"]["SetsResponse"];
type SetDetail = components["schemas"]["SetDetail"];
type SetCardsResponse = components["schemas"]["SetCardsResponse"];
type SetAnalysisResponse = components["schemas"]["SetAnalysisResponse"];

// Artists types from generated schema
type ArtistsListResponse = components["schemas"]["ArtistsListResponse"];
type ArtistCardsResult = components["schemas"]["ArtistCardsResult"];

// Synergy/Combo/Recommendation types from generated schema
type FindSynergiesResult = components["schemas"]["FindSynergiesResult"];
type DetectCombosResult = components["schemas"]["DetectCombosResult"];
type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];
type DeckSuggestion = components["schemas"]["DeckSuggestion"];
type FilterOptionsResponse = components["schemas"]["FilterOptionsResponse"];

// Deck analysis types from generated schema
type DeckHealthResult = components["schemas"]["DeckHealthResult"];
type ManaCurveResult = components["schemas"]["ManaCurveResult"];
type ColorAnalysisResult = components["schemas"]["ColorAnalysisResult"];
type DeckImpact = components["schemas"]["DeckImpact"];

// Setup types from generated schema
type SetupStatus = components["schemas"]["SetupStatus"];

// Collection types from generated schema
type ParseCollectionResponse = components["schemas"]["ParseCollectionResponse"];
type PriceCollectionResponse = components["schemas"]["PriceCollectionResponse"];
type CollectionParsedCard =
  components["schemas"]["mtg_core__api__routes__collection__ParsedCard"];
type ListCollectionResponse = components["schemas"]["ListCollectionResponse"];
type ImportCollectionResponse =
  components["schemas"]["ImportCollectionResponse"];

// CommanderMatch type (not in OpenAPI schema)
interface CommanderMatch {
  name: string;
  colors: string[];
  archetype: string | null;
  completion_pct: number;
  reasons: string[];
}

export interface CollectionCard {
  cardName: string;
  quantity: number;
  foilQuantity: number;
  setCode: string | null;
  collectorNumber: string | null;
  addedAt: string;
}

export interface CollectionStats {
  unique: number;
  total: number;
  foils: number;
}

export interface CollectionResult {
  cards: CollectionCard[];
  stats: CollectionStats;
  total: number;
  error?: string;
}

export interface CollectionStatsDetailed {
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

export interface CollectionValueResult {
  totalValue: number;
  mostValuable: Array<{
    cardName: string;
    value: number;
    setCode: string | null;
    collectorNumber: string | null;
  }>;
  error?: string;
}

export interface RecordPricesResult {
  success: boolean;
  cardsRecorded: number;
  error?: string;
}

export interface PriceHistoryEntry {
  date: string;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

export interface CollectionValueHistoryEntry {
  date: string;
  totalValue: number;
  cardCount: number;
}

// Deck types will be defined in shared/types/api.ts and used via HTTP API

// Valid channels for IPC event listeners
const VALID_EVENT_CHANNELS = ["navigate", "action"] as const;
type EventChannel = (typeof VALID_EVENT_CHANNELS)[number];

// Track wrapped callbacks to enable proper removal (prevents memory leak)
type WrappedCallback = (
  event: Electron.IpcRendererEvent,
  ...args: unknown[]
) => void;
const callbackMap = new WeakMap<
  (...args: unknown[]) => void,
  Map<EventChannel, WrappedCallback>
>();

// The API exposed to the renderer
const electronAPI = {
  // App info
  getVersion: () => ipcRenderer.invoke("app:get-version"),
  getPlatform: () => ipcRenderer.invoke("app:get-platform"),

  // Shell operations
  openExternal: (url: string): Promise<void> => shell.openExternal(url),

  // IPC event listeners for menu actions
  on: (channel: EventChannel, callback: (...args: unknown[]) => void): void => {
    if (VALID_EVENT_CHANNELS.includes(channel)) {
      // Create wrapped callback and store mapping
      const wrappedCallback: WrappedCallback = (_event, ...args) =>
        callback(...args);

      let channelMap = callbackMap.get(callback);
      if (!channelMap) {
        channelMap = new Map();
        callbackMap.set(callback, channelMap);
      }
      channelMap.set(channel, wrappedCallback);

      ipcRenderer.on(channel, wrappedCallback);
    }
  },
  off: (
    channel: EventChannel,
    callback: (...args: unknown[]) => void,
  ): void => {
    if (VALID_EVENT_CHANNELS.includes(channel)) {
      // Retrieve the wrapped callback to properly remove it
      const channelMap = callbackMap.get(callback);
      const wrappedCallback = channelMap?.get(channel);
      if (wrappedCallback) {
        ipcRenderer.removeListener(channel, wrappedCallback);
        channelMap?.delete(channel);
        // Clean up empty maps
        if (channelMap?.size === 0) {
          callbackMap.delete(callback);
        }
      }
    }
  },
  removeAllListeners: (channel: EventChannel): void => {
    if (VALID_EVENT_CHANNELS.includes(channel)) {
      ipcRenderer.removeAllListeners(channel);
    }
  },

  // HTTP API (mtg-core sidecar)
  api: {
    // Health check
    health: (): Promise<HealthResponse> => ipcRenderer.invoke("api:health"),

    // Sidecar status
    sidecarStatus: (): Promise<{
      status: string;
      isRunning: boolean;
      baseUrl: string;
    }> => ipcRenderer.invoke("sidecar:status"),

    // Setup operations (database initialization)
    setup: {
      getStatus: (): Promise<SetupStatus> =>
        ipcRenderer.invoke("api:setup-status"),
      ensureUserDb: (): Promise<{ success: boolean }> =>
        ipcRenderer.invoke("api:ensure-user-db"),
      initDatabase: (): Promise<{
        success: boolean;
        message?: string;
        error?: string;
      }> => ipcRenderer.invoke("api:init-database"),
      runUpdate: (
        force?: boolean,
      ): Promise<{ success: boolean; message?: string; error?: string }> =>
        ipcRenderer.invoke("api:run-update", force ?? false),
      getUpdateStreamUrl: (force?: boolean): Promise<string> =>
        ipcRenderer.invoke("api:get-update-stream-url", force ?? false),
      runUpdateWithProgress: (
        force?: boolean,
      ): Promise<{ success: boolean; message?: string; error?: string }> =>
        ipcRenderer.invoke("api:run-update-with-progress", force ?? false),
      onUpdateProgress: (
        callback: (data: {
          phase: string;
          progress: number;
          message: string;
          details?: string;
        }) => void,
      ): void => {
        ipcRenderer.on("update-progress", (_event, data) => callback(data));
      },
      removeUpdateProgressListener: (): void => {
        ipcRenderer.removeAllListeners("update-progress");
      },
    },

    // Card operations
    cards: {
      search: (filters: SearchCardsInput): Promise<ApiSearchResult> =>
        ipcRenderer.invoke("api:search-cards", filters),
      getByName: (name: string): Promise<CardDetail> =>
        ipcRenderer.invoke("api:card-details", name),
      getRulings: (name: string): Promise<RulingsResponse> =>
        ipcRenderer.invoke("api:card-rulings", name),
      getPrintings: (name: string): Promise<PrintingsResponse> =>
        ipcRenderer.invoke("api:card-printings", name),
      random: (): Promise<ApiSearchResult> =>
        ipcRenderer.invoke("api:search-cards", { page_size: 1, random: true }),
    },

    // Synergy operations
    synergies: {
      find: (
        cardName: string,
        options?: { limit?: number; formatLegal?: string },
      ): Promise<FindSynergiesResult> =>
        ipcRenderer.invoke("api:find-synergies", cardName, options),
    },

    // Combo operations
    combos: {
      detect: (cardNames: string[]): Promise<DetectCombosResult> =>
        ipcRenderer.invoke("api:detect-combos", cardNames),
      forCard: (cardName: string): Promise<DetectCombosResult> =>
        ipcRenderer.invoke("api:combos-for-card", cardName),
    },

    // Recommendation operations
    recommendations: {
      getFilterOptions: (): Promise<FilterOptionsResponse> =>
        ipcRenderer.invoke("api:get-filter-options"),

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
      ): Promise<SuggestCardsResult> =>
        ipcRenderer.invoke("api:suggest-cards", deckCards, options),

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
      }): Promise<CommanderMatch[]> =>
        ipcRenderer.invoke("api:find-commanders", options),

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
      }): Promise<DeckSuggestion[]> =>
        ipcRenderer.invoke("api:find-decks", options),
    },
  },

  // Store operations (persistent preferences)
  store: {
    getRecentSearches: (): Promise<string[]> =>
      ipcRenderer.invoke("store:get-recent-searches"),
    clearRecentSearches: (): Promise<{ success: boolean }> =>
      ipcRenderer.invoke("store:clear-recent-searches"),
    get: <T>(key: string): Promise<T> => ipcRenderer.invoke("store:get", key),
    set: (key: string, value: unknown): Promise<{ success: boolean }> =>
      ipcRenderer.invoke("store:set", key, value),
  },

  // Collection operations
  collection: {
    list: (limit?: number, offset?: number): Promise<CollectionResult> =>
      ipcRenderer.invoke("collection:list", { limit, offset }),
    listSorted: (options: {
      sortBy?: string;
      sortOrder?: "asc" | "desc";
      page?: number;
      pageSize?: number;
    }): Promise<ListCollectionResponse> =>
      ipcRenderer.invoke("api:collection-list", options),
    stats: (): Promise<CollectionStatsDetailed> =>
      ipcRenderer.invoke("collection:stats"),
    value: (): Promise<CollectionValueResult> =>
      ipcRenderer.invoke("collection:value"),
    parse: (
      text: string,
      defaultQuantity?: number,
    ): Promise<ParseCollectionResponse> =>
      ipcRenderer.invoke("api:parse-collection", text, defaultQuantity),
    price: (cards: CollectionParsedCard[]): Promise<PriceCollectionResponse> =>
      ipcRenderer.invoke("api:price-collection", cards),
    getValue: (): Promise<PriceCollectionResponse> =>
      ipcRenderer.invoke("api:collection-value"),
    import: (
      text: string,
      mode?: "add" | "replace",
    ): Promise<ImportCollectionResponse> =>
      ipcRenderer.invoke("api:collection-import", text, mode ?? "add"),
    update: (args: {
      cardName: string;
      setCode: string | null;
      collectorNumber: string | null;
      quantity: number;
      foilQuantity: number;
    }): Promise<{ success: boolean; card?: CollectionCard; error?: string }> =>
      ipcRenderer.invoke("collection:update", args),
    delete: (args: {
      cardName: string;
      setCode: string | null;
      collectorNumber: string | null;
    }): Promise<{ success: boolean; error?: string }> =>
      ipcRenderer.invoke("collection:delete", args),
    recordPrices: (): Promise<RecordPricesResult> =>
      ipcRenderer.invoke("collection:record-prices"),
    priceHistory: (args: {
      cardName: string;
      setCode?: string;
      collectorNumber?: string;
      days?: number;
    }): Promise<PriceHistoryEntry[]> =>
      ipcRenderer.invoke("collection:price-history", args),
    valueHistory: (days?: number): Promise<CollectionValueHistoryEntry[]> =>
      ipcRenderer.invoke("collection:value-history", days),
  },

  // Deck operations via HTTP API
  decks: {
    list: (): Promise<DeckSummaryResponse[]> =>
      ipcRenderer.invoke("api:list-decks"),

    create: (request: {
      name: string;
      format?: string | null;
      commander?: string | null;
      description?: string | null;
    }): Promise<{ id: number }> =>
      ipcRenderer.invoke("api:create-deck", request),

    get: (deckId: number): Promise<DeckResponse> =>
      ipcRenderer.invoke("api:get-deck", deckId),

    update: (
      deckId: number,
      request: {
        name?: string | null;
        format?: string | null;
        commander?: string | null;
        description?: string | null;
      },
    ): Promise<DeckResponse> =>
      ipcRenderer.invoke("api:update-deck", deckId, request),

    delete: (deckId: number): Promise<{ deleted: boolean }> =>
      ipcRenderer.invoke("api:delete-deck", deckId),

    addCard: (
      deckId: number,
      request: {
        card_name: string;
        quantity?: number;
        is_sideboard?: boolean;
        is_commander?: boolean;
        set_code?: string | null;
        collector_number?: string | null;
      },
    ): Promise<{ success: boolean }> =>
      ipcRenderer.invoke("api:add-card-to-deck", deckId, request),

    removeCard: (
      deckId: number,
      cardName: string,
      sideboard?: boolean,
      maybeboard?: boolean,
    ): Promise<{ removed: boolean }> =>
      ipcRenderer.invoke(
        "api:remove-card-from-deck",
        deckId,
        cardName,
        sideboard ?? false,
        maybeboard ?? false,
      ),

    updateCardQuantity: (
      deckId: number,
      cardName: string,
      quantity: number,
      sideboard?: boolean,
      maybeboard?: boolean,
    ): Promise<{ success: boolean }> =>
      ipcRenderer.invoke(
        "api:update-card-quantity",
        deckId,
        cardName,
        quantity,
        sideboard ?? false,
        maybeboard ?? false,
      ),

    // Deck analysis
    validate: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
      format: string;
      commander?: string | null;
    }): Promise<{
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
    }> => ipcRenderer.invoke("api:validate-deck", input),

    analyzeManaCurve: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }): Promise<{
      curve: Record<string, number>;
      average_cmc: number;
      median_cmc: number;
      land_count: number;
      nonland_count: number;
      x_spell_count: number;
    }> => ipcRenderer.invoke("api:analyze-mana-curve", input),

    analyzeColors: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }): Promise<{
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
    }> => ipcRenderer.invoke("api:analyze-colors", input),

    analyzeComposition: (input: {
      cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
    }): Promise<{
      total_cards: number;
      types: Array<{ type: string; count: number; percentage: number }>;
      creatures: number;
      noncreatures: number;
      lands: number;
      spells: number;
      interaction: number;
      ramp_count: number;
    }> => ipcRenderer.invoke("api:analyze-composition", input),

    analyzeDeckHealth: (
      input: {
        cards: Array<{ name: string; quantity?: number; sideboard?: boolean }>;
      },
      deckFormat?: string | null,
    ): Promise<{
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
    }> => ipcRenderer.invoke("api:analyze-deck-health", { input, deckFormat }),

    // Analyze by deck ID (fetches cards from database directly)
    analyzeDeckHealthById: (deckId: number): Promise<DeckHealthResult> =>
      ipcRenderer.invoke("api:analyze-deck-health-by-id", deckId),

    analyzeDeckManaCurveById: (deckId: number): Promise<ManaCurveResult> =>
      ipcRenderer.invoke("api:analyze-deck-mana-curve-by-id", deckId),

    analyzeDeckColorsById: (deckId: number): Promise<ColorAnalysisResult> =>
      ipcRenderer.invoke("api:analyze-deck-colors-by-id", deckId),

    analyzeDeckPriceById: (
      deckId: number,
    ): Promise<{
      total_price: number | null;
      mainboard_price: number | null;
      sideboard_price: number | null;
      average_card_price: number | null;
      most_expensive: Array<{ name: string; price: number }>;
      missing_prices: string[];
    }> => ipcRenderer.invoke("api:analyze-deck-price-by-id", deckId),

    analyzeDeckImpact: (
      cardName: string,
      deckId: number,
      quantity?: number,
    ): Promise<DeckImpact> =>
      ipcRenderer.invoke("api:analyze-deck-impact", {
        cardName,
        deckId,
        quantity,
      }),

    // Import deck from URL or text
    parseImport: (input: {
      url?: string | null;
      text?: string | null;
      name?: string | null;
      format?: string | null;
    }): Promise<{
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
    }> => ipcRenderer.invoke("api:parse-import-deck", input),
  },

  // Sets operations via HTTP API
  sets: {
    list: (params?: {
      name?: string;
      set_type?: string;
    }): Promise<SetsResponse> => ipcRenderer.invoke("api:list-sets", params),

    get: (code: string): Promise<SetDetail> =>
      ipcRenderer.invoke("api:get-set", code),

    getCards: (
      code: string,
      page?: number,
      pageSize?: number,
    ): Promise<SetCardsResponse> =>
      ipcRenderer.invoke("api:get-set-cards", { code, page, pageSize }),

    getAnalysis: (code: string): Promise<SetAnalysisResponse> =>
      ipcRenderer.invoke("api:get-set-analysis", code),
  },

  // Artists operations via HTTP API
  artists: {
    list: (params?: {
      query?: string;
      min_cards?: number;
      limit?: number;
      offset?: number;
    }): Promise<ArtistsListResponse> =>
      ipcRenderer.invoke("api:list-artists", params),

    getCards: (name: string): Promise<ArtistCardsResult> =>
      ipcRenderer.invoke("api:get-artist-cards", name),
  },
} as const;

// Export type for use in renderer
export type ElectronAPI = typeof electronAPI;

// Expose to renderer
contextBridge.exposeInMainWorld("electronAPI", electronAPI);
