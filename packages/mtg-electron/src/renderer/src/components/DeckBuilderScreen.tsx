import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import * as d3 from "d3";

import { colors, getRarityColor } from "../theme";
import { getFormatColor } from "../utils/formatUtils";
import { getCardCategory, getSubtype } from "../utils/cardUtils";
import { ManaCost } from "./ManaSymbols";
import { ComboDetectionPanel } from "./ComboDetectionPanel";
import { CardDetailModal } from "./CardDetailModal";
import { DeckImpactBadges, DeckImpactTooltip } from "./DeckImpactTooltip";
import { SearchFilters, type SearchFilterState } from "./SearchFilters";

import type { ReactNode } from "react";
import type { Format } from "../../../shared/types/api";
import type { components } from "../../../shared/types/api-generated";

// Types - matches DeckCardResponse from API (now enriched with card data)
interface DeckCard {
  card_name: string;
  quantity: number;
  is_sideboard: boolean;
  is_maybeboard: boolean;
  is_commander: boolean;
  set_code: string | null;
  collector_number: string | null;
  // Enriched card data from API (optional - may be undefined if card not found)
  mana_cost?: string | null;
  cmc?: number | null;
  type_line?: string | null;
  rarity?: string | null;
  flavor_name?: string | null;
  colors?: string[] | null;
  image_small?: string | null;
}

// Board type for the deck list tabs
type BoardType = "mainboard" | "sideboard" | "maybeboard";

interface Deck {
  id: number;
  name: string;
  format: string | null;
  commander: string | null;
  description: string | null;
  cards: DeckCard[];
}

interface CardSearchResult {
  name: string;
  mana_cost?: string | null;
  type?: string | null;
  cmc?: number | null;
  rarity?: string | null;
  image_small?: string | null;
  set_code?: string | null;
}

interface ManaCurveData {
  curve: Record<string, number>;
  average_cmc: number;
  land_count: number;
  nonland_count: number;
}

interface ColorData {
  breakdown: Array<{
    color: string;
    color_name: string;
    card_count: number;
    mana_symbols: number;
  }>;
}

interface DeckTheme {
  name: string;
  card_count: number;
  description?: string | null;
}

interface SynergyPair {
  card1: string;
  card2: string;
  reason: string;
  category: string;
}

interface MatchupInfo {
  strong_against?: string[];
  weak_against?: string[];
}

interface DeckHealthData {
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
  top_keywords?: Array<{ keyword: string; count: number }>;
  issues?: Array<{ message: string; severity: "warning" | "error" }>;
  archetype_traits?: string[];
  // New fields for themes, matchups, synergies (optional per API schema)
  themes?: DeckTheme[];
  dominant_tribe?: string | null;
  tribal_count?: number;
  matchups?: MatchupInfo | null;
  synergy_pairs?: SynergyPair[];
}

interface PriceData {
  total_price: number | null;
  mainboard_price: number | null;
  sideboard_price: number | null;
  average_card_price: number | null;
  most_expensive: Array<{ name: string; price: number }>;
  missing_prices: string[];
}

interface DeckBuilderScreenProps {
  deckId: number;
  onBack: () => void;
}

// Card type categories for grouping
const TYPE_ORDER = [
  "Commander",
  "Creature",
  "Planeswalker",
  "Instant",
  "Sorcery",
  "Artifact",
  "Enchantment",
  "Land",
  "Other",
];

// Type icon and color mapping using mana-font
const TYPE_CONFIG: Record<
  string,
  { icon: string; color: string; manaClass: string }
> = {
  Commander: {
    icon: "commander",
    color: colors.gold.standard,
    manaClass: "ms-commander",
  },
  Creature: {
    icon: "creature",
    color: colors.mana.green.color,
    manaClass: "ms-creature",
  },
  Planeswalker: {
    icon: "planeswalker",
    color: colors.gold.bright,
    manaClass: "ms-planeswalker",
  },
  Instant: {
    icon: "instant",
    color: colors.mana.blue.color,
    manaClass: "ms-instant",
  },
  Sorcery: {
    icon: "sorcery",
    color: colors.mana.red.color,
    manaClass: "ms-sorcery",
  },
  Artifact: {
    icon: "artifact",
    color: "#9fa6a8",
    manaClass: "ms-artifact",
  },
  Enchantment: {
    icon: "enchantment",
    color: colors.mana.white.color,
    manaClass: "ms-enchantment",
  },
  Land: { icon: "land", color: "#8b7355", manaClass: "ms-land" },
  Other: { icon: "c", color: colors.text.muted, manaClass: "ms-c" },
};

// Card utility functions moved to ../utils/cardUtils.ts

// Get color for deck health grade
function getGradeColor(grade: "S" | "A" | "B" | "C" | "D" | "F"): string {
  switch (grade) {
    case "S":
      return "#7ec850"; // Bright green
    case "A":
      return "#4a9fd8"; // Blue
    case "B":
      return "#e6c84a"; // Yellow
    case "C":
      return "#e89b5a"; // Orange
    case "D":
      return "#e86a58"; // Red-orange
    case "F":
      return "#ff5555"; // Red
    default:
      return colors.text.muted;
  }
}

// Mana Curve Mini Chart
function ManaCurveChart({ data }: { data: ManaCurveData }): ReactNode {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.curve) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 200;
    const height = 90;
    const margin = { top: 15, right: 5, bottom: 20, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const chartData = Array.from({ length: 8 }, (_, i) => ({
      cmc: i,
      count: data.curve[String(i)] || 0,
      label: i === 7 ? "7+" : String(i),
    }));

    const maxCount = Math.max(...chartData.map((d) => d.count), 1);

    const xScale = d3
      .scaleBand()
      .domain(chartData.map((d) => d.label))
      .range([0, innerWidth])
      .padding(0.2);

    const yScale = d3
      .scaleLinear()
      .domain([0, maxCount])
      .range([innerHeight, 0]);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Bars
    g.selectAll(".bar")
      .data(chartData)
      .enter()
      .append("rect")
      .attr("x", (d) => xScale(d.label) || 0)
      .attr("y", (d) => yScale(d.count))
      .attr("width", xScale.bandwidth())
      .attr("height", (d) => innerHeight - yScale(d.count))
      .attr("fill", colors.mana.blue.color)
      .attr("rx", 2)
      .style("opacity", 0.8);

    // Count labels above bars
    g.selectAll(".count-label")
      .data(chartData)
      .enter()
      .append("text")
      .attr("x", (d) => (xScale(d.label) || 0) + xScale.bandwidth() / 2)
      .attr("y", (d) => yScale(d.count) - 3)
      .attr("text-anchor", "middle")
      .attr("fill", colors.gold.standard)
      .style("font-size", "10px")
      .style("font-weight", "500")
      .text((d) => (d.count > 0 ? d.count : ""));

    // X-axis labels
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).tickSize(0))
      .call((g) => g.select(".domain").attr("stroke", colors.border.subtle))
      .selectAll("text")
      .attr("fill", colors.text.muted)
      .style("font-size", "9px");
  }, [data]);

  return <svg ref={svgRef} width={200} height={90} />;
}

