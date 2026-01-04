/**
 * Deck Suggestions Screen - Redesigned
 * Three modes: Card Suggestions, Commander Finder, and Deck Ideas
 * Features rich filtering, visual components, and discovery-focused UX
 */

import { useState, useCallback, useEffect } from "react";
import { createPortal } from "react-dom";
import { colors, synergyColors, gradients } from "../theme";
import { CardDetailModal } from "./CardDetailModal";
import {
  SuggestionsTabs,
  FilterPanel,
  CardSuggestionsPanel,
  DeckArchetypeCard,
} from "./DeckSuggestions";
import type { FilterState } from "./DeckSuggestions";

import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

// Session storage keys for persisting state
const STORAGE_KEYS = {
  filters: "deck-suggestions-filters",
  activeTab: "deck-suggestions-tab",
  cardInput: "deck-suggestions-card-input",
  hasSearched: "deck-suggestions-has-searched",
  cardSuggestions: "deck-suggestions-card-results",
  commanders: "deck-suggestions-commander-results",
  deckIdeas: "deck-suggestions-deck-results",
};

// Use generated types from OpenAPI schema
type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];
type DeckSuggestion = components["schemas"]["DeckSuggestion"];

// CommanderMatch type (not in OpenAPI schema, defined in preload)
interface CommanderMatch {
  name: string;
  colors: string[];
  archetype: string | null;
  completion_pct: number;
  reasons: string[];
}

type TabMode = "suggestions" | "commanders" | "decks";

// Initial filter state - defaults to entire collection
const INITIAL_FILTERS: FilterState = {
  cardSource: "collection",
  selectedDeckId: null,
  activeColors: [],
  archetype: null,
  archetypes: [],
  tribal: null,
  tribals: [],
  setCodes: [],
  format: null,
  ownedOnly: true,
} as FilterState;

// Helper to safely get from session storage
function getStoredValue<T>(key: string, defaultValue: T): T {
  try {
    const stored = sessionStorage.getItem(key);
    if (stored) {
      return JSON.parse(stored) as T;
    }
  } catch {
    // Ignore parse errors
  }
  return defaultValue;
}

// Helper to save to session storage
function setStoredValue<T>(key: string, value: T): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage errors (e.g., quota exceeded)
  }
}

