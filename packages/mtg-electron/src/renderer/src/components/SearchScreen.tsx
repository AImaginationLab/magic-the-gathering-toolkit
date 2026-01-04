import { useState, useEffect, useCallback } from "react";

import { colors } from "../theme";
import { CardGrid } from "./CardGrid";
import { CardDetailModal } from "./CardDetailModal";
import { SearchFilters } from "./SearchFilters";
import { parseSearchQuery } from "../utils/search-parser";

import type { ReactNode, KeyboardEvent } from "react";
import type { CardData } from "./CardGrid";
import type { CardSummary, Format } from "../../../shared/types/api";
import type { SearchFilterState } from "./SearchFilters";

interface SearchScreenProps {
  initialQuery?: string;
  onOpenGallery?: (cardName: string) => void;
}

/**
 * Convert API CardSummary to CardGrid's CardData format.
 */
function toCardData(card: CardSummary): CardData {
  return {
    uuid: card.uuid ?? card.name,
    name: card.name,
    manaCost: card.mana_cost,
    type: card.type ?? "",
    rarity: card.rarity ?? "common",
    setCode: card.set_code ?? "",
    text: null, // CardSummary doesn't include oracle text
    imageUrl: card.image ?? card.image_small,
    owned: card.owned,
  };
}

const INITIAL_FILTERS: SearchFilterState = {
  colors: [],
  setCodes: [],
  format: null,
  rarity: null,
  type: null,
};