// Color Distribution Mini Chart
function ColorChart({ data }: { data: ColorData }): ReactNode {
  const MANA_COLORS: Record<string, string> = {
    W: colors.mana.white.color,
    U: colors.mana.blue.color,
    B: colors.mana.black.color,
    R: colors.mana.red.color,
    G: colors.mana.green.color,
    C: "#bab1ab",
  };

  if (!data.breakdown?.length) {
    return (
      <div className="text-xs" style={{ color: colors.text.muted }}>
        No colors
      </div>
    );
  }

  const total = data.breakdown.reduce((sum, b) => sum + b.mana_symbols, 0) || 1;

  return (
    <div className="flex items-center gap-1">
      {data.breakdown
        .filter((b) => b.mana_symbols > 0)
        .sort((a, b) => b.mana_symbols - a.mana_symbols)
        .map((b) => (
          <div
            key={b.color}
            className="flex items-center gap-1"
            title={`${b.color_name}: ${b.mana_symbols} pips`}
          >
            <div
              className="w-4 h-4 rounded-full flex items-center justify-center text-xs font-bold"
              style={{
                background: MANA_COLORS[b.color] || colors.text.muted,
                color: b.color === "W" ? colors.void.deep : colors.text.bright,
              }}
            >
              {b.color}
            </div>
            <span className="text-xs" style={{ color: colors.text.dim }}>
              {Math.round((b.mana_symbols / total) * 100)}%
            </span>
          </div>
        ))}
    </div>
  );
}

// Card Search Panel - Types for deck impact
type DeckImpact = components["schemas"]["DeckImpact"];

const emptyFilters: SearchFilterState = {
  colors: [],
  setCodes: [],
  format: null,
  rarity: null,
  type: null,
};

const PAGE_SIZE = 30;

