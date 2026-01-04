/**
 * Type-safe API client generated from OpenAPI schema.
 *
 * Uses openapi-fetch for automatic type inference from the generated schema.
 * This replaces manually written type definitions with auto-generated ones.
 */

import createClient from "openapi-fetch";
import type { paths, components } from "../shared/types/api-generated";
import { logger } from "./utils";
import type { SidecarManager } from "./sidecar";

// Re-export schema types for convenience
export type { paths, components };

// Commonly used schema types
export type SearchCardsInput = components["schemas"]["SearchCardsInput"];
export type SearchResult = components["schemas"]["SearchResult"];
export type CardSummary = components["schemas"]["CardSummary"];
export type CardDetail = components["schemas"]["CardDetail"];
export type RulingsResponse = components["schemas"]["RulingsResponse"];
export type PrintingsResponse = components["schemas"]["PrintingsResponse"];
export type PrintingInfo = components["schemas"]["PrintingInfo"];
export type FindSynergiesResult = components["schemas"]["FindSynergiesResult"];
export type DetectCombosResult = components["schemas"]["DetectCombosResult"];
export type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];
export type DeckSuggestion = components["schemas"]["DeckSuggestion"];
export type FilterOptionsResponse =
  components["schemas"]["FilterOptionsResponse"];
export type DeckValidationResult =
  components["schemas"]["DeckValidationResult"];
export type ManaCurveResult = components["schemas"]["ManaCurveResult"];
export type ColorAnalysisResult = components["schemas"]["ColorAnalysisResult"];
export type CompositionResult = components["schemas"]["CompositionResult"];
export type DeckHealthResult = components["schemas"]["DeckHealthResult"];
export type DeckHealthIssue = components["schemas"]["DeckHealthIssue"];
export type KeywordCount = components["schemas"]["KeywordCount"];
export type ValidateDeckInput = components["schemas"]["ValidateDeckInput"];
export type AnalyzeDeckInput = components["schemas"]["AnalyzeDeckInput"];
export type DeckSummaryResponse = components["schemas"]["DeckSummaryResponse"];
export type DeckResponse = components["schemas"]["DeckResponse"];
export type DeckCardResponse = components["schemas"]["DeckCardResponse"];
export type DeckImpact = components["schemas"]["DeckImpact"];
export type DeckImpactInput = components["schemas"]["DeckImpactInput"];
export type StatChange = components["schemas"]["StatChange"];
export type PriceAnalysisResult = components["schemas"]["PriceAnalysisResult"];
export type ImportDeckInput = components["schemas"]["ImportDeckInput"];
export type ImportDeckResult = components["schemas"]["ImportDeckResult"];
export type DeckParsedCard =
  components["schemas"]["mtg_core__api__routes__decks__ParsedCard"];
export type HealthCheckResponse = { status: string };

// Sets types
export type SetSummary = components["schemas"]["SetSummary"];
export type SetDetail = components["schemas"]["SetDetail"];
export type SetsResponse = components["schemas"]["SetsResponse"];
export type SetCardsResponse = components["schemas"]["SetCardsResponse"];
export type SetAnalysisResponse = components["schemas"]["SetAnalysisResponse"];

// Artists types
export type ArtistSummary = components["schemas"]["ArtistSummary"];
export type ArtistsListResponse = components["schemas"]["ArtistsListResponse"];
export type ArtistCardsResult = components["schemas"]["ArtistCardsResult"];

// Collection types
export type ParseCollectionRequest =
  components["schemas"]["ParseCollectionRequest"];
export type ParseCollectionResponse =
  components["schemas"]["ParseCollectionResponse"];
export type ParsedCard =
  components["schemas"]["mtg_core__api__routes__collection__ParsedCard"];
export type PriceCollectionRequest =
  components["schemas"]["PriceCollectionRequest"];
export type PriceCollectionResponse =
  components["schemas"]["PriceCollectionResponse"];