export function DeckSuggestionsScreen(): ReactNode {
  // Tab state - restore from session
  const [activeTab, setActiveTab] = useState<TabMode>(() =>
    getStoredValue(STORAGE_KEYS.activeTab, "decks" as TabMode),
  );

  // Filter state (shared across tabs) - restore from session
  const [filters, setFilters] = useState<FilterState>(() =>
    getStoredValue(STORAGE_KEYS.filters, INITIAL_FILTERS),
  );

  // Track if user has initiated a search - restore from session
  const [hasSearched, setHasSearched] = useState(() =>
    getStoredValue(STORAGE_KEYS.hasSearched, false),
  );

  // Card suggestions state - restore from session
  const [cardSuggestions, setCardSuggestions] =
    useState<SuggestCardsResult | null>(() =>
      getStoredValue(STORAGE_KEYS.cardSuggestions, null),
    );
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [suggestionsError, setSuggestionsError] = useState<string | null>(null);

  // Commander finder state - restore from session
  const [commanders, setCommanders] = useState<CommanderMatch[]>(() =>
    getStoredValue(STORAGE_KEYS.commanders, []),
  );
  const [isLoadingCommanders, setIsLoadingCommanders] = useState(false);
  const [commandersError, setCommandersError] = useState<string | null>(null);

  // Deck ideas state - restore from session
  const [deckIdeas, setDeckIdeas] = useState<DeckSuggestion[]>(() =>
    getStoredValue(STORAGE_KEYS.deckIdeas, []),
  );
  const [isLoadingDecks, setIsLoadingDecks] = useState(false);
  const [decksError, setDecksError] = useState<string | null>(null);

  // Card detail modal state
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);

  // Persist state changes to session storage
  useEffect(() => {
    setStoredValue(STORAGE_KEYS.activeTab, activeTab);
  }, [activeTab]);

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.filters, filters);
  }, [filters]);

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.hasSearched, hasSearched);
  }, [hasSearched]);

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.cardSuggestions, cardSuggestions);
  }, [cardSuggestions]);

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.commanders, commanders);
  }, [commanders]);

  useEffect(() => {
    setStoredValue(STORAGE_KEYS.deckIdeas, deckIdeas);
  }, [deckIdeas]);

  // Fetch commanders - uses collection when cardSource is "collection", all cards otherwise
  const fetchCommanders = useCallback(async (): Promise<void> => {
    setIsLoadingCommanders(true);
    setCommandersError(null);

    try {
      const useCollection = filters.cardSource === "collection";

      const result =
        await window.electronAPI.api.recommendations.findCommanders({
          useCollection,
          limit: 15,
          colors:
            filters.activeColors.length > 0 ? filters.activeColors : undefined,
          creatureTypes:
            filters.tribals.length > 0 ? filters.tribals : undefined,
          creatureType:
            filters.tribals.length === 0 && filters.tribal
              ? filters.tribal
              : undefined,
          themes:
            filters.archetypes.length > 0 ? filters.archetypes : undefined,
          theme:
            filters.archetypes.length === 0 && filters.archetype
              ? filters.archetype
              : undefined,
          format: filters.format || undefined,
          setCodes: filters.setCodes.length > 0 ? filters.setCodes : undefined,
        });
      setCommanders(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setCommandersError(`Failed to find commanders: ${message}`);
    } finally {
      setIsLoadingCommanders(false);
    }
  }, [filters]);

  // Fetch deck ideas - uses collection when cardSource is "collection", all cards otherwise
  const fetchDeckIdeas = useCallback(async (): Promise<void> => {
    setIsLoadingDecks(true);
    setDecksError(null);

    try {
      const useCollection = filters.cardSource === "collection";

      const result = await window.electronAPI.api.recommendations.findDecks({
        useCollection,
        limit: 10,
        minCompletion: 0.2,
        colors:
          filters.activeColors.length > 0 ? filters.activeColors : undefined,
        creatureTypes: filters.tribals.length > 0 ? filters.tribals : undefined,
        creatureType:
          filters.tribals.length === 0 && filters.tribal
            ? filters.tribal
            : undefined,
        themes: filters.archetypes.length > 0 ? filters.archetypes : undefined,
        theme:
          filters.archetypes.length === 0 && filters.archetype
            ? filters.archetype
            : undefined,
        format: filters.format || undefined,
        setCodes: filters.setCodes.length > 0 ? filters.setCodes : undefined,
      });
      setDeckIdeas(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setDecksError(`Failed to find deck ideas: ${message}`);
    } finally {
      setIsLoadingDecks(false);
    }
  }, [filters]);

  // Fetch card suggestions for a specific deck
  const fetchSuggestions = useCallback(async (): Promise<void> => {
    // Card suggestions requires a deck to be selected
    if (!filters.selectedDeckId) {
      setCardSuggestions(null);
      setSuggestionsError(null);
      return;
    }

    setIsLoadingSuggestions(true);
    setSuggestionsError(null);

    try {
      // Get the deck's cards first
      const deckDetails = await window.electronAPI.decks.get(
        filters.selectedDeckId,
      );
      const deckCardNames = deckDetails.cards.map((c) => c.card_name);

      const result = await window.electronAPI.api.recommendations.suggestCards(
        deckCardNames,
        {
          maxResults: 30,
          setCodes: filters.setCodes.length > 0 ? filters.setCodes : undefined,
          themes:
            filters.archetypes.length > 0 ? filters.archetypes : undefined,
          creatureTypes:
            filters.tribals.length > 0 ? filters.tribals : undefined,
        },
      );
      setCardSuggestions(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setSuggestionsError(`Failed to get suggestions: ${message}`);
    } finally {
      setIsLoadingSuggestions(false);
    }
  }, [filters]);

  // Manual fetch trigger - only called when user clicks "Generate"
  const handleFetch = (): void => {
    setHasSearched(true);
    switch (activeTab) {
      case "suggestions":
        fetchSuggestions();
        break;
      case "commanders":
        fetchCommanders();
        break;
      case "decks":
        fetchDeckIdeas();
        break;
    }
  };

  // View card details
  const handleViewCard = useCallback((cardName: string) => {
    setSelectedCardName(cardName);
  }, []);

  // Add suggestion to user's decks
  const handleAddToDeck = useCallback(async (suggestion: DeckSuggestion) => {
    try {
      // Create the deck
      const result = await window.electronAPI.decks.create({
        name: suggestion.name,
        format: suggestion.format || "commander",
        commander: suggestion.commander || null,
        description: suggestion.reasons?.join(". ") || null,
      });

      // Add all owned cards to the deck
      const deckId = result.id;
      const cardsToAdd = suggestion.key_cards_owned || [];

      for (const cardName of cardsToAdd) {
        try {
          await window.electronAPI.decks.addCard(deckId, {
            card_name: cardName,
            quantity: 1,
            is_commander: cardName === suggestion.commander,
          });
        } catch (err) {
          console.error(`Failed to add card ${cardName}:`, err);
        }
      }

      // Show success (could add a toast notification here)
      alert(
        `Deck "${suggestion.name}" created with ${cardsToAdd.length} cards!`,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      alert(`Failed to create deck: ${message}`);
    }
  }, []);

  return (
    <div
      className="h-full flex flex-col relative overflow-hidden"
      style={{ background: colors.void.deepest }}
    >
      {/* Ambient background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ opacity: 0.3 }}
      >
        <div
          className="absolute top-1/3 left-1/4 w-96 h-96 rounded-full blur-3xl"
          style={{
            background: gradients.deckSuggestion,
            animation: "pulse-glow 4s ease-in-out infinite",
          }}
        />
      </div>

      {/* Header */}
      <header
        className="relative z-10 p-4 border-b"
        style={{
          background: `linear-gradient(180deg, ${colors.void.deep} 0%, ${colors.void.deepest} 100%)`,
          borderColor: colors.border.subtle,
        }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center gap-4 mb-4">
            {/* Icon */}
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{
                background: colors.void.medium,
                border: `1px solid ${synergyColors.strategy.color}40`,
                boxShadow: `0 0 20px ${synergyColors.strategy.glow}`,
              }}
            >
              <i
                className="ms ms-saga"
                style={{ color: synergyColors.strategy.color, fontSize: 20 }}
              />
            </div>

            {/* Title */}
            <div>
              <h1
                className="font-display text-xl tracking-widest"
                style={{ color: colors.gold.standard }}
              >
                DECK SUGGESTIONS
              </h1>
              <p className="text-xs" style={{ color: colors.text.muted }}>
                Discover cards, commanders, and deck ideas
              </p>
            </div>
          </div>

          {/* Tab navigation */}
          <SuggestionsTabs activeTab={activeTab} onChange={setActiveTab} />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* Filter bar - horizontal, above the fold */}
        <FilterPanel
          filters={filters}
          onChange={setFilters}
          onSearch={handleFetch}
          activeTab={activeTab}
        />

        {/* Results area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tab content */}
          <div className="flex-1 overflow-auto p-6">
            {activeTab === "suggestions" && (
              <CardSuggestionsView
                result={cardSuggestions}
                isLoading={isLoadingSuggestions}
                error={suggestionsError}
                onViewCard={handleViewCard}
                hasSearched={hasSearched}
                onGenerate={handleFetch}
              />
            )}

            {activeTab === "commanders" && (
              <CommanderFinderView
                commanders={commanders}
                isLoading={isLoadingCommanders}
                error={commandersError}
                onViewCard={handleViewCard}
                hasSearched={hasSearched}
                onGenerate={handleFetch}
              />
            )}

            {activeTab === "decks" && (
              <DeckIdeasView
                decks={deckIdeas}
                isLoading={isLoadingDecks}
                error={decksError}
                onViewCard={handleViewCard}
                onAddToDeck={handleAddToDeck}
                hasSearched={hasSearched}
                onGenerate={handleFetch}
              />
            )}
          </div>
        </div>
      </main>

      {/* Card detail modal */}
      {selectedCardName && (
        <CardDetailModal
          cardName={selectedCardName}
          onClose={() => setSelectedCardName(null)}
        />
      )}
    </div>
  );
}

// Card Suggestions View - Redesigned with editorial layout
function CardSuggestionsView({
  result,
  isLoading,
  error,
  onViewCard,
  hasSearched,
  onGenerate,
}: {
  result: SuggestCardsResult | null;
  isLoading: boolean;
  error: string | null;
  onViewCard: (name: string) => void;
  hasSearched: boolean;
  onGenerate: () => void;
}): ReactNode {
  if (isLoading) {
    return <LoadingState message="Analyzing deck and finding suggestions..." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  // Show "Ready to Generate" state before user has searched
  if (!hasSearched) {
    return (
      <ReadyToGenerateState
        title="Get Card Suggestions"
        description="Select a deck from the dropdown above, then click Generate to get personalized card suggestions based on your deck's themes and synergies."
        onGenerate={onGenerate}
      />
    );
  }

  if (!result || !result.suggestions || result.suggestions.length === 0) {
    return (
      <EmptyState
        icon="ms-instant"
        title="No Suggestions Found"
        message="Make sure you've selected a deck from the dropdown above. We'll analyze its themes and recommend cards that synergize with your strategy."
        onRetry={onGenerate}
      />
    );
  }

  return <CardSuggestionsPanel result={result} onViewCard={onViewCard} />;
}

// Synergy indicator colors (matching DeckImpactTooltip)
const synergyIndicatorColors = {
  owned: "#4CAF50", // Material green - cards you own
  tribal: "#50B050", // Muted green
  strategy: "#E67300", // Warm orange
  lands: "#8B7355", // Brown for lands
  default: "#40C4D0", // Soft cyan
};

// Parse synergy reason to determine type and color
function parseSynergyType(reason: string): {
  type: string;
  color: string;
  icon: string;
} {
  const lower = reason.toLowerCase();
  if (lower.includes("you own") || lower.includes("cards in")) {
    return { type: "owned", color: synergyIndicatorColors.owned, icon: "✓" };
  }
  if (lower.includes("tribal") || lower.includes("creature type")) {
    return { type: "tribal", color: synergyIndicatorColors.tribal, icon: "★" };
  }
  if (
    lower.includes("strategy") ||
    lower.includes("theme") ||
    lower.includes("archetype")
  ) {
    return {
      type: "strategy",
      color: synergyIndicatorColors.strategy,
      icon: "↑",
    };
  }
  if (lower.includes("land") || lower.includes("basic")) {
    return { type: "lands", color: synergyIndicatorColors.lands, icon: "◆" };
  }
  return { type: "default", color: synergyIndicatorColors.default, icon: "•" };
}

// Synergy tooltip for commander hover - styled like DeckImpactTooltip
function CommanderSynergyTooltip({
  commanderName,
  archetype,
  reasons,
  isLoading,
}: {
  commanderName: string;
  archetype: string | null;
  reasons: string[];
  isLoading?: boolean;
}): ReactNode {
  if (isLoading) {
    return (
      <div
        className="p-3 rounded-lg"
        style={{
          background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
        }}
      >
        <div className="text-xs" style={{ color: colors.text.muted }}>
          Loading synergies...
        </div>
      </div>
    );
  }

  if (!reasons || reasons.length === 0) {
    return (
      <div
        className="p-3 rounded-lg"
        style={{
          background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
        }}
      >
        <div
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          {commanderName}
        </div>
        <div className="text-xs mt-1" style={{ color: colors.text.muted }}>
          No synergies detected
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-3 rounded-lg space-y-2"
      style={{
        background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
        border: `1px solid ${colors.border.standard}`,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
      }}
    >
      {/* Header */}
      <div
        className="text-xs font-display uppercase tracking-wider pb-1 border-b"
        style={{
          color: colors.gold.standard,
          borderColor: colors.border.subtle,
        }}
      >
        {commanderName}
      </div>

      {/* Archetype badge */}
      {archetype && (
        <div
          className="flex items-center gap-2 text-sm font-medium"
          style={{ color: synergyIndicatorColors.strategy }}
        >
          <span>↑</span>
          <span>{archetype} strategy</span>
        </div>
      )}

      {/* Synergy reasons with icons */}
      <div className="space-y-1.5">
        {reasons.slice(0, 5).map((reason, idx) => {
          const { color, icon } = parseSynergyType(reason);
          return (
            <div
              key={idx}
              className="flex items-start gap-2 text-sm"
              style={{ color }}
            >
              <span>{icon}</span>
              <span>{reason}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Synergy badges for inline display (like DeckImpactBadges)
function CommanderSynergyBadges({
  archetype,
  reasons,
}: {
  archetype: string | null;
  reasons: string[];
}): ReactNode {
  const badges: Array<{ text: string; color: string }> = [];

  // Add archetype badge
  if (archetype) {
    badges.push({ text: archetype, color: synergyIndicatorColors.strategy });
  }

  // Parse first couple reasons for badge-worthy content
  for (const reason of reasons.slice(0, 3)) {
    const lower = reason.toLowerCase();

    // Extract card counts
    const countMatch = reason.match(/(\d+)\s+cards?\s+in/i);
    if (countMatch) {
      badges.push({
        text: `${countMatch[1]} cards`,
        color: synergyIndicatorColors.owned,
      });
      continue;
    }

    // Extract tribal info
    const tribalMatch = reason.match(/(\w+)\s+tribal/i);
    if (
      tribalMatch &&
      !badges.some((b) => b.text.toLowerCase().includes("tribal"))
    ) {
      badges.push({
        text: `${tribalMatch[1]} Tribal`,
        color: synergyIndicatorColors.tribal,
      });
      continue;
    }

    // Owned legendary
    if (lower.includes("you own this")) {
      badges.push({ text: "Owned", color: synergyIndicatorColors.owned });
    }
  }

  if (badges.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {badges.slice(0, 3).map((badge, idx) => (
        <span
          key={idx}
          className="text-xs px-1.5 py-0.5 rounded font-medium"
          style={{
            color: badge.color,
            background: `${badge.color}15`,
            border: `1px solid ${badge.color}30`,
          }}
        >
          {badge.text}
        </span>
      ))}
    </div>
  );
}

// Mana colors for commander color identity
const MANA_COLORS: Record<string, { color: string; name: string }> = {
  W: { color: colors.mana.white.color, name: "White" },
  U: { color: colors.mana.blue.color, name: "Blue" },
  B: { color: colors.mana.black.color, name: "Black" },
  R: { color: colors.mana.red.color, name: "Red" },
  G: { color: colors.mana.green.color, name: "Green" },
};

// Commander Finder View - List style like DeckBuilder search results
function CommanderFinderView({
  commanders,
  isLoading,
  error,
  onViewCard,
  hasSearched,
  onGenerate,
}: {
  commanders: CommanderMatch[];
  isLoading: boolean;
  error: string | null;
  onViewCard: (name: string) => void;
  hasSearched: boolean;
  onGenerate: () => void;
}): ReactNode {
  const [hoveredCommander, setHoveredCommander] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [cardImages, setCardImages] = useState<Record<string, string>>({});
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  // Fetch card images for commanders
  useEffect(() => {
    if (commanders.length === 0) return;

    const fetchImages = async (): Promise<void> => {
      const images: Record<string, string> = {};
      await Promise.all(
        commanders.map(async (cmd) => {
          try {
            const details = await window.electronAPI.api.cards.getByName(
              cmd.name,
            );
            if (details?.images?.small) {
              images[cmd.name] = details.images.small;
            }
          } catch {
            // Ignore errors
          }
        }),
      );
      setCardImages(images);
    };

    fetchImages();
  }, [commanders]);

  // Fetch preview image when hovering
  useEffect(() => {
    if (!hoveredCommander) {
      setPreviewImageUrl(null);
      return;
    }

    const smallImage = cardImages[hoveredCommander];
    if (smallImage) {
      const normalUrl = smallImage.replace("/small/", "/normal/");
      setPreviewImageUrl(normalUrl);
    }

    const fetchImage = async (): Promise<void> => {
      try {
        const details =
          await window.electronAPI.api.cards.getByName(hoveredCommander);
        if (details?.images?.normal) {
          setPreviewImageUrl(details.images.normal);
        } else if (details?.images?.large) {
          setPreviewImageUrl(details.images.large);
        }
      } catch {
        // Keep existing image
      }
    };

    fetchImage();
  }, [hoveredCommander, cardImages]);

  if (isLoading) {
    return <LoadingState message="Finding commanders for your collection..." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  // Show "Ready to Generate" state before user has searched
  if (!hasSearched) {
    return (
      <ReadyToGenerateState
        title="Find Your Commander"
        description="Discover legendary creatures that synergize with the cards you own. We'll match commanders to your collection and show completion percentage."
        onGenerate={onGenerate}
      />
    );
  }

  if (commanders.length === 0) {
    return (
      <EmptyState
        icon="ms-planeswalker"
        title="No Commanders Found"
        message="No matching commanders found with your current filters. Try adjusting the color or tribal filters."
        onRetry={onGenerate}
      />
    );
  }

  const hoveredCmd = commanders.find((c) => c.name === hoveredCommander);

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: colors.void.deep,
        border: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Results header */}
      <div
        className="px-4 py-2 border-b flex items-center justify-between"
        style={{ borderColor: colors.border.subtle }}
      >
        <span className="text-sm" style={{ color: colors.text.muted }}>
          {commanders.length} commanders found
        </span>
      </div>

      {/* Results list */}
      <div className="max-h-[600px] overflow-auto">
        {commanders.map((commander) => {
          const isHovered = hoveredCommander === commander.name;
          const imageUrl = cardImages[commander.name];

          return (
            <div
              key={commander.name}
              className="flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors"
              style={{
                borderBottom: `1px solid ${colors.border.subtle}`,
                background: isHovered ? colors.void.light : "transparent",
              }}
              onClick={() => onViewCard(commander.name)}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const tooltipWidth = 280;
                const tooltipHeight = 200;

                // Try to position to the right of the item
                let x = rect.right + 8;
                let y = rect.top;

                // If tooltip would go off-screen right, position to the left
                if (x + tooltipWidth > window.innerWidth - 20) {
                  x = rect.left - tooltipWidth - 8;
                }

                // If still off-screen (left), center horizontally
                if (x < 20) {
                  x = Math.max(20, (window.innerWidth - tooltipWidth) / 2);
                }

                // Keep tooltip within vertical bounds
                if (y + tooltipHeight > window.innerHeight - 20) {
                  y = window.innerHeight - tooltipHeight - 20;
                }

                setTooltipPosition({ x, y });
                setHoveredCommander(commander.name);
              }}
              onMouseLeave={() => {
                setHoveredCommander(null);
                setTooltipPosition(null);
              }}
            >
              {/* Card image thumbnail */}
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt=""
                  className="w-10 h-14 rounded object-cover"
                  loading="lazy"
                  style={{ border: `1px solid ${colors.border.subtle}` }}
                />
              ) : (
                <div
                  className="w-10 h-14 rounded flex items-center justify-center"
                  style={{
                    background: colors.void.medium,
                    border: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  <i
                    className="ms ms-planeswalker"
                    style={{ color: colors.text.muted, fontSize: 16 }}
                  />
                </div>
              )}

              {/* Commander info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="text-sm font-display truncate"
                    style={{ color: colors.gold.standard }}
                  >
                    {commander.name}
                  </span>
                  {/* Color identity */}
                  <div className="flex items-center gap-0.5">
                    {commander.colors.length === 0 ? (
                      <i
                        className="ms ms-c ms-cost"
                        style={{ color: "#bab1ab", fontSize: 12 }}
                        title="Colorless"
                      />
                    ) : (
                      commander.colors.map((c) => {
                        const manaInfo = MANA_COLORS[c];
                        if (!manaInfo) return null;
                        return (
                          <i
                            key={c}
                            className={`ms ms-${c.toLowerCase()} ms-cost`}
                            style={{ color: manaInfo.color, fontSize: 12 }}
                            title={manaInfo.name}
                          />
                        );
                      })
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {/* Synergy badges */}
                  <CommanderSynergyBadges
                    archetype={commander.archetype}
                    reasons={commander.reasons}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Card preview panel */}
      {hoveredCommander && previewImageUrl && hoveredCmd && (
        <div
          className="fixed right-6 top-1/2 -translate-y-1/2 z-40"
          style={{ pointerEvents: "none", width: 280 }}
        >
          <div
            className="p-3 rounded-xl"
            style={{
              background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
              border: `1px solid ${colors.border.standard}`,
              boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 60px ${colors.gold.glow}20`,
            }}
          >
            <img
              src={previewImageUrl}
              alt={hoveredCommander}
              className="rounded-lg w-full"
              style={{
                boxShadow: `0 4px 16px rgba(0,0,0,0.4)`,
              }}
            />
            <div className="mt-3 text-center">
              <div
                className="font-display text-sm tracking-wide truncate px-1"
                style={{ color: colors.gold.standard }}
                title={hoveredCommander}
              >
                {hoveredCommander}
              </div>
              <div className="flex items-center justify-center gap-1 mt-1">
                {hoveredCmd.colors.length === 0 ? (
                  <i
                    className="ms ms-c ms-cost"
                    style={{ color: "#bab1ab", fontSize: 14 }}
                  />
                ) : (
                  hoveredCmd.colors.map((c) => {
                    const manaInfo = MANA_COLORS[c];
                    if (!manaInfo) return null;
                    return (
                      <i
                        key={c}
                        className={`ms ms-${c.toLowerCase()} ms-cost`}
                        style={{ color: manaInfo.color, fontSize: 14 }}
                      />
                    );
                  })
                )}
              </div>
              {hoveredCmd.archetype && (
                <div
                  className="mt-2 text-xs"
                  style={{ color: synergyIndicatorColors.strategy }}
                >
                  {hoveredCmd.archetype}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Hover tooltip - rendered via portal */}
      {hoveredCommander &&
        tooltipPosition &&
        hoveredCmd &&
        createPortal(
          <div
            className="pointer-events-none"
            style={{
              position: "fixed",
              left: tooltipPosition.x,
              top: tooltipPosition.y,
              width: 280,
              zIndex: 9999,
            }}
          >
            <CommanderSynergyTooltip
              commanderName={hoveredCmd.name}
              archetype={hoveredCmd.archetype}
              reasons={hoveredCmd.reasons}
            />
          </div>,
          document.body,
        )}
    </div>
  );
}

// Deck Ideas View
function DeckIdeasView({
  decks,
  isLoading,
  error,
  onViewCard,
  onAddToDeck,
  hasSearched,
  onGenerate,
}: {
  decks: DeckSuggestion[];
  isLoading: boolean;
  error: string | null;
  onViewCard: (name: string) => void;
  onAddToDeck: (deck: DeckSuggestion) => void;
  hasSearched: boolean;
  onGenerate: () => void;
}): ReactNode {
  if (isLoading) {
    return (
      <LoadingState message="Finding buildable decks from your collection..." />
    );
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  // Show "Ready to Generate" state before user has searched
  if (!hasSearched) {
    return (
      <ReadyToGenerateState
        title="Discover Deck Ideas"
        description="Analyze your collection to find Commander decks you can build. We'll look at your cards, detect synergies, and suggest complete deck archetypes."
        onGenerate={onGenerate}
      />
    );
  }

  if (decks.length === 0) {
    return (
      <EmptyState
        icon="ms-saga"
        title="No Decks Found"
        message="No buildable decks found with your current filters. Try adjusting the color or archetype filters, or add more cards to your collection."
        onRetry={onGenerate}
      />
    );
  }

  return (
    <div className="space-y-4">
      {decks.map((deck, idx) => (
        <DeckArchetypeCard
          key={`${deck.name}-${idx}`}
          deck={deck}
          onViewCard={onViewCard}
          onAddToDeck={onAddToDeck}
        />
      ))}
    </div>
  );
}

// Loading state with animated spinner and elapsed time
function LoadingState({ message }: { message: string }): ReactNode {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center py-16">
      {/* Animated spinner */}
      <div
        className="relative w-20 h-20"
        style={{
          animation: "spin 2s linear infinite",
        }}
      >
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: `3px solid ${colors.void.lighter}`,
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: `3px solid transparent`,
            borderTopColor: colors.gold.standard,
            borderRightColor: colors.gold.dim,
          }}
        />
        {/* Center icon */}
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{ animation: "spin 2s linear infinite reverse" }}
        >
          <i
            className="ms ms-ability-constellation"
            style={{ color: colors.gold.standard, fontSize: 24 }}
          />
        </div>
      </div>

      <p
        className="mt-6 text-sm font-display tracking-wide"
        style={{ color: colors.text.standard }}
      >
        {message.toUpperCase()}
      </p>

      {/* Elapsed time */}
      <p
        className="mt-2 text-xs font-mono"
        style={{ color: colors.text.muted }}
      >
        {formatTime(elapsedSeconds)} elapsed
      </p>

      {/* Helpful tip after 5 seconds */}
      {elapsedSeconds >= 5 && (
        <p
          className="mt-4 text-xs max-w-xs text-center"
          style={{ color: colors.text.muted, opacity: 0.7 }}
        >
          Analyzing your collection and finding the best matches...
        </p>
      )}
    </div>
  );
}

// Error state
function ErrorState({ message }: { message: string }): ReactNode {
  return (
    <div
      className="p-4 rounded-lg"
      style={{
        background: `${colors.status.error}15`,
        border: `1px solid ${colors.status.error}40`,
      }}
    >
      <p className="text-sm" style={{ color: colors.status.error }}>
        {message}
      </p>
    </div>
  );
}

// Empty state with optional retry button
function EmptyState({
  icon,
  title,
  message,
  onRetry,
}: {
  icon: string;
  title: string;
  message: string;
  onRetry?: () => void;
}): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
      <div
        className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <i
          className={`ms ${icon}`}
          style={{ fontSize: 28, color: colors.text.muted, opacity: 0.5 }}
        />
      </div>
      <h3
        className="font-display text-base mb-2"
        style={{ color: colors.text.dim }}
      >
        {title}
      </h3>
      <p className="text-sm max-w-md mb-4" style={{ color: colors.text.muted }}>
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-lg text-sm transition-all"
          style={{
            background: colors.void.lighter,
            border: `1px solid ${colors.border.standard}`,
            color: colors.text.dim,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = colors.gold.standard;
            e.currentTarget.style.color = colors.gold.standard;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = colors.border.standard;
            e.currentTarget.style.color = colors.text.dim;
          }}
        >
          Try Different Filters
        </button>
      )}
    </div>
  );
}

// Ready to generate state - shown before user initiates search
function ReadyToGenerateState({
  title,
  description,
  onGenerate,
}: {
  title: string;
  description: string;
  onGenerate: () => void;
}): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
      <div
        className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.gold.standard}40`,
        }}
      >
        <i
          className="ms ms-saga"
          style={{ fontSize: 32, color: colors.gold.standard }}
        />
      </div>
      <h3
        className="font-display text-lg mb-3"
        style={{ color: colors.text.bright }}
      >
        {title}
      </h3>
      <p className="text-sm max-w-md mb-6" style={{ color: colors.text.muted }}>
        {description}
      </p>
      <button
        onClick={onGenerate}
        className="px-5 py-2.5 rounded-lg font-display text-sm tracking-wide transition-all"
        style={{
          background: colors.gold.standard,
          color: colors.void.deepest,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = colors.gold.bright;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = colors.gold.standard;
        }}
      >
        Generate
      </button>
    </div>
  );
}

export default DeckSuggestionsScreen;