function CardSearchPanel({
  onAddCard,
  deckFormat,
  deckId,
  onCardHover,
  onCardClick,
}: {
  onAddCard: (card: CardSearchResult) => void;
  deckFormat: string | null;
  deckId: number;
  onCardHover?: (card: CardSearchResult | null) => void;
  onCardClick?: (card: CardSearchResult) => void;
}): ReactNode {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardSearchResult[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [filters, setFilters] = useState<SearchFilterState>(emptyFilters);
  const [collectionOnly, setCollectionOnly] = useState(false);
  const [cardImpacts, setCardImpacts] = useState<Record<string, DeckImpact>>(
    {},
  );
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const impactTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(
    async (searchQuery: string, page: number = 1, append: boolean = false) => {
      const hasFilters =
        filters.colors.length > 0 ||
        filters.type !== null ||
        filters.rarity !== null ||
        filters.setCodes.length > 0;
      if (!searchQuery.trim() && !hasFilters) {
        setResults([]);
        setTotalCount(0);
        setCurrentPage(1);
        return;
      }

      if (append) {
        setIsLoadingMore(true);
      } else {
        setIsSearching(true);
      }

      try {
        // Use deck format OR filter format (deck format takes precedence)
        const effectiveFormat = deckFormat || filters.format;

        const result = await window.electronAPI.api.cards.search({
          name: searchQuery || undefined,
          colors:
            filters.colors.length > 0
              ? (filters.colors as ("W" | "U" | "B" | "R" | "G" | "C")[])
              : undefined,
          type: filters.type || undefined,
          rarity:
            (filters.rarity as "common" | "uncommon" | "rare" | "mythic") ||
            undefined,
          set_code:
            filters.setCodes.length > 0 ? filters.setCodes[0] : undefined,
          format_legal: (effectiveFormat as Format) || undefined,
          in_collection: collectionOnly || undefined,
          page: page,
          page_size: PAGE_SIZE,
        });

        const newCards = result.cards.map((c) => ({
          name: c.name,
          mana_cost: c.mana_cost,
          type: c.type,
          cmc: c.cmc,
          rarity: c.rarity,
          image_small: c.image_small,
          set_code: c.set_code,
        }));

        if (append) {
          setResults((prev) => [...prev, ...newCards]);
        } else {
          setResults(newCards);
        }
        setTotalCount(result.total_count ?? 0);
        setCurrentPage(page);
      } catch (err) {
        console.error("Search failed:", err);
      } finally {
        setIsSearching(false);
        setIsLoadingMore(false);
      }
    },
    [filters, deckFormat, collectionOnly],
  );

  const handleQueryChange = (value: string): void => {
    setQuery(value);
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }
    searchTimeout.current = setTimeout(() => doSearch(value, 1, false), 300);
  };

  const handleLoadMore = (): void => {
    if (!isLoadingMore && results.length < totalCount) {
      doSearch(query, currentPage + 1, true);
    }
  };

  // Re-search when filters change
  useEffect(() => {
    const hasFilters =
      filters.colors.length > 0 ||
      filters.type !== null ||
      filters.rarity !== null ||
      filters.setCodes.length > 0;
    if (query || hasFilters) {
      doSearch(query, 1, false);
    }
  }, [filters, collectionOnly, doSearch, query]);

  // Fetch deck impact for ALL visible search results (debounced)
  useEffect(() => {
    if (results.length === 0 || !deckId) {
      setCardImpacts({});
      return;
    }

    // Clear previous timeout
    if (impactTimeout.current) {
      clearTimeout(impactTimeout.current);
    }

    // Debounce impact fetching
    impactTimeout.current = setTimeout(async () => {
      const impacts: Record<string, DeckImpact> = {};

      // Fetch impacts for all visible cards in parallel
      await Promise.all(
        results.map(async (card) => {
          try {
            const impact = await window.electronAPI.decks.analyzeDeckImpact(
              card.name,
              deckId,
              1,
            );
            impacts[card.name] = impact;
          } catch {
            // Ignore errors for individual cards
          }
        }),
      );

      setCardImpacts(impacts);
    }, 300);

    return () => {
      if (impactTimeout.current) {
        clearTimeout(impactTimeout.current);
      }
    };
  }, [results, deckId]);

  const hasMore = results.length < totalCount;

  return (
    <div className="flex flex-col h-full">
      {/* Search input */}
      <div
        className="p-3 border-b"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="Search cards to add..."
            className="flex-1 h-9 px-3 text-sm rounded"
            style={{
              background: colors.void.medium,
              border: `1px solid ${colors.border.standard}`,
              color: colors.text.standard,
              outline: "none",
            }}
            autoFocus
          />

          {/* Collection only toggle */}
          <button
            onClick={() => setCollectionOnly(!collectionOnly)}
            className="h-9 px-3 text-xs rounded flex items-center gap-1.5 transition-all whitespace-nowrap"
            style={{
              background: collectionOnly ? colors.gold.dim : colors.void.medium,
              border: `1px solid ${collectionOnly ? colors.gold.standard : colors.border.standard}`,
              color: collectionOnly ? colors.gold.bright : colors.text.muted,
            }}
            title="Only show cards in your collection"
          >
            <i className="ms ms-infinity" style={{ fontSize: 12 }} />
            <span>Collection</span>
          </button>

          {/* Format indicator */}
          {deckFormat && (
            <span
              className="h-9 px-3 text-xs rounded flex items-center"
              style={{
                background: colors.void.lighter,
                color: colors.gold.standard,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              {deckFormat}
            </span>
          )}
        </div>

        {/* Full filter bar using reusable SearchFilters component */}
        <SearchFilters filters={filters} onChange={setFilters} />
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto relative">
        {isSearching && (
          <div className="p-4 text-center">
            <span style={{ color: colors.text.muted }}>Searching...</span>
          </div>
        )}

        {!isSearching &&
          results.length === 0 &&
          (query ||
            filters.colors.length > 0 ||
            filters.setCodes.length > 0 ||
            filters.type ||
            filters.rarity) && (
            <div className="p-4 text-center">
              <span style={{ color: colors.text.muted }}>No cards found</span>
            </div>
          )}

        {!isSearching &&
          results.length === 0 &&
          !query &&
          filters.colors.length === 0 &&
          filters.setCodes.length === 0 &&
          !filters.type &&
          !filters.rarity && (
            <div className="p-4 text-center">
              <span style={{ color: colors.text.muted }}>
                Type to search for cards
              </span>
            </div>
          )}

        {results.map((card) => {
          const rarityColor = getRarityColor(card.rarity || "common");
          const isHovered = hoveredCard === card.name;

          return (
            <div
              key={card.name}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("text/plain", card.name);
                e.dataTransfer.setData("application/x-source", "search");
                e.dataTransfer.effectAllowed = "copy";
              }}
              className="flex items-center gap-3 px-3 py-2 cursor-grab transition-colors relative"
              style={{ borderBottom: `1px solid ${colors.border.subtle}` }}
              onClick={() => onCardClick?.(card)}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = colors.void.light;
                const rect = e.currentTarget.getBoundingClientRect();
                setTooltipPosition({ x: rect.right + 8, y: rect.top });
                setHoveredCard(card.name);
                onCardHover?.(card);
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                setHoveredCard(null);
                setTooltipPosition(null);
                onCardHover?.(null);
              }}
            >
              {/* Card image thumbnail */}
              {card.image_small && (
                <img
                  src={card.image_small}
                  alt=""
                  className="w-8 h-11 rounded object-cover"
                  loading="lazy"
                  style={{ border: `1px solid ${colors.border.subtle}` }}
                />
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="text-sm font-display truncate"
                    style={{ color: rarityColor }}
                  >
                    {card.name}
                  </span>
                  {card.mana_cost && (
                    <ManaCost cost={card.mana_cost} size="small" />
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs truncate"
                    style={{ color: colors.text.muted }}
                  >
                    {card.type}
                  </span>
                  {/* Impact badges */}
                  <DeckImpactBadges impact={cardImpacts[card.name] || null} />
                </div>
              </div>

              <button
                className="px-2 py-1 text-xs rounded"
                style={{
                  background: colors.gold.standard,
                  color: colors.void.deepest,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onAddCard(card);
                }}
              >
                + Add
              </button>

              {/* Hover tooltip for deck impact - rendered via portal */}
              {isHovered &&
                tooltipPosition &&
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
                    <DeckImpactTooltip
                      impact={cardImpacts[card.name] || null}
                      isLoading={!cardImpacts[card.name]}
                    />
                  </div>,
                  document.body,
                )}
            </div>
          );
        })}

        {/* Load More button */}
        {hasMore && !isSearching && (
          <div className="p-3 text-center">
            <button
              onClick={handleLoadMore}
              disabled={isLoadingMore}
              className="px-4 py-2 text-sm rounded transition-all"
              style={{
                background: colors.void.lighter,
                border: `1px solid ${colors.border.standard}`,
                color: isLoadingMore ? colors.text.muted : colors.gold.standard,
                cursor: isLoadingMore ? "wait" : "pointer",
              }}
              onMouseEnter={(e) => {
                if (!isLoadingMore) {
                  e.currentTarget.style.borderColor = colors.gold.dim;
                  e.currentTarget.style.background = colors.void.light;
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = colors.border.standard;
                e.currentTarget.style.background = colors.void.lighter;
              }}
            >
              {isLoadingMore
                ? "Loading..."
                : `Load More (${(totalCount - results.length).toLocaleString()} remaining)`}
            </button>
          </div>
        )}

        {/* Results count */}
        {results.length > 0 && (
          <div
            className="p-2 text-center text-xs"
            style={{ color: colors.text.muted }}
          >
            Showing {results.length} of {totalCount.toLocaleString()} cards
          </div>
        )}
      </div>
    </div>
  );
}

// Deck List Panel with rich card info - mainboard/sideboard/maybeboard tabs with drag-drop
function DeckListPanel({
  cards,
  onRemoveCard,
  onUpdateQuantity,
  onMoveCard,
  onCardHover,
  onCardClick,
  activeBoard,
  onSetActiveBoard,
  onDrop,
}: {
  cards: DeckCard[];
  onRemoveCard: (cardName: string, board: BoardType) => void;
  onUpdateQuantity: (
    cardName: string,
    quantity: number,
    board: BoardType,
  ) => void;
  onMoveCard?: (
    cardName: string,
    fromBoard: BoardType,
    toBoard: BoardType,
  ) => void;
  onCardHover?: (card: DeckCard | null) => void;
  onCardClick?: (card: DeckCard) => void;
  activeBoard: BoardType;
  onSetActiveBoard: (board: BoardType) => void;
  onDrop?: (cardName: string, toBoard: BoardType) => void;
}): ReactNode {
  const [dragOverBoard, setDragOverBoard] = useState<BoardType | null>(null);

  // Separate cards by board
  const mainboardCards = cards.filter(
    (c) => !c.is_sideboard && !c.is_maybeboard,
  );
  const sideboardCards = cards.filter((c) => c.is_sideboard);
  const maybeboardCards = cards.filter((c) => c.is_maybeboard);

  // Calculate totals
  const maindeckCount = mainboardCards.reduce((sum, c) => sum + c.quantity, 0);
  const sideboardCount = sideboardCards.reduce((sum, c) => sum + c.quantity, 0);
  const maybeboardCount = maybeboardCards.reduce(
    (sum, c) => sum + c.quantity,
    0,
  );

  // Get cards for active board
  const getActiveCards = (): DeckCard[] => {
    switch (activeBoard) {
      case "mainboard":
        return mainboardCards;
      case "sideboard":
        return sideboardCards;
      case "maybeboard":
        return maybeboardCards;
    }
  };

  // Group cards by type
  const groupByType = (cardList: DeckCard[]): Record<string, DeckCard[]> => {
    return cardList.reduce<Record<string, DeckCard[]>>((acc, card) => {
      const category = getCardCategory(card.type_line, card.is_commander);
      if (!acc[category]) acc[category] = [];
      acc[category].push(card);
      return acc;
    }, {});
  };

  const activeCards = getActiveCards();
  const groupedCards = groupByType(activeCards);

  // Tab config
  const tabs: Array<{
    board: BoardType;
    label: string;
    icon: string;
    color: string;
    count: number;
  }> = [
    {
      board: "mainboard",
      label: "Main",
      icon: "ms-creature",
      color: colors.gold.standard,
      count: maindeckCount,
    },
    {
      board: "sideboard",
      label: "Side",
      icon: "ms-sideboard",
      color: colors.mana.blue.color,
      count: sideboardCount,
    },
    {
      board: "maybeboard",
      label: "Maybe",
      icon: "ms-saga",
      color: colors.mana.green.color,
      count: maybeboardCount,
    },
  ];

  // Drag handlers for tabs (drop zones)
  const handleDragOver = (e: React.DragEvent, board: BoardType): void => {
    e.preventDefault();
    setDragOverBoard(board);
  };

  const handleDragLeave = (): void => {
    setDragOverBoard(null);
  };

  const handleDropOnTab = (e: React.DragEvent, board: BoardType): void => {
    e.preventDefault();
    setDragOverBoard(null);
    const cardName = e.dataTransfer.getData("text/plain");
    const fromBoard = e.dataTransfer.getData("application/x-board") as
      | BoardType
      | "";

    if (!cardName) return;

    // If dragging from another board, move the card
    if (fromBoard && onMoveCard && fromBoard !== board) {
      onMoveCard(cardName, fromBoard as BoardType, board);
    } else if (!fromBoard && onDrop) {
      // If dragging from search (no fromBoard), add to deck
      onDrop(cardName, board);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tab Header - 3 tabs */}
      <div
        className="border-b flex"
        style={{ borderColor: colors.border.subtle }}
      >
        {tabs.map((tab) => {
          const isActive = activeBoard === tab.board;
          const isDragOver = dragOverBoard === tab.board;
          return (
            <button
              key={tab.board}
              onClick={() => onSetActiveBoard(tab.board)}
              onDragOver={(e) => handleDragOver(e, tab.board)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDropOnTab(e, tab.board)}
              className="flex-1 py-2 px-2 text-sm font-display tracking-wide transition-all flex items-center justify-center gap-1.5"
              style={{
                background: isActive
                  ? colors.void.medium
                  : isDragOver
                    ? `${tab.color}20`
                    : "transparent",
                color: isActive ? colors.text.bright : colors.text.muted,
                borderBottom: isActive
                  ? `2px solid ${tab.color}`
                  : isDragOver
                    ? `2px solid ${tab.color}`
                    : "2px solid transparent",
              }}
            >
              <i className={`ms ${tab.icon}`} style={{ fontSize: 11 }} />
              <span>{tab.label}</span>
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  background: isActive ? `${tab.color}30` : colors.void.lighter,
                  color: isActive ? tab.color : colors.text.dim,
                }}
              >
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Card list - entire area is a drop zone for the active board */}
      <div
        className="flex-1 overflow-auto"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOverBoard(activeBoard);
        }}
        onDragLeave={(e) => {
          // Only clear if leaving the container entirely
          if (!e.currentTarget.contains(e.relatedTarget as Node)) {
            setDragOverBoard(null);
          }
        }}
        onDrop={(e) => handleDropOnTab(e, activeBoard)}
        style={{
          background:
            dragOverBoard === activeBoard
              ? `${tabs.find((t) => t.board === activeBoard)?.color}10`
              : undefined,
          transition: "background 0.15s ease",
        }}
      >
        {activeCards.length === 0 ? (
          <div className="p-4 text-center">
            <span style={{ color: colors.text.muted }}>
              {activeBoard === "mainboard" &&
                "No mainboard cards yet. Search and add cards from the left panel."}
              {activeBoard === "sideboard" &&
                "No sideboard cards yet. Drag cards here or click the Side tab when adding."}
              {activeBoard === "maybeboard" &&
                "No maybeboard cards yet. Drag cards here to consider them for your deck."}
            </span>
          </div>
        ) : (
          TYPE_ORDER.filter((type) => groupedCards[type]?.length).map(
            (type) => {
              const typeConfig = TYPE_CONFIG[type] || TYPE_CONFIG.Other;
              return (
                <div key={type} className="mb-1">
                  <div
                    className="px-3 py-1.5 text-xs uppercase tracking-wider sticky top-0 flex items-center gap-2"
                    style={{
                      background: colors.void.medium,
                      color: typeConfig.color,
                      borderBottom: `1px solid ${colors.border.subtle}`,
                      zIndex: 10,
                    }}
                  >
                    <i
                      className={`ms ${typeConfig.manaClass}`}
                      style={{ fontSize: "12px" }}
                    />
                    {type} (
                    {groupedCards[type].reduce((sum, c) => sum + c.quantity, 0)}
                    )
                  </div>
                  {groupedCards[type]
                    .sort((a, b) => (a.cmc || 0) - (b.cmc || 0))
                    .map((card) => (
                      <DraggableCardRow
                        key={`${activeBoard}-${card.card_name}`}
                        card={card}
                        board={activeBoard}
                        onRemoveCard={onRemoveCard}
                        onUpdateQuantity={onUpdateQuantity}
                        onMoveCard={onMoveCard}
                        onCardHover={onCardHover}
                        onCardClick={onCardClick}
                      />
                    ))}
                </div>
              );
            },
          )
        )}
      </div>
    </div>
  );
}

// Draggable card row component
function DraggableCardRow({
  card,
  board,
  onRemoveCard,
  onUpdateQuantity,
  onMoveCard,
  onCardHover,
  onCardClick,
}: {
  card: DeckCard;
  board: BoardType;
  onRemoveCard: (cardName: string, board: BoardType) => void;
  onUpdateQuantity: (
    cardName: string,
    quantity: number,
    board: BoardType,
  ) => void;
  onMoveCard?: (
    cardName: string,
    fromBoard: BoardType,
    toBoard: BoardType,
  ) => void;
  onCardHover?: (card: DeckCard | null) => void;
  onCardClick?: (card: DeckCard) => void;
}): ReactNode {
  const rarityColor = getRarityColor(card.rarity || "common");
  const subtype = getSubtype(card.type_line);
  const displayName = card.flavor_name || card.card_name;
  const showActualName =
    card.flavor_name && card.flavor_name !== card.card_name;

  const handleDragStart = (e: React.DragEvent): void => {
    e.dataTransfer.setData("text/plain", card.card_name);
    e.dataTransfer.setData("application/x-board", board);
    e.dataTransfer.effectAllowed = "move";
  };

  // Get other boards for move menu
  const otherBoards = (
    ["mainboard", "sideboard", "maybeboard"] as BoardType[]
  ).filter((b) => b !== board);

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className="flex items-start gap-2 px-3 py-2 group cursor-grab active:cursor-grabbing transition-colors"
      style={{ borderBottom: `1px solid ${colors.border.subtle}` }}
      onMouseEnter={() => onCardHover?.(card)}
      onMouseLeave={() => onCardHover?.(null)}
      onClick={() => onCardClick?.(card)}
    >
      {/* Quantity controls */}
      <div className="flex items-center gap-1 pt-0.5">
        <button
          className="w-5 h-5 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ background: colors.void.lighter, color: colors.text.dim }}
          onClick={(e) => {
            e.stopPropagation();
            onUpdateQuantity(
              card.card_name,
              Math.max(0, card.quantity - 1),
              board,
            );
          }}
        >
          -
        </button>
        <span
          className="w-5 text-center text-sm font-mono"
          style={{ color: colors.gold.standard }}
        >
          {card.quantity}
        </span>
        <button
          className="w-5 h-5 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ background: colors.void.lighter, color: colors.text.dim }}
          onClick={(e) => {
            e.stopPropagation();
            onUpdateQuantity(card.card_name, card.quantity + 1, board);
          }}
        >
          +
        </button>
      </div>

      {/* Card info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-display truncate"
            style={{
              color: card.is_commander ? colors.gold.standard : rarityColor,
            }}
          >
            {displayName}
          </span>
          {card.mana_cost && <ManaCost cost={card.mana_cost} size="small" />}
        </div>
        <div
          className="flex items-center gap-2 text-xs mt-0.5"
          style={{ color: colors.text.muted }}
        >
          {showActualName && (
            <span style={{ color: colors.text.dim }}>{card.card_name}</span>
          )}
          {subtype && <span className="truncate">{subtype}</span>}
          {card.set_code && (
            <span className="flex items-center gap-1 shrink-0">
              <i
                className={`ss ss-${card.set_code.toLowerCase()}`}
                style={{ fontSize: "10px" }}
              />
              {card.collector_number && <span>#{card.collector_number}</span>}
            </span>
          )}
        </div>
      </div>

      {/* Move buttons */}
      {onMoveCard && (
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity pt-0.5">
          {otherBoards.map((toBoard) => (
            <button
              key={toBoard}
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                background: colors.void.lighter,
                color:
                  toBoard === "mainboard"
                    ? colors.gold.standard
                    : toBoard === "sideboard"
                      ? colors.mana.blue.color
                      : colors.mana.green.color,
              }}
              onClick={(e) => {
                e.stopPropagation();
                onMoveCard(card.card_name, board, toBoard);
              }}
              title={`Move to ${toBoard}`}
            >
              →{" "}
              {toBoard === "mainboard"
                ? "M"
                : toBoard === "sideboard"
                  ? "S"
                  : "?"}
            </button>
          ))}
        </div>
      )}

      {/* Remove button */}
      <button
        className="text-xs opacity-0 group-hover:opacity-100 transition-opacity pt-0.5"
        style={{ color: colors.status.error }}
        onClick={(e) => {
          e.stopPropagation();
          onRemoveCard(card.card_name, board);
        }}
      >
        ✕
      </button>
    </div>
  );
}