export function SearchScreen({
  initialQuery = "",
  onOpenGallery,
}: SearchScreenProps): ReactNode {
  const [query, setQuery] = useState(initialQuery);
  const [cards, setCards] = useState<CardData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);
  const [filters, setFilters] = useState<SearchFilterState>(INITIAL_FILTERS);
  const [showFilters, setShowFilters] = useState(false);

  // Load recent searches on mount
  useEffect(() => {
    window.electronAPI.store.getRecentSearches().then(setRecentSearches);
  }, []);

  const performSearch = useCallback(
    async (searchQuery: string) => {
      // Allow search with just filters (no text query needed)
      const hasFilters =
        filters.colors.length > 0 ||
        filters.setCodes.length > 0 ||
        filters.format !== null ||
        filters.rarity !== null ||
        filters.type !== null;

      if (!searchQuery.trim() && !hasFilters) return;

      setIsLoading(true);
      setError(null);

      try {
        // Parse the search query into API filters
        const queryFilters = parseSearchQuery(searchQuery);

        // Merge with visual filters (visual filters take precedence for their fields)
        const mergedFilters = {
          ...queryFilters,
          // Colors: merge both sources
          colors:
            filters.colors.length > 0
              ? (filters.colors as ("W" | "U" | "B" | "R" | "G")[])
              : queryFilters.colors,
          // Set: visual filter takes precedence if set
          set_code:
            filters.setCodes.length > 0
              ? filters.setCodes[0].toUpperCase()
              : queryFilters.set_code,
          // Format: visual filter takes precedence if set
          format_legal: (filters.format as Format) ?? queryFilters.format_legal,
          // Rarity: visual filter takes precedence if set
          rarity:
            (filters.rarity as "common" | "uncommon" | "rare" | "mythic") ??
            queryFilters.rarity,
          // Type: visual filter takes precedence if set
          type: filters.type ?? queryFilters.type,
        };

        // Use the HTTP API
        const result = await window.electronAPI.api.cards.search(mergedFilters);

        // Convert CardSummary[] to CardData[]
        const cardData = result.cards.map(toCardData);

        setCards(cardData);
        setTotal(result.total_count ?? result.count);

        // Update recent searches (only for text queries)
        if (searchQuery.trim()) {
          const updated = await window.electronAPI.store.getRecentSearches();
          setRecentSearches(updated);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(`Search failed: ${message}`);
        setCards([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    },
    [filters],
  );

  // Auto-search if initialQuery provided
  useEffect(() => {
    if (initialQuery) {
      performSearch(initialQuery);
    }
  }, [initialQuery, performSearch]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "Enter") {
      performSearch(query);
    }
  };

  const handleRecentClick = (search: string): void => {
    setQuery(search);
    performSearch(search);
  };

  const handleClearRecent = async (): Promise<void> => {
    await window.electronAPI.store.clearRecentSearches();
    setRecentSearches([]);
  };

  const handleCardClick = (card: CardData): void => {
    setSelectedCardName(card.name);
  };

  const handleCloseModal = (): void => {
    setSelectedCardName(null);
  };

  return (
    <div
      className="h-full flex flex-col"
      style={{ background: colors.void.deepest }}
    >
      {/* Search header */}
      <div
        className="p-4 border-b"
        style={{
          background: colors.void.deep,
          borderColor: colors.border.subtle,
        }}
      >
        <div className="max-w-4xl mx-auto">
          {/* Search input row */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search cards... (e.g. Lightning Bolt, t:creature c:R)"
                autoFocus
                className="w-full h-12 px-4 pr-24 text-base font-body"
                style={{
                  background: colors.void.medium,
                  border: `1px solid ${colors.border.standard}`,
                  borderRadius: "4px",
                  color: colors.text.standard,
                  outline: "none",
                }}
              />
              <button
                onClick={() => performSearch(query)}
                disabled={isLoading}
                className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-1.5 font-display text-sm tracking-wide transition-colors duration-150"
                style={{
                  background: colors.gold.standard,
                  color: colors.void.deepest,
                  borderRadius: "3px",
                  opacity: isLoading ? 0.5 : 1,
                }}
              >
                {isLoading ? "Searching..." : "Search"}
              </button>
            </div>

            {/* Filter toggle button */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="h-12 px-4 rounded flex items-center gap-2 transition-colors"
              style={{
                background: showFilters
                  ? colors.gold.standard
                  : colors.void.medium,
                color: showFilters ? colors.void.deepest : colors.text.dim,
                border: `1px solid ${showFilters ? colors.gold.standard : colors.border.standard}`,
              }}
            >
              <i className="ms ms-ability-menace" style={{ fontSize: 14 }} />
              <span className="text-sm font-display">Filters</span>
              {(filters.colors.length > 0 ||
                filters.setCodes.length > 0 ||
                filters.format ||
                filters.rarity ||
                filters.type) && (
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: colors.gold.bright }}
                />
              )}
            </button>
          </div>

          {/* Visual filters bar */}
          {showFilters && (
            <div className="mt-3">
              <SearchFilters filters={filters} onChange={setFilters} />
            </div>
          )}

          {/* Search tips (collapsed when filters shown) */}
          {!showFilters && (
            <div
              className="flex flex-wrap items-center gap-3 mt-2 text-xs"
              style={{ color: colors.text.muted }}
            >
              <span className="font-display" style={{ color: colors.text.dim }}>
                Syntax:
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.mana.white.color }}
                >
                  t:
                </span>
                <span style={{ color: colors.text.dim }}>creature</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.mana.blue.color }}
                >
                  c:
                </span>
                <span style={{ color: colors.text.dim }}>UB</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.mana.black.color }}
                >
                  cmc:
                </span>
                <span style={{ color: colors.text.dim }}>3</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.mana.red.color }}
                >
                  r:
                </span>
                <span style={{ color: colors.text.dim }}>mythic</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.mana.green.color }}
                >
                  set:
                </span>
                <span style={{ color: colors.text.dim }}>MH3</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.gold.standard }}
                >
                  f:
                </span>
                <span style={{ color: colors.text.dim }}>modern</span>
              </span>
              <span>
                <span
                  className="font-mono"
                  style={{ color: colors.text.standard }}
                >
                  text:
                </span>
                <span style={{ color: colors.text.dim }}>"draw a card"</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 overflow-auto p-4">
        {/* Recent searches (show when no results) */}
        {!isLoading &&
          cards.length === 0 &&
          !error &&
          recentSearches.length > 0 && (
            <div className="max-w-2xl mx-auto mb-6">
              <div className="flex items-center justify-between mb-2">
                <span
                  className="text-sm font-display"
                  style={{ color: colors.text.dim }}
                >
                  Recent Searches
                </span>
                <button
                  onClick={handleClearRecent}
                  className="text-xs"
                  style={{ color: colors.text.muted }}
                >
                  Clear
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {recentSearches.map((search) => (
                  <button
                    key={search}
                    onClick={() => handleRecentClick(search)}
                    className="px-3 py-1.5 text-sm transition-colors duration-150"
                    style={{
                      background: colors.void.light,
                      border: `1px solid ${colors.border.subtle}`,
                      borderRadius: "3px",
                      color: colors.text.dim,
                    }}
                  >
                    {search}
                  </button>
                ))}
              </div>
            </div>
          )}

        {/* Error message */}
        {error && (
          <div
            className="max-w-2xl mx-auto mb-4 p-3 rounded text-sm"
            style={{
              background: `${colors.status.error}20`,
              border: `1px solid ${colors.status.error}40`,
              color: colors.status.error,
            }}
          >
            {error}
          </div>
        )}

        {/* Results header */}
        {cards.length > 0 && (
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm" style={{ color: colors.text.dim }}>
              Showing{" "}
              <span style={{ color: colors.gold.standard }}>
                {cards.length}
              </span>
              {total > cards.length && (
                <>
                  {" "}
                  of{" "}
                  <span style={{ color: colors.gold.standard }}>
                    {total.toLocaleString()}
                  </span>
                </>
              )}{" "}
              results for "
              <span style={{ color: colors.text.standard }}>{query}</span>"
            </span>
          </div>
        )}

        {/* Card grid */}
        <CardGrid
          cards={cards}
          onCardClick={handleCardClick}
          isLoading={isLoading}
          emptyMessage={
            query
              ? "No cards found. Try a different search."
              : "Enter a search term to find cards."
          }
        />
      </div>

      {/* Card detail modal */}
      {selectedCardName && (
        <CardDetailModal
          cardName={selectedCardName}
          onClose={handleCloseModal}
          onOpenGallery={onOpenGallery}
        />
      )}
    </div>
  );
}

export default SearchScreen;