export type PricedCard = components["schemas"]["PricedCard"];
export type TopCard = components["schemas"]["TopCard"];
export type ImportCollectionRequest =
  components["schemas"]["ImportCollectionRequest"];
export type ImportCollectionResponse =
  components["schemas"]["ImportCollectionResponse"];
export type ImportedCardInfo = components["schemas"]["ImportedCardInfo"];
export type ListCollectionResponse =
  components["schemas"]["ListCollectionResponse"];
export type CollectionCardResponse =
  components["schemas"]["CollectionCardResponse"];

// CollectionSortField is a query parameter enum, not in schemas
export type CollectionSortField =
  | "name"
  | "dateAdded"
  | "quantity"
  | "setCode"
  | "price"
  | "rarity"
  | "cmc"
  | "type"
  | "color"
  | "winRate"
  | "tier"
  | "draftPick";

// Setup types
export type SetupStatus = components["schemas"]["SetupStatus"];

// CommanderMatch is not in the OpenAPI schema (returns dict), so define it here
export interface CommanderMatch {
  name: string;
  colors: string[];
  archetype: string | null;
  completion_pct: number;
  reasons: string[];
}

export interface ApiClientOptions {
  baseUrl?: string;
  timeout?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Type-safe MTG API client using openapi-fetch.
 *
 * All methods are automatically typed based on the OpenAPI schema.
 */
export class MTGApiClient {
  private readonly client: ReturnType<typeof createClient<paths>>;
  private readonly baseUrl: string;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? "http://127.0.0.1:8765";

    this.client = createClient<paths>({
      baseUrl: this.baseUrl,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });
  }

  /**
   * Create a client from a sidecar manager.
   */
  static fromSidecar(sidecar: SidecarManager): MTGApiClient {
    return new MTGApiClient({ baseUrl: sidecar.baseUrl });
  }

  // ===========================================================================
  // Health
  // ===========================================================================

  async health(): Promise<HealthCheckResponse> {
    const { data, error } = await this.client.GET("/health");
    if (error) throw this.toApiError(error);
    return { status: (data as Record<string, string>).status ?? "ok" };
  }

  // ===========================================================================
  // Setup
  // ===========================================================================

  async getSetupStatus(): Promise<SetupStatus> {
    logger.debug("getSetupStatus");
    const { data, error } = await this.client.GET("/setup/status");
    if (error) throw this.toApiError(error);
    return data;
  }

  async ensureUserDb(): Promise<{ success: boolean }> {
    logger.debug("ensureUserDb");
    const { data, error } = await this.client.POST("/setup/ensure-user-db");
    if (error) throw this.toApiError(error);
    return data as { success: boolean };
  }

  async runUpdate(
    force: boolean = false,
  ): Promise<{ success: boolean; message?: string; error?: string }> {
    logger.debug("runUpdate", { force });
    const { data, error } = await this.client.POST("/setup/update", {
      params: { query: { force } },
    });
    if (error) throw this.toApiError(error);
    return data as { success: boolean; message?: string; error?: string };
  }

