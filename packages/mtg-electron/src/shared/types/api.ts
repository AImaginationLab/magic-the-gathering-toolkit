/**
 * TypeScript types for the mtg-core API.
 *
 * This file contains:
 * 1. Re-exports from generated types (api-generated.ts)
 * 2. Custom types not in the OpenAPI schema (literal types, HealthResponse)
 * 3. Modified types that need different optionality than generated
 */

import type { components } from "./api-generated";

// =============================================================================
// Re-export generated types for convenience
// =============================================================================

// Card types
export type CardSummary = components["schemas"]["CardSummary"];
export type CardDetail = components["schemas"]["CardDetail"];
export type ImageUrls = components["schemas"]["ImageUrls"];
export type Prices = components["schemas"]["Prices"];
export type PurchaseLinks = components["schemas"]["PurchaseLinks"];
export type RelatedLinks = components["schemas"]["RelatedLinks"];

// Search types
export type SearchResult = components["schemas"]["SearchResult"];

// Rulings types
export type RulingEntry = components["schemas"]["RulingEntry"];
export type RulingsResponse = components["schemas"]["RulingsResponse"];

// Printings types
export type PrintingInfo = components["schemas"]["PrintingInfo"];
export type PrintingsResponse = components["schemas"]["PrintingsResponse"];

// Deck types
export type DeckCardInput = components["schemas"]["DeckCardInput"];
export type CardIssue = components["schemas"]["CardIssue"];
export type DeckValidationResult =
  components["schemas"]["DeckValidationResult"];
export type ManaCurveResult = components["schemas"]["ManaCurveResult"];
export type ColorBreakdown = components["schemas"]["ColorBreakdown"];
export type ColorAnalysisResult = components["schemas"]["ColorAnalysisResult"];
export type TypeCount = components["schemas"]["TypeCount"];
export type CompositionResult = components["schemas"]["CompositionResult"];

// Synergy types
export type SynergyResult = components["schemas"]["SynergyResult"];
export type FindSynergiesResult = components["schemas"]["FindSynergiesResult"];
export type ComboCard = components["schemas"]["ComboCard"];
export type Combo = components["schemas"]["Combo"];
export type DetectCombosResult = components["schemas"]["DetectCombosResult"];
export type SuggestedCard = components["schemas"]["SuggestedCard"];
export type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];

// Recommendation types
export type ComboSummary = components["schemas"]["ComboSummary"];
export type DeckSuggestion = components["schemas"]["DeckSuggestion"];

// CommanderMatch is not in generated schema - define manually
export interface CommanderMatch {
  name: string;
  colors: string[];
  archetype: string | null;
  completion_pct: number;
  reasons: string[];
}

// =============================================================================
// Literal Types (not exported from generated schema)
// =============================================================================

export type Color = "W" | "U" | "B" | "R" | "G" | "C";

export type Format =
  | "standard"
  | "modern"
  | "legacy"
  | "vintage"
  | "commander"
  | "pioneer"
  | "pauper"
  | "historic"
  | "brawl"
  | "alchemy"
  | "explorer"
  | "timeless"
  | "oathbreaker"
  | "penny"
  | "duel";

export type Rarity = "common" | "uncommon" | "rare" | "mythic";

export type SortField = "name" | "cmc" | "color" | "rarity" | "type" | "random";
export type SortOrder = "asc" | "desc";

export type IssueType =
  | "not_found"
  | "not_legal"
  | "over_copy_limit"
  | "over_singleton_limit"
  | "outside_color_identity";

export type SynergyType =
  | "keyword"
  | "tribal"
  | "ability"
  | "theme"
  | "archetype";

export type ComboType = "infinite" | "value" | "lock" | "win";

export type SuggestionCategory = "synergy" | "staple" | "upgrade" | "budget";

// =============================================================================
// Modified Input Types (with optional fields that have defaults in API)
// =============================================================================

/**
 * Search input with all fields optional.
 * The generated type requires sort_order, page, and random because they have
 * defaults in the API, but callers shouldn't need to specify them.
 */
export interface SearchCardsInput {
  name?: string | null;
  colors?: Color[] | null;
  color_identity?: Color[] | null;
  type?: string | null;
  subtype?: string | null;
  supertype?: string | null;
  rarity?: Rarity | null;
  set_code?: string | null;
  cmc?: number | null;
  cmc_min?: number | null;
  cmc_max?: number | null;
  power?: string | null;
  toughness?: string | null;
  text?: string | null;
  keywords?: string[] | null;
  format_legal?: Format | null;
  artist?: string | null;
  sort_by?: SortField | null;
  sort_order?: SortOrder;
  page?: number;
  page_size?: number;
  random?: boolean;
  in_collection?: boolean;
}

export interface ValidateDeckInput {
  cards: DeckCardInput[];
  format: Format;
  commander?: string | null;
  check_legality?: boolean;
  check_deck_size?: boolean;
  check_copy_limit?: boolean;
  check_singleton?: boolean;
  check_color_identity?: boolean;
}

export interface AnalyzeDeckInput {
  cards: DeckCardInput[];
  format?: Format | null;
  commander?: string | null;
}

// =============================================================================
// Request Models (matching FastAPI request bodies)
// =============================================================================

export interface CardDetailsRequest {
  name: string;
}

export interface CardRulingsRequest {
  name: string;
}

export interface FindSynergiesRequest {
  card_name: string;
  limit?: number;
  format_legal?: string | null;
}

export interface DetectCombosRequest {
  card_names: string[];
}

export interface CombosForCardRequest {
  card_name: string;
}

export interface SuggestCardsRequest {
  deck_cards: string[];
  format_legal?: string | null;
  budget_max?: number | null;
  max_results?: number;
}

export interface FindCommandersRequest {
  collection_cards: string[];
  colors?: string[] | null;
  creature_type?: string | null;
  theme?: string | null;
  limit?: number;
}

export interface FindDecksRequest {
  collection_cards: string[];
  colors?: string[] | null;
  creature_type?: string | null;
  theme?: string | null;
  min_completion?: number;
  limit?: number;
}

// =============================================================================
// Types not in OpenAPI schema
// =============================================================================

export interface HealthResponse {
  status: string;
}