export function DeckBuilderScreen({
  deckId,
  onBack,
}: DeckBuilderScreenProps): ReactNode {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [manaCurve, setManaCurve] = useState<ManaCurveData | null>(null);
  const [colorData, setColorData] = useState<ColorData | null>(null);
  const [healthData, setHealthData] = useState<DeckHealthData | null>(null);
  const [priceData, setPriceData] = useState<PriceData | null>(null);
  const [showCombos, setShowCombos] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  // Card preview state
  const [hoveredCard, setHoveredCard] = useState<DeckCard | null>(null);
  const [hoveredSearchCard, setHoveredSearchCard] =
    useState<CardSearchResult | null>(null);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);

  // Load deck
  const loadDeck = useCallback(async () => {
    try {
      const result = await window.electronAPI.decks.get(deckId);
      setDeck(result);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  }, [deckId]);

  // Analyze deck by ID (fetches cards from database directly)
  const analyzeDeck = useCallback(async () => {
    if (!deck || deck.cards.length === 0) {
      setManaCurve(null);
      setColorData(null);
      setHealthData(null);
      setPriceData(null);
      return;
    }

    try {
      const [curve, colorsResult, health, price] = await Promise.all([
        window.electronAPI.decks.analyzeDeckManaCurveById(deck.id),
        window.electronAPI.decks.analyzeDeckColorsById(deck.id),
        window.electronAPI.decks.analyzeDeckHealthById(deck.id),
        window.electronAPI.decks.analyzeDeckPriceById(deck.id),
      ]);
      setManaCurve(curve);
      setColorData(colorsResult);
      setHealthData(health);
      setPriceData(price);
    } catch (err) {
      console.error("Analysis failed:", err);
    }
  }, [deck]);

  useEffect(() => {
    loadDeck();
  }, [loadDeck]);

  useEffect(() => {
    if (deck) {
      analyzeDeck();
    }
  }, [deck, analyzeDeck]);

  // Fetch card image when hovered (deck card or search result)
  useEffect(() => {
    // Determine which card is being previewed (deck card takes priority, then search card)
    const previewCard = hoveredCard || hoveredSearchCard;

    if (!previewCard) {
      setPreviewImageUrl(null);
      return;
    }

    // Get card name - deck cards use card_name, search results use name
    const cardName =
      "card_name" in previewCard ? previewCard.card_name : previewCard.name;
    const smallImage = previewCard.image_small;

    // If we already have a small image, use it initially
    if (smallImage) {
      // Convert small to normal size image
      const normalUrl = smallImage.replace("/small/", "/normal/");
      setPreviewImageUrl(normalUrl);
    }

    // Fetch full card details for best image
    const fetchImage = async (): Promise<void> => {
      try {
        const details = await window.electronAPI.api.cards.getByName(cardName);
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
  }, [hoveredCard, hoveredSearchCard]);

  // Add card to deck - state for which board to add to
  const [activeBoard, setActiveBoard] = useState<BoardType>("mainboard");

  const handleAddCard = useCallback(
    async (card: CardSearchResult): Promise<void> => {
      if (!deck) return;

      try {
        await window.electronAPI.decks.addCard(deck.id, {
          card_name: card.name,
          quantity: 1,
          is_sideboard: activeBoard === "sideboard",
          is_maybeboard: activeBoard === "maybeboard",
          is_commander: false,
        });
        await loadDeck();
      } catch (err) {
        setError(String(err));
      }
    },
    [deck, loadDeck, activeBoard],
  );

  // Remove card from deck
  const handleRemoveCard = useCallback(
    async (cardName: string, board: BoardType): Promise<void> => {
      if (!deck) return;

      try {
        await window.electronAPI.decks.removeCard(
          deck.id,
          cardName,
          board === "sideboard",
          board === "maybeboard",
        );
        await loadDeck();
      } catch (err) {
        setError(String(err));
      }
    },
    [deck, loadDeck],
  );

  // Update card quantity
  const handleUpdateQuantity = useCallback(
    async (
      cardName: string,
      quantity: number,
      board: BoardType,
    ): Promise<void> => {
      if (!deck) return;

      try {
        if (quantity <= 0) {
          await window.electronAPI.decks.removeCard(
            deck.id,
            cardName,
            board === "sideboard",
            board === "maybeboard",
          );
        } else {
          await window.electronAPI.decks.updateCardQuantity(
            deck.id,
            cardName,
            quantity,
            board === "sideboard",
            board === "maybeboard",
          );
        }
        await loadDeck();
      } catch (err) {
        setError(String(err));
      }
    },
    [deck, loadDeck],
  );

  // Move card between boards
  const handleMoveCard = useCallback(
    async (
      cardName: string,
      fromBoard: BoardType,
      toBoard: BoardType,
    ): Promise<void> => {
      if (!deck) return;

      try {
        // Find the card to get its quantity
        const card = deck.cards.find((c) => {
          const cardBoard: BoardType = c.is_maybeboard
            ? "maybeboard"
            : c.is_sideboard
              ? "sideboard"
              : "mainboard";
          return c.card_name === cardName && cardBoard === fromBoard;
        });
        if (!card) return;

        // Move only 1 copy at a time
        if (card.quantity === 1) {
          // Remove entirely from source
          await window.electronAPI.decks.removeCard(
            deck.id,
            cardName,
            fromBoard === "sideboard",
            fromBoard === "maybeboard",
          );
        } else {
          // Decrement quantity in source
          await window.electronAPI.decks.updateCardQuantity(
            deck.id,
            cardName,
            card.quantity - 1,
            fromBoard === "sideboard",
            fromBoard === "maybeboard",
          );
        }

        // Add 1 to destination (will increment if already exists)
        await window.electronAPI.decks.addCard(deck.id, {
          card_name: cardName,
          quantity: 1,
          is_sideboard: toBoard === "sideboard",
          is_maybeboard: toBoard === "maybeboard",
          is_commander: false,
        });

        // Update local state without full reload to avoid count recalculation flicker
        setDeck((prev) => {
          if (!prev) return prev;

          const newCards = [...prev.cards];
          const sourceIdx = newCards.findIndex((c) => {
            const cardBoard: BoardType = c.is_maybeboard
              ? "maybeboard"
              : c.is_sideboard
                ? "sideboard"
                : "mainboard";
            return c.card_name === cardName && cardBoard === fromBoard;
          });

          if (sourceIdx === -1) return prev;

          // Update or remove source card
          if (newCards[sourceIdx].quantity === 1) {
            newCards.splice(sourceIdx, 1);
          } else {
            newCards[sourceIdx] = {
              ...newCards[sourceIdx],
              quantity: newCards[sourceIdx].quantity - 1,
            };
          }

          // Find or add destination card
          const destIdx = newCards.findIndex((c) => {
            const cardBoard: BoardType = c.is_maybeboard
              ? "maybeboard"
              : c.is_sideboard
                ? "sideboard"
                : "mainboard";
            return c.card_name === cardName && cardBoard === toBoard;
          });

          if (destIdx !== -1) {
            // Increment existing
            newCards[destIdx] = {
              ...newCards[destIdx],
              quantity: newCards[destIdx].quantity + 1,
            };
          } else {
            // Add new entry based on source card data
            const sourceCard = prev.cards.find((c) => {
              const cardBoard: BoardType = c.is_maybeboard
                ? "maybeboard"
                : c.is_sideboard
                  ? "sideboard"
                  : "mainboard";
              return c.card_name === cardName && cardBoard === fromBoard;
            });
            if (sourceCard) {
              newCards.push({
                ...sourceCard,
                quantity: 1,
                is_sideboard: toBoard === "sideboard",
                is_maybeboard: toBoard === "maybeboard",
              });
            }
          }

          return { ...prev, cards: newCards };
        });
      } catch (err) {
        setError(String(err));
      }
    },
    [deck],
  );

  // Handle drop from search panel onto a board tab
  const handleDropOnBoard = useCallback(
    async (cardName: string, toBoard: BoardType): Promise<void> => {
      if (!deck) return;

      try {
        await window.electronAPI.decks.addCard(deck.id, {
          card_name: cardName,
          quantity: 1,
          is_sideboard: toBoard === "sideboard",
          is_maybeboard: toBoard === "maybeboard",
          is_commander: false,
        });
        await loadDeck();
      } catch (err) {
        setError(String(err));
      }
    },
    [deck, loadDeck],
  );

  if (isLoading) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{
          background: `
            radial-gradient(ellipse 100% 60% at 50% 50%, ${colors.gold.glow}08 0%, transparent 50%),
            ${colors.void.deepest}
          `,
        }}
      >
        <div className="text-center">
          <div
            className="w-10 h-10 mx-auto mb-4 rounded-full border-2 border-t-transparent"
            style={{
              borderColor: colors.gold.dim,
              borderTopColor: "transparent",
              animation: "spin 1s linear infinite",
            }}
          />
          <p
            className="font-display tracking-wider text-sm"
            style={{ color: colors.text.muted }}
          >
            Loading deck...
          </p>
        </div>
        <style>{`
          @keyframes spin { to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (!deck) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ background: colors.void.deepest }}
      >
        <div className="text-center">
          <i
            className="ms ms-saga"
            style={{ fontSize: 48, color: colors.gold.dim, opacity: 0.3 }}
          />
          <p
            className="mt-4 font-display"
            style={{ color: colors.status.error }}
          >
            Deck not found
          </p>
          <button
            className="mt-4 px-4 py-2 rounded-lg transition-colors"
            style={{
              background: colors.void.lighter,
              color: colors.text.standard,
              border: `1px solid ${colors.border.subtle}`,
            }}
            onClick={onBack}
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const formatColor = getFormatColor(deck.format);

  return (
    <div
      className="h-full flex flex-col"
      style={{
        background: `
          radial-gradient(ellipse 100% 60% at 0% 0%, ${formatColor}08 0%, transparent 50%),
          radial-gradient(ellipse 80% 50% at 100% 100%, ${colors.gold.glow}06 0%, transparent 50%),
          ${colors.void.deepest}
        `,
      }}
    >
      {/* Header */}
      <div
        className="p-5 border-b flex items-center gap-4"
        style={{
          background: `linear-gradient(180deg, ${colors.void.deep} 0%, transparent 100%)`,
          borderColor: `${colors.border.subtle}80`,
        }}
      >
        <button
          className="px-3 py-1.5 text-sm rounded-lg transition-colors"
          style={{
            background: colors.void.lighter,
            color: colors.text.dim,
            border: `1px solid ${colors.border.subtle}`,
          }}
          onClick={onBack}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = colors.text.dim;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = colors.border.subtle;
          }}
        >
          ← Back
        </button>

        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1
              className="font-display text-2xl tracking-wide"
              style={{ color: colors.text.bright }}
            >
              {deck.name}
            </h1>
            {deck.format && (
              <span
                className="text-xs font-display tracking-wider px-2.5 py-1 rounded-md"
                style={{
                  background: `${formatColor}15`,
                  color: formatColor,
                  border: `1px solid ${formatColor}30`,
                }}
              >
                {deck.format.toUpperCase()}
              </span>
            )}
          </div>
          {deck.commander && (
            <div className="flex items-center gap-2 mt-1.5">
              <i
                className="ms ms-commander"
                style={{ fontSize: 12, color: colors.gold.standard }}
              />
              <span className="text-sm" style={{ color: colors.gold.standard }}>
                {deck.commander}
              </span>
            </div>
          )}
        </div>

        {/* Quick stats */}
        <div className="flex items-center gap-4">
          <div
            className="text-center px-4 py-2 rounded-lg"
            style={{
              background: colors.void.medium,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            <div
              className="text-2xl font-display"
              style={{ color: colors.text.bright }}
            >
              {deck.cards
                .filter((c) => !c.is_sideboard)
                .reduce((sum, c) => sum + c.quantity, 0)}
            </div>
            <div className="text-xs" style={{ color: colors.text.muted }}>
              cards
            </div>
          </div>
          {manaCurve && (
            <div
              className="text-center px-4 py-2 rounded-lg"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div
                className="text-2xl font-display"
                style={{ color: colors.mana.blue.color }}
              >
                {manaCurve.average_cmc.toFixed(1)}
              </div>
              <div className="text-xs" style={{ color: colors.text.muted }}>
                avg CMC
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div
          className="mx-4 mt-4 p-3 rounded text-sm"
          style={{
            background: "rgba(255,85,85,0.1)",
            border: "1px solid rgba(255,85,85,0.3)",
            color: "#ff5555",
          }}
        >
          {error}
        </div>
      )}

      {/* Main content - split view */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Card browser */}
        <div
          className="w-1/2 border-r flex flex-col"
          style={{
            background: colors.void.deep,
            borderColor: colors.border.subtle,
          }}
        >
          <CardSearchPanel
            onAddCard={handleAddCard}
            deckFormat={deck.format}
            deckId={deck.id}
            onCardHover={setHoveredSearchCard}
            onCardClick={(card) => setSelectedCardName(card.name)}
          />
        </div>

        {/* Middle: Deck list */}
        <div
          className="flex-1 flex flex-col"
          style={{ background: colors.void.deep }}
        >
          <DeckListPanel
            cards={deck.cards}
            onRemoveCard={handleRemoveCard}
            onUpdateQuantity={handleUpdateQuantity}
            onMoveCard={handleMoveCard}
            onCardHover={setHoveredCard}
            onCardClick={(card) => setSelectedCardName(card.card_name)}
            activeBoard={activeBoard}
            onSetActiveBoard={setActiveBoard}
            onDrop={handleDropOnBoard}
          />
        </div>

        {/* Right: Card Preview Panel */}
        <div
          className="w-64 border-l flex flex-col"
          style={{
            background: colors.void.medium,
            borderColor: colors.border.subtle,
          }}
        >
          <div
            className="p-3 border-b"
            style={{ borderColor: colors.border.subtle }}
          >
            <span
              className="font-display text-sm"
              style={{ color: colors.text.bright }}
            >
              Card Preview
            </span>
            <span className="text-xs ml-2" style={{ color: colors.text.muted }}>
              (hover to preview, click for details)
            </span>
          </div>

          <div className="flex-1 flex items-center justify-center p-4">
            {(hoveredCard || hoveredSearchCard) && previewImageUrl ? (
              <div className="text-center">
                <img
                  src={previewImageUrl}
                  alt={hoveredCard?.card_name || hoveredSearchCard?.name || ""}
                  className="rounded-lg shadow-lg max-w-full"
                  loading="lazy"
                  style={{
                    maxHeight: "400px",
                    boxShadow: `0 4px 20px rgba(0,0,0,0.5)`,
                  }}
                />
                <div
                  className="mt-3 font-display text-sm"
                  style={{ color: colors.gold.standard }}
                >
                  {hoveredCard?.card_name || hoveredSearchCard?.name}
                </div>
                {(hoveredCard?.type_line || hoveredSearchCard?.type) && (
                  <div
                    className="text-xs mt-1"
                    style={{ color: colors.text.muted }}
                  >
                    {hoveredCard?.type_line || hoveredSearchCard?.type}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center" style={{ color: colors.text.dim }}>
                <i
                  className="ms ms-planeswalker"
                  style={{ fontSize: "48px", opacity: 0.3 }}
                />
                <p className="mt-3 text-sm">Hover over a card to preview it</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom: Analytics Bar */}
      <div
        className="border-t flex flex-wrap items-stretch"
        style={{
          background: colors.void.medium,
          borderColor: colors.border.subtle,
          minHeight: "100px",
        }}
      >
        {/* Deck Score */}
        <div
          className="flex flex-col justify-center items-center px-4 border-r border-b"
          style={{ borderColor: colors.border.subtle, minWidth: "80px" }}
        >
          {healthData ? (
            <>
              <div
                className="text-3xl font-display font-bold"
                style={{
                  color: getGradeColor(healthData.grade),
                }}
              >
                {healthData.grade}
              </div>
              <div className="text-xs" style={{ color: colors.text.muted }}>
                {healthData.score}/100
              </div>
              <div
                className="w-full h-1 rounded mt-1"
                style={{ background: colors.void.lighter }}
              >
                <div
                  className="h-full rounded"
                  style={{
                    width: `${healthData.score}%`,
                    background: getGradeColor(healthData.grade),
                  }}
                />
              </div>
            </>
          ) : (
            <div className="text-xs" style={{ color: colors.text.dim }}>
              -
            </div>
          )}
        </div>

        {/* Archetype */}
        <div
          className="flex flex-col justify-center px-4 border-r border-b"
          style={{ borderColor: colors.border.subtle, minWidth: "120px" }}
        >
          <div className="text-sm mb-1" style={{ color: colors.text.muted }}>
            Archetype
          </div>
          {healthData ? (
            <>
              <div
                className="text-base font-display font-medium"
                style={{ color: colors.gold.standard }}
              >
                {healthData.archetype}
              </div>
              <div className="text-sm" style={{ color: colors.text.dim }}>
                {healthData.archetype_confidence}% confidence
              </div>
            </>
          ) : (
            <div className="text-sm" style={{ color: colors.text.dim }}>
              -
            </div>
          )}
        </div>

        {/* Mana Curve */}
        <div
          className="flex flex-col justify-center px-3 border-r border-b"
          style={{ borderColor: colors.border.subtle }}
        >
          <div className="text-sm mb-1" style={{ color: colors.text.muted }}>
            Curve
          </div>
          {manaCurve ? (
            <ManaCurveChart data={manaCurve} />
          ) : (
            <div className="text-sm" style={{ color: colors.text.dim }}>
              Add cards
            </div>
          )}
        </div>

        {/* Color Distribution */}
        <div
          className="flex flex-col justify-center px-4 border-r border-b"
          style={{ borderColor: colors.border.subtle }}
        >
          <div className="text-sm mb-1" style={{ color: colors.text.muted }}>
            Colors
          </div>
          {colorData ? (
            <ColorChart data={colorData} />
          ) : (
            <div className="text-sm" style={{ color: colors.text.dim }}>
              -
            </div>
          )}
        </div>

        {/* Key Metrics */}
        <div
          className="flex flex-col justify-center px-4 border-r border-b flex-1"
          style={{ borderColor: colors.border.subtle, minWidth: "280px" }}
        >
          <div className="text-sm mb-2" style={{ color: colors.text.muted }}>
            Key Metrics
          </div>
          {healthData ? (
            <div className="grid grid-cols-3 gap-x-6 gap-y-2 text-sm">
              <div className="flex items-center gap-2">
                <i
                  className="ms ms-creature"
                  style={{ color: colors.mana.green.color, fontSize: 14 }}
                />
                <span style={{ color: colors.text.dim }}>Creatures:</span>
                <span style={{ color: colors.text.bright, fontWeight: 500 }}>
                  {healthData.creature_count}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <i
                  className="ms ms-land"
                  style={{ color: "#8b7355", fontSize: 14 }}
                />
                <span style={{ color: colors.text.dim }}>Lands:</span>
                <span
                  style={{
                    fontWeight: 500,
                    color:
                      healthData.land_percentage >= 33 &&
                      healthData.land_percentage <= 42
                        ? colors.status.success
                        : colors.status.warning,
                  }}
                >
                  {healthData.land_count} ({healthData.land_percentage}%)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span style={{ color: colors.text.dim }}>Interaction:</span>
                <span
                  style={{
                    fontWeight: 500,
                    color:
                      healthData.interaction_count >= 6
                        ? colors.status.success
                        : colors.status.warning,
                  }}
                >
                  {healthData.interaction_count}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <i
                  className="ms ms-instant"
                  style={{ color: colors.mana.blue.color, fontSize: 14 }}
                />
                <span style={{ color: colors.text.dim }}>Spells:</span>
                <span style={{ color: colors.text.bright, fontWeight: 500 }}>
                  {healthData.instant_count + healthData.sorcery_count}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span style={{ color: colors.text.dim }}>Draw:</span>
                <span
                  style={{
                    fontWeight: 500,
                    color:
                      healthData.card_draw_count >= 5
                        ? colors.status.success
                        : colors.status.warning,
                  }}
                >
                  {healthData.card_draw_count}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span style={{ color: colors.text.dim }}>Ramp:</span>
                <span style={{ color: colors.text.bright, fontWeight: 500 }}>
                  {healthData.ramp_count}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-sm" style={{ color: colors.text.dim }}>
              -
            </div>
          )}
        </div>

        {/* Deck Cost */}
        <div
          className="flex flex-col justify-center px-4 border-r border-b"
          style={{ borderColor: colors.border.subtle, minWidth: "90px" }}
        >
          <div className="text-sm mb-1" style={{ color: colors.text.muted }}>
            Deck Cost
          </div>
          {priceData && priceData.total_price !== null ? (
            <>
              <div
                className="text-xl font-display font-medium"
                style={{ color: colors.gold.standard }}
              >
                ${priceData.total_price.toFixed(2)}
              </div>
              <div className="text-xs" style={{ color: colors.text.dim }}>
                {priceData.missing_prices.length > 0 && (
                  <span
                    title={`Missing prices for: ${priceData.missing_prices.slice(0, 5).join(", ")}${priceData.missing_prices.length > 5 ? "..." : ""}`}
                  >
                    {priceData.missing_prices.length} missing
                  </span>
                )}
                {priceData.missing_prices.length === 0 &&
                  priceData.average_card_price !== null && (
                    <span>
                      ~${priceData.average_card_price.toFixed(2)}/card
                    </span>
                  )}
              </div>
            </>
          ) : (
            <div className="text-sm" style={{ color: colors.text.dim }}>
              -
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div
          className="flex flex-col justify-center gap-2 px-4 border-b"
          style={{ borderColor: colors.border.subtle }}
        >
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="px-3 py-1.5 rounded text-xs font-display transition-all"
            style={{
              background: showAnalysis
                ? colors.gold.standard
                : colors.void.light,
              color: showAnalysis ? colors.void.deepest : colors.text.dim,
              border: `1px solid ${showAnalysis ? colors.gold.standard : colors.border.subtle}`,
            }}
          >
            <i className="ms ms-saga mr-1" style={{ fontSize: 10 }} />
            {showAnalysis ? "Hide Details" : "Analysis"}
          </button>
          <button
            onClick={() => setShowCombos(!showCombos)}
            className="px-3 py-1.5 rounded text-xs font-display transition-all"
            style={{
              background: showCombos ? colors.gold.standard : colors.void.light,
              color: showCombos ? colors.void.deepest : colors.text.dim,
              border: `1px solid ${showCombos ? colors.gold.standard : colors.border.subtle}`,
            }}
          >
            <i className="ms ms-instant mr-1" style={{ fontSize: 10 }} />
            {showCombos ? "Hide Combos" : "Combos"}
          </button>
        </div>
      </div>

      {/* Detailed Analysis Panel - Compact, Colorful Design */}
      {showAnalysis && healthData && (
        <div
          className="border-t overflow-auto"
          style={{
            background: colors.void.deep,
            borderColor: colors.border.subtle,
            maxHeight: "320px",
          }}
        >
          <div
            className="grid gap-0"
            style={{
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            }}
          >
            {/* Column 1: Themes */}
            <div
              className="p-3 border-r border-b"
              style={{ borderColor: colors.border.subtle }}
            >
              <div
                className="font-display text-base mb-2 flex items-center gap-2"
                style={{ color: colors.gold.standard }}
              >
                <span className="text-lg">🎭</span>
                <span>Themes</span>
              </div>
              {(healthData.themes?.length ?? 0) > 0 ? (
                <div className="space-y-2">
                  {healthData.themes?.slice(0, 5).map((theme) => (
                    <div key={theme.name}>
                      <div className="flex items-baseline gap-2">
                        <span
                          className="text-base font-semibold"
                          style={{ color: colors.text.bright }}
                        >
                          {theme.name}
                        </span>
                        <span
                          className="text-base font-mono"
                          style={{ color: colors.gold.standard }}
                        >
                          {theme.card_count}
                        </span>
                      </div>
                      {theme.description && (
                        <div
                          className="text-sm mt-0.5"
                          style={{ color: colors.text.dim }}
                        >
                          {theme.description}
                        </div>
                      )}
                    </div>
                  ))}
                  {healthData.dominant_tribe && (
                    <div
                      className="flex items-baseline gap-2 pt-1 mt-1 border-t"
                      style={{ borderColor: colors.border.subtle }}
                    >
                      <span
                        className="text-base font-semibold"
                        style={{ color: colors.mana.green.color }}
                      >
                        Tribal: {healthData.dominant_tribe}
                      </span>
                      {healthData.tribal_count && (
                        <span
                          className="text-base font-mono"
                          style={{ color: colors.gold.standard }}
                        >
                          {healthData.tribal_count}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm" style={{ color: colors.text.dim }}>
                  No themes detected
                </p>
              )}
            </div>

            {/* Column 2: Matchups */}
            <div
              className="p-3 border-r border-b"
              style={{ borderColor: colors.border.subtle }}
            >
              <div
                className="font-display text-base mb-2 flex items-center gap-2"
                style={{ color: colors.gold.standard }}
              >
                <span className="text-lg">⚔️</span>
                <span>Matchups</span>
              </div>
              {healthData.matchups ? (
                <div className="space-y-2">
                  {(healthData.matchups.strong_against?.length ?? 0) > 0 && (
                    <div>
                      <div
                        className="text-sm font-semibold mb-1"
                        style={{ color: colors.status.success }}
                      >
                        ✓ Strong vs
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {healthData.matchups.strong_against?.map((m) => (
                          <span
                            key={m}
                            className="text-sm px-2 py-0.5 rounded"
                            style={{
                              background: "rgba(126,200,80,0.15)",
                              color: colors.status.success,
                            }}
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {(healthData.matchups.weak_against?.length ?? 0) > 0 && (
                    <div>
                      <div
                        className="text-sm font-semibold mb-1"
                        style={{ color: colors.status.error }}
                      >
                        ✗ Weak to
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {healthData.matchups.weak_against?.map((m) => (
                          <span
                            key={m}
                            className="text-sm px-2 py-0.5 rounded"
                            style={{
                              background: "rgba(255,85,85,0.15)",
                              color: colors.status.error,
                            }}
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm" style={{ color: colors.text.dim }}>
                  Add themed cards
                </p>
              )}
            </div>

            {/* Column 3: Card Synergies */}
            <div
              className="p-3 border-r border-b"
              style={{ borderColor: colors.border.subtle }}
            >
              <div
                className="font-display text-base mb-2 flex items-center gap-2"
                style={{ color: colors.gold.standard }}
              >
                <span className="text-lg">🔗</span>
                <span>Synergies</span>
              </div>
              {(healthData.synergy_pairs?.length ?? 0) > 0 ? (
                <div className="space-y-1.5">
                  {healthData.synergy_pairs?.slice(0, 4).map((pair, idx) => (
                    <div key={idx}>
                      <div
                        className="text-sm font-medium"
                        style={{ color: colors.text.bright }}
                      >
                        {pair.card1}
                        <span style={{ color: colors.gold.standard }}> + </span>
                        {pair.card2}
                      </div>
                      <div
                        className="text-xs"
                        style={{ color: colors.text.muted }}
                      >
                        {pair.reason}
                        <span
                          className="ml-2 px-1.5 py-0.5 rounded"
                          style={{
                            background: colors.void.lighter,
                            color: colors.gold.dim,
                          }}
                        >
                          {pair.category}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm" style={{ color: colors.text.dim }}>
                  No synergies found
                </p>
              )}
            </div>

            {/* Column 4: Health & Keywords */}
            <div
              className="p-3 border-b"
              style={{ borderColor: colors.border.subtle }}
            >
              <div
                className="font-display text-base mb-2 flex items-center gap-2"
                style={{ color: colors.gold.standard }}
              >
                <span className="text-lg">🏥</span>
                <span>Health</span>
              </div>

              {/* Issues */}
              {(healthData.issues?.length ?? 0) > 0 ? (
                <div className="space-y-1 mb-3">
                  {healthData.issues?.slice(0, 3).map((issue, idx) => (
                    <div
                      key={idx}
                      className="text-sm flex items-start gap-1.5"
                      style={{
                        color:
                          issue.severity === "error"
                            ? colors.status.error
                            : colors.status.warning,
                      }}
                    >
                      <span>{issue.severity === "error" ? "⚠" : "△"}</span>
                      <span>{issue.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  className="text-sm mb-3 flex items-center gap-1.5"
                  style={{ color: colors.status.success }}
                >
                  <span>✓</span>
                  <span>Well-balanced!</span>
                </div>
              )}

              {/* Card count + CMC */}
              <div
                className="text-sm mb-3 flex items-center gap-3"
                style={{ color: colors.text.standard }}
              >
                <span
                  style={{
                    color:
                      healthData.total_cards >= healthData.expected_cards
                        ? colors.status.success
                        : colors.status.error,
                  }}
                >
                  {healthData.total_cards}/{healthData.expected_cards} cards
                </span>
                <span style={{ color: colors.text.muted }}>
                  CMC {healthData.average_cmc.toFixed(1)}
                </span>
              </div>

              {/* Keywords inline */}
              {(healthData.top_keywords?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1">
                  {healthData.top_keywords?.slice(0, 5).map((kw) => (
                    <span
                      key={kw.keyword}
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        background: colors.void.lighter,
                        color: colors.text.dim,
                      }}
                    >
                      {kw.keyword}
                      <span
                        style={{ color: colors.gold.standard, marginLeft: 4 }}
                      >
                        ×{kw.count}
                      </span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Combo Detection Panel */}
      {showCombos && deck.cards.length > 0 && (
        <div
          className="border-t"
          style={{
            background: colors.void.deep,
            borderColor: colors.border.subtle,
            maxHeight: "300px",
            overflow: "auto",
          }}
        >
          <ComboDetectionPanel cardNames={deck.cards.map((c) => c.card_name)} />
        </div>
      )}

      {/* Card Detail Modal */}
      {selectedCardName && (
        <CardDetailModal
          cardName={selectedCardName}
          onClose={() => setSelectedCardName(null)}
        />
      )}
    </div>
  );
}

export default DeckBuilderScreen;