  async initDatabase(): Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }> {
    logger.debug("initDatabase");
    const { data, error } = await this.client.POST("/setup/init-database");
    if (error) throw this.toApiError(error);
    return data as { success: boolean; message?: string; error?: string };
  }

  /**
   * Get the URL for the SSE update stream endpoint.
   * This returns the URL to connect to for streaming progress updates.
   */
  getUpdateStreamUrl(force: boolean = false): string {
    return `${this.baseUrl}/setup/update/stream?force=${force}`;
  }

  // ===========================================================================
  // Cards
  // ===========================================================================

  async searchCards(filters: SearchCardsInput): Promise<SearchResult> {
    logger.debug("searchCards", filters);
    const { data, error } = await this.client.POST("/cards/search", {
      body: filters,
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getCardDetails(name: string): Promise<CardDetail> {
    logger.debug("getCardDetails", name);
    const { data, error } = await this.client.POST("/cards/details", {
      body: { name },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getCardRulings(name: string): Promise<RulingsResponse> {
    logger.debug("getCardRulings", name);
    const { data, error } = await this.client.POST("/cards/rulings", {
      body: { name },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getCardPrintings(name: string): Promise<PrintingsResponse> {
    logger.debug("getCardPrintings", name);
    const { data, error } = await this.client.POST("/cards/printings", {
      body: { name },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Synergies
  // ===========================================================================

  async findSynergies(
    cardName: string,
    options: { limit?: number; formatLegal?: string } = {},
  ): Promise<FindSynergiesResult> {
    logger.debug("findSynergies", cardName, options);
    const { data, error } = await this.client.POST("/synergies/find", {
      body: {
        card_name: cardName,
        limit: options.limit ?? 20,
        format_legal: options.formatLegal ?? null,
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Combos
  // ===========================================================================

  async detectCombos(cardNames: string[]): Promise<DetectCombosResult> {
    logger.debug("detectCombos", cardNames.length, "cards");
    const { data, error } = await this.client.POST("/combos/detect", {
      body: { card_names: cardNames },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getCombosForCard(cardName: string): Promise<DetectCombosResult> {
    logger.debug("getCombosForCard", cardName);
    const { data, error } = await this.client.POST("/combos/for-card", {
      body: { card_name: cardName },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Recommendations
  // ===========================================================================

  async getFilterOptions(): Promise<FilterOptionsResponse> {
    logger.debug("getFilterOptions");
    const { data, error } = await this.client.GET(
      "/recommendations/filter-options",
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async suggestCards(
    deckCards: string[],
    options: {
      formatLegal?: string;
      budgetMax?: number;
      maxResults?: number;
      setCodes?: string[];
      themes?: string[];
      creatureTypes?: string[];
      ownedOnly?: boolean;
    } = {},
  ): Promise<SuggestCardsResult> {
    logger.debug("suggestCards", deckCards.length, "cards", options);
    const { data, error } = await this.client.POST("/recommendations/cards", {
      body: {
        deck_cards: deckCards,
        format_legal: options.formatLegal ?? null,
        budget_max: options.budgetMax ?? null,
        max_results: options.maxResults ?? 10,
        set_codes: options.setCodes ?? null,
        themes: options.themes ?? null,
        creature_types: options.creatureTypes ?? null,
        owned_only: options.ownedOnly ?? false,
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async findCommanders(
    options: {
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
    } = {},
  ): Promise<CommanderMatch[]> {
    logger.debug(
      "findCommanders",
      options.useCollection
        ? "using collection"
        : `${options.collectionCards?.length ?? 0} cards`,
      options,
    );
    // The API returns an array directly for this endpoint
    const response = await fetch(`${this.baseUrl}/recommendations/commanders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        collection_cards: options.collectionCards ?? null,
        use_collection: options.useCollection ?? false,
        colors: options.colors ?? null,
        creature_type: options.creatureType ?? null,
        creature_types: options.creatureTypes ?? null,
        theme: options.theme ?? null,
        themes: options.themes ?? null,
        format: options.format ?? null,
        set_codes: options.setCodes ?? null,
        limit: options.limit ?? 10,
      }),
    });
    if (!response.ok) {
      throw new ApiError(
        `API request failed with status ${response.status}`,
        response.status,
      );
    }
    return response.json() as Promise<CommanderMatch[]>;
  }

  async findDecks(
    options: {
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
    } = {},
  ): Promise<DeckSuggestion[]> {
    logger.debug(
      "findDecks",
      options.useCollection
        ? "using collection"
        : `${options.collectionCards?.length ?? 0} cards`,
      options,
    );
    // The API returns an array directly for this endpoint
    const response = await fetch(`${this.baseUrl}/recommendations/decks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        collection_cards: options.collectionCards ?? null,
        use_collection: options.useCollection ?? false,
        colors: options.colors ?? null,
        creature_type: options.creatureType ?? null,
        creature_types: options.creatureTypes ?? null,
        theme: options.theme ?? null,
        themes: options.themes ?? null,
        format: options.format ?? null,
        set_codes: options.setCodes ?? null,
        min_completion: options.minCompletion ?? 0.0,
        limit: options.limit ?? 10,
      }),
    });
    if (!response.ok) {
      throw new ApiError(
        `API request failed with status ${response.status}`,
        response.status,
      );
    }
    return response.json() as Promise<DeckSuggestion[]>;
  }

  // ===========================================================================
  // Deck Analysis
  // ===========================================================================

  async validateDeck(input: ValidateDeckInput): Promise<DeckValidationResult> {
    logger.debug("validateDeck", input.cards.length, "cards");
    const { data, error } = await this.client.POST("/decks/validate", {
      body: input,
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeManaCurve(input: AnalyzeDeckInput): Promise<ManaCurveResult> {
    logger.debug("analyzeManaCurve", input.cards.length, "cards");
    const { data, error } = await this.client.POST(
      "/decks/analyze/mana-curve",
      {
        body: input,
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeColors(input: AnalyzeDeckInput): Promise<ColorAnalysisResult> {
    logger.debug("analyzeColors", input.cards.length, "cards");
    const { data, error } = await this.client.POST("/decks/analyze/colors", {
      body: input,
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeComposition(
    input: AnalyzeDeckInput,
  ): Promise<CompositionResult> {
    logger.debug("analyzeComposition", input.cards.length, "cards");
    const { data, error } = await this.client.POST(
      "/decks/analyze/composition",
      {
        body: input,
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckHealth(
    input: AnalyzeDeckInput,
    deckFormat?: string | null,
  ): Promise<DeckHealthResult> {
    logger.debug("analyzeDeckHealth", input.cards.length, "cards");
    const { data, error } = await this.client.POST("/decks/analyze/health", {
      body: input,
      params: { query: { deck_format: deckFormat ?? undefined } },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // User Decks (CRUD)
  // ===========================================================================

  async listDecks(): Promise<DeckSummaryResponse[]> {
    logger.debug("listDecks");
    const { data, error } = await this.client.GET("/user/decks");
    if (error) throw this.toApiError(error);
    return data;
  }

  async createDeck(request: {
    name: string;
    format?: string | null;
    commander?: string | null;
    description?: string | null;
  }): Promise<{ id: number }> {
    logger.debug("createDeck", request.name);
    const { data, error } = await this.client.POST("/user/decks", {
      body: request,
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getDeck(deckId: number): Promise<DeckResponse> {
    logger.debug("getDeck", deckId);
    const { data, error } = await this.client.GET("/user/decks/{deck_id}", {
      params: { path: { deck_id: deckId } },
    });
    if (error) throw this.toApiError(error);
    return data as DeckResponse;
  }

  async updateDeck(
    deckId: number,
    request: {
      name?: string | null;
      format?: string | null;
      commander?: string | null;
      description?: string | null;
    },
  ): Promise<DeckResponse> {
    logger.debug("updateDeck", deckId, request);
    const { data, error } = await this.client.PUT("/user/decks/{deck_id}", {
      params: { path: { deck_id: deckId } },
      body: request,
    });
    if (error) throw this.toApiError(error);
    return data as DeckResponse;
  }

  async deleteDeck(deckId: number): Promise<{ deleted: boolean }> {
    logger.debug("deleteDeck", deckId);
    const { data, error } = await this.client.DELETE("/user/decks/{deck_id}", {
      params: { path: { deck_id: deckId } },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async addCardToDeck(
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
  ): Promise<{ success: boolean }> {
    logger.debug("addCardToDeck", deckId, request.card_name);
    const { data, error } = await this.client.POST(
      "/user/decks/{deck_id}/cards",
      {
        params: { path: { deck_id: deckId } },
        body: {
          card_name: request.card_name,
          quantity: request.quantity ?? 1,
          is_sideboard: request.is_sideboard ?? false,
          is_maybeboard: request.is_maybeboard ?? false,
          is_commander: request.is_commander ?? false,
          set_code: request.set_code ?? null,
          collector_number: request.collector_number ?? null,
        },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async removeCardFromDeck(
    deckId: number,
    cardName: string,
    sideboard: boolean = false,
    maybeboard: boolean = false,
  ): Promise<{ removed: boolean }> {
    logger.debug("removeCardFromDeck", deckId, cardName, sideboard, maybeboard);
    const { data, error } = await this.client.DELETE(
      "/user/decks/{deck_id}/cards/{card_name}",
      {
        params: {
          path: { deck_id: deckId, card_name: cardName },
          query: { sideboard, maybeboard },
        },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async updateCardQuantity(
    deckId: number,
    cardName: string,
    quantity: number,
    sideboard: boolean = false,
    maybeboard: boolean = false,
  ): Promise<{ success: boolean }> {
    logger.debug(
      "updateCardQuantity",
      deckId,
      cardName,
      quantity,
      sideboard,
      maybeboard,
    );
    const { data, error } = await this.client.PUT(
      "/user/decks/{deck_id}/cards/{card_name}",
      {
        params: {
          path: { deck_id: deckId, card_name: cardName },
          query: { sideboard, maybeboard },
        },
        body: { quantity },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckHealthById(deckId: number): Promise<DeckHealthResult> {
    logger.debug("analyzeDeckHealthById", deckId);
    const { data, error } = await this.client.GET(
      "/user/decks/{deck_id}/analyze/health",
      {
        params: { path: { deck_id: deckId } },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckManaCurveById(deckId: number): Promise<ManaCurveResult> {
    logger.debug("analyzeDeckManaCurveById", deckId);
    const { data, error } = await this.client.GET(
      "/user/decks/{deck_id}/analyze/mana-curve",
      {
        params: { path: { deck_id: deckId } },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckColorsById(deckId: number): Promise<ColorAnalysisResult> {
    logger.debug("analyzeDeckColorsById", deckId);
    const { data, error } = await this.client.GET(
      "/user/decks/{deck_id}/analyze/colors",
      {
        params: { path: { deck_id: deckId } },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckPriceById(deckId: number): Promise<PriceAnalysisResult> {
    logger.debug("analyzeDeckPriceById", deckId);
    const { data, error } = await this.client.GET(
      "/user/decks/{deck_id}/analyze/price",
      {
        params: { path: { deck_id: deckId } },
      },
    );
    if (error) throw this.toApiError(error);
    return data;
  }

  async analyzeDeckImpact(
    cardName: string,
    deckId: number,
    quantity: number = 1,
  ): Promise<DeckImpact> {
    logger.debug("analyzeDeckImpact", cardName, deckId, quantity);
    const { data, error } = await this.client.POST("/decks/analyze/impact", {
      body: {
        card_name: cardName,
        deck_id: deckId,
        quantity: quantity,
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async parseImportDeck(input: {
    url?: string | null;
    text?: string | null;
    name?: string | null;
    format?: string | null;
  }): Promise<ImportDeckResult> {
    logger.debug("parseImportDeck", input.url ?? input.text?.slice(0, 50));
    const { data, error } = await this.client.POST("/decks/import/parse", {
      body: {
        url: input.url ?? null,
        text: input.text ?? null,
        name: input.name ?? null,
        format: input.format ?? null,
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Sets
  // ===========================================================================

  async listSets(params?: {
    name?: string;
    set_type?: string;
  }): Promise<SetsResponse> {
    logger.debug("listSets", params);
    const { data, error } = await this.client.GET("/sets", {
      params: { query: params },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getSet(code: string): Promise<SetDetail> {
    logger.debug("getSet", code);
    const { data, error } = await this.client.GET("/sets/{code}", {
      params: { path: { code } },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getSetCards(
    code: string,
    page?: number,
    pageSize?: number,
  ): Promise<SetCardsResponse> {
    logger.debug("getSetCards", code, page, pageSize);
    const { data, error } = await this.client.GET("/sets/{code}/cards", {
      params: {
        path: { code },
        query: { page, page_size: pageSize },
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getSetAnalysis(code: string): Promise<SetAnalysisResponse> {
    logger.debug("getSetAnalysis", code);
    const { data, error } = await this.client.GET("/sets/{code}/analysis", {
      params: { path: { code } },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Artists
  // ===========================================================================

  async listArtists(params?: {
    query?: string;
    min_cards?: number;
    limit?: number;
    offset?: number;
  }): Promise<ArtistsListResponse> {
    logger.debug("listArtists", params);
    const { data, error } = await this.client.GET("/artists", {
      params: { query: params },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getArtistCards(name: string): Promise<ArtistCardsResult> {
    logger.debug("getArtistCards", name);
    const { data, error } = await this.client.GET("/artists/{name}/cards", {
      params: { path: { name } },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Collection
  // ===========================================================================

  async parseCollection(
    text: string,
    defaultQuantity: number = 1,
  ): Promise<ParseCollectionResponse> {
    logger.debug("parseCollection", text.length, "chars");
    const { data, error } = await this.client.POST("/collection/parse", {
      body: {
        text,
        default_quantity: defaultQuantity,
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async priceCollection(cards: ParsedCard[]): Promise<PriceCollectionResponse> {
    logger.debug("priceCollection", cards.length, "cards");
    const { data, error } = await this.client.POST("/collection/price", {
      body: { cards },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async getCollectionValue(): Promise<PriceCollectionResponse> {
    logger.debug("getCollectionValue");
    const { data, error } = await this.client.GET("/collection/value");
    if (error) throw this.toApiError(error);
    return data;
  }

  async importCollection(
    text: string,
    mode: "add" | "replace" = "add",
  ): Promise<ImportCollectionResponse> {
    logger.debug("importCollection", text.length, "chars", mode);
    const { data, error } = await this.client.POST("/collection/import", {
      body: { text, mode },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  async listCollection(options: {
    sortBy?: CollectionSortField;
    sortOrder?: "asc" | "desc";
    page?: number;
    pageSize?: number;
  }): Promise<ListCollectionResponse> {
    logger.debug("listCollection", options);
    const { data, error } = await this.client.GET("/collection/list", {
      params: {
        query: {
          sort_by: options.sortBy ?? "name",
          sort_order: options.sortOrder ?? "asc",
          page: options.page ?? 1,
          page_size: options.pageSize ?? 50,
        },
      },
    });
    if (error) throw this.toApiError(error);
    return data;
  }

  // ===========================================================================
  // Error Handling
  // ===========================================================================

  private toApiError(error: unknown): ApiError {
    if (typeof error === "object" && error !== null) {
      const err = error as Record<string, unknown>;
      const detail =
        typeof err.detail === "string"
          ? err.detail
          : JSON.stringify(err.detail ?? err);
      const status = typeof err.status === "number" ? err.status : 500;
      logger.error(`API error ${status}: ${detail}`);
      return new ApiError(`API request failed`, status, detail);
    }
    return new ApiError("Unknown API error", 500, String(error));
  }
}

// Singleton instance
let apiClientInstance: MTGApiClient | null = null;

/**
 * Get the singleton API client instance.
 * Must call initApiClient first.
 */
export function getApiClient(): MTGApiClient {
  if (!apiClientInstance) {
    throw new Error("API client not initialized. Call initApiClient first.");
  }
  return apiClientInstance;
}

/**
 * Initialize the API client with options.
 */
export function initApiClient(options: ApiClientOptions = {}): MTGApiClient {
  apiClientInstance = new MTGApiClient(options);
  return apiClientInstance;
}

/**
 * Initialize the API client from a sidecar manager.
 */
export function initApiClientFromSidecar(
  sidecar: SidecarManager,
): MTGApiClient {
  apiClientInstance = MTGApiClient.fromSidecar(sidecar);
  return apiClientInstance;
}
