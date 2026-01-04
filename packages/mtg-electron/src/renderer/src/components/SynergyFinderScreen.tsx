/**
 * Synergy Finder Screen
 * Discover cards that synergize with a selected source card.
 * Displays synergies grouped by category with animated connections.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { colors, synergyColors, gradients } from "../theme";
import { CardDetailModal } from "./CardDetailModal";
import { ManaCost, CardText } from "./ManaSymbols";

import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

// Use generated types from OpenAPI schema
type CardSummary = components["schemas"]["CardSummary"];
type CardDetail = components["schemas"]["CardDetail"];
type SynergyResult = components["schemas"]["SynergyResult"];
type SynergyType = SynergyResult["synergy_type"];

// Grouped synergies by category (transformed from API's flat array)
interface SynergyCategory {
  type: SynergyType;
  name: string;
  description: string;
  cards: SynergyResult[];
  average_score: number;
}

// Category icon mapping (using mana-font icons)
const CATEGORY_ICONS: Record<string, string> = {
  keyword: "ms ms-ability-flying",
  tribal: "ms ms-creature",
  ability: "ms ms-ability-activated",
  mana: "ms ms-c",
  combo: "ms ms-instant",
  strategy: "ms ms-saga",
  type: "ms ms-artifact",
  default: "ms ms-ability-constellation",
};

// Get synergy color for category
function getCategoryColor(type: string): { color: string; glow: string } {
  const key = type.toLowerCase() as keyof typeof synergyColors;
  return synergyColors[key] || synergyColors.strategy;
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

export function SynergyFinderScreen(): ReactNode {
  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<CardSummary[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [sourceCard, setSourceCard] = useState<CardDetail | null>(null);
  const [synergies, setSynergies] = useState<SynergyCategory[]>([]);
  const [isLoadingSynergies, setIsLoadingSynergies] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [hoveredCardName, setHoveredCardName] = useState<string | null>(null);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Centralized hover handlers to ensure only one tooltip at a time
  const handleCardHover = useCallback((card: SynergyResult | null) => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    if (card) {
      // Immediately show new tooltip
      setHoveredCardName(card.name);
    } else {
      // Delay hiding to prevent flicker
      hoverTimeoutRef.current = setTimeout(() => {
        setHoveredCardName(null);
      }, 150);
    }
  }, []);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);
  const [formatFilter, setFormatFilter] = useState<string | null>(null);

  const debouncedSearch = useDebounce(searchQuery, 300);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Track current format filter in a ref to avoid stale closures in async callbacks
  const formatFilterRef = useRef(formatFilter);
  useEffect(() => {
    formatFilterRef.current = formatFilter;
  }, [formatFilter]);

  // Request ID to detect stale responses from in-flight requests
  const requestIdRef = useRef(0);

  // Search for cards
  useEffect(() => {
    if (!debouncedSearch || debouncedSearch.length < 2) {
      setSearchResults([]);
      return;
    }

    const search = async (): Promise<void> => {
      setIsSearching(true);
      try {
        const result = await window.electronAPI.api.cards.search({
          name: debouncedSearch,
          page_size: 10,
        });
        setSearchResults(result.cards || []);
      } catch (error) {
        console.error("Search failed:", error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    };

    search();
  }, [debouncedSearch]);

  // Select a source card
  // Uses refs to avoid race conditions when format filter changes mid-request
  const handleSelectCard = useCallback(
    async (card: CardSummary) => {
      setSearchQuery("");
      setSearchResults([]);
      setIsLoadingSynergies(true);
      setSynergies([]);

      // Capture the current request ID and format filter at call time
      const thisRequestId = ++requestIdRef.current;
      const currentFormatFilter = formatFilterRef.current;

      try {
        // Get full card details
        const details = await window.electronAPI.api.cards.getByName(card.name);

        // Check if this request is still valid (no newer request started)
        if (thisRequestId !== requestIdRef.current) {
          return; // Stale request, discard results
        }

        setSourceCard(details);

        // Find synergies using the format filter captured at call time
        const result = await window.electronAPI.api.synergies.find(card.name, {
          limit: 50,
          formatLegal: currentFormatFilter || undefined,
        });

        // Check again after synergies API call
        if (thisRequestId !== requestIdRef.current) {
          return; // Stale request, discard results
        }

        // Transform API result: group flat synergies array by synergy_type
        if (result && result.synergies && result.synergies.length > 0) {
          // Group by synergy_type
          const grouped = result.synergies.reduce(
            (acc, synergy) => {
              const type = synergy.synergy_type;
              if (!acc[type]) {
                acc[type] = [];
              }
              acc[type].push(synergy);
              return acc;
            },
            {} as Record<SynergyType, SynergyResult[]>,
          );

          // Convert to SynergyCategory array
          const categories: SynergyCategory[] = Object.entries(grouped).map(
            ([type, cards]) => ({
              type: type as SynergyType,
              name: type.charAt(0).toUpperCase() + type.slice(1),
              description: getTypeDescription(type),
              cards,
              average_score:
                cards.reduce((sum, c) => sum + c.score, 0) / cards.length,
            }),
          );

          // Sort by average score descending
          categories.sort((a, b) => b.average_score - a.average_score);
          setSynergies(categories);
        }
      } catch (error) {
        // Only log error if this is still the active request
        if (thisRequestId === requestIdRef.current) {
          console.error("Failed to load synergies:", error);
        }
      } finally {
        // Only update loading state if this is still the active request
        if (thisRequestId === requestIdRef.current) {
          setIsLoadingSynergies(false);
        }
      }
    },
    [], // Empty deps - uses refs instead of closure over formatFilter
  );

  // Get description for synergy type
  function getTypeDescription(type: string): string {
    const descriptions: Record<string, string> = {
      keyword: "Cards that share or synergize with keywords",
      tribal: "Cards that synergize with creature types",
      ability: "Cards with complementary activated or triggered abilities",
      mana: "Cards that synergize with mana costs or generation",
      combo: "Cards that form powerful combinations",
      strategy: "Cards that support similar strategies",
      type: "Cards that synergize with card types",
    };
    return descriptions[type.toLowerCase()] || "Related cards";
  }

  // Clear source card
  const handleClearSource = useCallback(() => {
    setSourceCard(null);
    setSynergies([]);
    setSelectedCategory(null);
    searchInputRef.current?.focus();
  }, []);

  // View card details
  const handleViewCard = useCallback((cardName: string) => {
    setSelectedCardName(cardName);
  }, []);

  // Calculate total synergies
  const totalSynergies = synergies.reduce(
    (sum, cat) => sum + cat.cards.length,
    0,
  );

  return (
    <div
      className="h-full flex flex-col relative overflow-hidden"
      style={{ background: colors.void.deepest }}
    >
      {/* Ambient background effect */}
      <SynergyAmbient synergies={synergies} />

      {/* Header */}
      <header
        className="relative z-10 p-4 border-b"
        style={{
          background: `linear-gradient(180deg, ${colors.void.deep} 0%, ${colors.void.deepest} 100%)`,
          borderColor: colors.border.subtle,
        }}
      >
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            {/* Icon */}
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.gold.dim}`,
                boxShadow: `0 0 20px ${colors.gold.glow}`,
              }}
            >
              <i
                className="ms ms-ability-constellation"
                style={{ color: colors.gold.standard, fontSize: 20 }}
              />
            </div>

            {/* Title */}
            <div>
              <h1
                className="font-display text-xl tracking-widest"
                style={{ color: colors.gold.standard }}
              >
                SYNERGY FINDER
              </h1>
              <p className="text-xs" style={{ color: colors.text.muted }}>
                Discover hidden connections between cards
              </p>
            </div>

            {/* Search input */}
            <div className="flex-1 ml-8 relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for a card to find synergies..."
                className="w-full h-10 px-4 rounded-lg text-sm"
                style={{
                  background: colors.void.medium,
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.standard,
                }}
              />

              {/* Search results dropdown */}
              {searchResults.length > 0 && (
                <div
                  className="absolute top-full left-0 right-0 mt-1 rounded-lg overflow-hidden z-50"
                  style={{
                    background: colors.void.medium,
                    border: `1px solid ${colors.border.standard}`,
                    boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                  }}
                >
                  {searchResults.map((card) => (
                    <button
                      key={card.uuid}
                      onClick={() => handleSelectCard(card)}
                      className="w-full flex items-center gap-3 px-4 py-2 text-left transition-colors"
                      style={{
                        borderBottom: `1px solid ${colors.border.subtle}`,
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background = colors.void.light)
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      {card.image_small && (
                        <img
                          src={card.image_small}
                          alt=""
                          className="w-8 h-11 rounded object-cover"
                          loading="lazy"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div
                          className="text-sm truncate"
                          style={{ color: colors.text.standard }}
                        >
                          {card.name}
                        </div>
                        <div
                          className="text-xs truncate"
                          style={{ color: colors.text.muted }}
                        >
                          {card.type}
                        </div>
                      </div>
                      {card.mana_cost && (
                        <ManaCost cost={card.mana_cost} size="small" />
                      )}
                    </button>
                  ))}
                </div>
              )}

              {isSearching && (
                <div
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: colors.text.muted }}
                >
                  <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                </div>
              )}
            </div>

            {/* Format filter */}
            <select
              value={formatFilter || ""}
              onChange={(e) => setFormatFilter(e.target.value || null)}
              className="h-10 px-3 rounded-lg text-sm"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.standard}`,
                color: colors.text.standard,
              }}
            >
              <option value="">All Formats</option>
              <option value="commander">Commander</option>
              <option value="modern">Modern</option>
              <option value="legacy">Legacy</option>
              <option value="standard">Standard</option>
              <option value="pioneer">Pioneer</option>
            </select>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left panel - Source card */}
        <aside
          className="w-80 p-6 border-r flex flex-col overflow-auto"
          style={{
            background: colors.void.deep,
            borderColor: colors.border.subtle,
          }}
        >
          {sourceCard ? (
            <SourceCardPanel card={sourceCard} onClear={handleClearSource} />
          ) : (
            <EmptySourceState />
          )}

          {/* Synergy summary */}
          {sourceCard && synergies.length > 0 && (
            <div
              className="mt-4 p-3 rounded-lg"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <i
                  className="ms ms-ability-constellation"
                  style={{ color: colors.gold.standard, fontSize: 14 }}
                />
                <span
                  className="text-xs font-display"
                  style={{ color: colors.text.muted }}
                >
                  SYNERGIES FOUND
                </span>
              </div>
              <div
                className="text-2xl font-display"
                style={{ color: colors.gold.standard }}
              >
                {totalSynergies}
              </div>
              <div className="text-xs" style={{ color: colors.text.muted }}>
                across {synergies.length} categories
              </div>
            </div>
          )}
        </aside>

        {/* Right panel - Synergies */}
        <section className="flex-1 p-6 overflow-auto">
          {isLoadingSynergies ? (
            <LoadingState />
          ) : synergies.length > 0 ? (
            <SynergyConstellation
              categories={synergies}
              selectedCategory={selectedCategory}
              onSelectCategory={setSelectedCategory}
              onHoverCard={handleCardHover}
              hoveredCardName={hoveredCardName}
              onViewCard={handleViewCard}
            />
          ) : sourceCard ? (
            <NoSynergiesState />
          ) : (
            <EmptySynergyState />
          )}
        </section>
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

// Source card panel component
function SourceCardPanel({
  card,
  onClear,
}: {
  card: CardDetail;
  onClear: () => void;
}): ReactNode {
  return (
    <div
      className="flex flex-col"
      style={{ animation: "reveal-up 0.4s ease-out" }}
    >
      {/* Card image with glow */}
      <div className="relative mb-4">
        <div
          className="absolute inset-0 rounded-lg blur-xl"
          style={{
            background: colors.gold.glow,
            transform: "scale(0.8)",
            opacity: 0.5,
          }}
        />

        <div
          className="relative rounded-lg overflow-hidden"
          style={{
            border: `2px solid ${colors.gold.dim}`,
            boxShadow: `0 0 30px ${colors.gold.glow}, inset 0 0 20px rgba(0,0,0,0.5)`,
          }}
        >
          {card.images?.normal ? (
            <img
              src={card.images.normal}
              alt={card.name}
              className="w-full"
              style={{ aspectRatio: "488/680" }}
              loading="lazy"
            />
          ) : (
            <div
              className="w-full flex items-center justify-center"
              style={{
                aspectRatio: "488/680",
                background: colors.void.medium,
              }}
            >
              <span style={{ color: colors.text.muted }}>No image</span>
            </div>
          )}
        </div>

        {/* Clear button */}
        <button
          onClick={onClear}
          className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center transition-all hover:scale-110"
          style={{
            background: colors.void.medium,
            border: `1px solid ${colors.border.standard}`,
            color: colors.text.muted,
          }}
        >
          x
        </button>
      </div>

      {/* Card info */}
      <h2
        className="font-display text-lg mb-1"
        style={{ color: colors.text.bright }}
      >
        {card.name}
      </h2>

      <div className="flex items-center gap-2 mb-3">
        {card.mana_cost && <ManaCost cost={card.mana_cost} size="small" />}
        <span className="text-xs" style={{ color: colors.text.muted }}>
          {card.type}
        </span>
      </div>

      {/* Keywords */}
      {card.keywords && card.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {card.keywords.map((kw) => (
            <span
              key={kw}
              className="px-2 py-0.5 text-xs rounded-full"
              style={{
                background: `${synergyColors.keyword.color}20`,
                border: `1px solid ${synergyColors.keyword.color}40`,
                color: synergyColors.keyword.color,
              }}
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Oracle text with mana symbols */}
      {card.text && (
        <div
          className="text-sm leading-relaxed"
          style={{ color: colors.text.dim }}
        >
          <CardText text={card.text} size="small" />
        </div>
      )}
    </div>
  );
}

// Synergy constellation component
function SynergyConstellation({
  categories,
  selectedCategory,
  onSelectCategory,
  onHoverCard,
  hoveredCardName,
  onViewCard,
}: {
  categories: SynergyCategory[];
  selectedCategory: string | null;
  onSelectCategory: (cat: string | null) => void;
  onHoverCard: (card: SynergyResult | null) => void;
  hoveredCardName: string | null;
  onViewCard: (name: string) => void;
}): ReactNode {
  return (
    <div className="space-y-6">
      {/* Category tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => onSelectCategory(null)}
          className="px-4 py-2 rounded-lg text-sm font-display tracking-wide transition-all whitespace-nowrap"
          style={{
            background: !selectedCategory
              ? colors.void.lighter
              : colors.void.light,
            color: !selectedCategory ? colors.gold.standard : colors.text.dim,
            border: `1px solid ${!selectedCategory ? colors.gold.dim : colors.border.subtle}`,
          }}
        >
          All Synergies
        </button>

        {categories.map((cat) => {
          const catColor = getCategoryColor(cat.type);
          const isSelected = selectedCategory === cat.type;
          return (
            <button
              key={cat.type}
              onClick={() => onSelectCategory(cat.type)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-display tracking-wide transition-all whitespace-nowrap"
              style={{
                background: isSelected
                  ? `${catColor.color}20`
                  : colors.void.light,
                border: `1px solid ${isSelected ? catColor.color : colors.border.subtle}`,
                color: isSelected ? catColor.color : colors.text.dim,
                boxShadow: isSelected ? `0 0 15px ${catColor.glow}` : "none",
              }}
            >
              <i
                className={
                  CATEGORY_ICONS[cat.type.toLowerCase()] ||
                  CATEGORY_ICONS.default
                }
                style={{ fontSize: 14 }}
              />
              <span>{cat.name}</span>
              <span
                className="px-1.5 py-0.5 rounded text-xs"
                style={{
                  background: isSelected ? catColor.color : colors.void.medium,
                  color: isSelected ? colors.void.deepest : colors.text.muted,
                }}
              >
                {cat.cards.length}
              </span>
            </button>
          );
        })}
      </div>

      {/* Synergy groups */}
      <div className="grid gap-6">
        {categories
          .filter((cat) => !selectedCategory || cat.type === selectedCategory)
          .map((category, idx) => (
            <SynergyGroup
              key={category.type}
              category={category}
              onHoverCard={onHoverCard}
              hoveredCardName={hoveredCardName}
              onViewCard={onViewCard}
              delay={idx * 0.1}
            />
          ))}
      </div>
    </div>
  );
}

// Synergy group component
function SynergyGroup({
  category,
  onHoverCard,
  hoveredCardName,
  onViewCard,
  delay,
}: {
  category: SynergyCategory;
  onHoverCard: (card: SynergyResult | null) => void;
  hoveredCardName: string | null;
  onViewCard: (name: string) => void;
  delay: number;
}): ReactNode {
  const [isExpanded, setIsExpanded] = useState(true);
  const catColor = getCategoryColor(category.type);

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: `linear-gradient(180deg, ${colors.void.light} 0%, ${colors.void.medium} 100%)`,
        border: `1px solid ${colors.border.subtle}`,
        animation: `reveal-up 0.4s ease-out ${delay}s both`,
      }}
    >
      {/* Group header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-4 p-4 transition-colors"
        style={{
          borderBottom: isExpanded
            ? `1px solid ${colors.border.subtle}`
            : "none",
        }}
      >
        {/* Category icon */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{
            background: `${catColor.color}20`,
            border: `1px solid ${catColor.color}40`,
            boxShadow: `0 0 20px ${catColor.glow}`,
          }}
        >
          <i
            className={
              CATEGORY_ICONS[category.type.toLowerCase()] ||
              CATEGORY_ICONS.default
            }
            style={{ color: catColor.color, fontSize: 18 }}
          />
        </div>

        <div className="flex-1 text-left">
          <h3
            className="font-display text-sm tracking-wider"
            style={{ color: catColor.color }}
          >
            {category.name.toUpperCase()}
          </h3>
          <p className="text-xs" style={{ color: colors.text.muted }}>
            {category.description}
          </p>
        </div>

        {/* Score indicator (score is 0-1, display as 5 bars) */}
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((level) => (
            <div
              key={level}
              className="w-1.5 h-4 rounded-full"
              style={{
                background:
                  level <= Math.round(category.average_score * 5)
                    ? catColor.color
                    : colors.void.lighter,
                boxShadow:
                  level <= Math.round(category.average_score * 5)
                    ? `0 0 4px ${catColor.glow}`
                    : "none",
              }}
            />
          ))}
        </div>

        {/* Expand/collapse */}
        <div
          style={{
            color: colors.text.muted,
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>

      {/* Cards list - compact, scannable rows */}
      {isExpanded && (
        <div className="px-4 pb-4 flex flex-col gap-1">
          {category.cards.map((card, idx) => (
            <SynergyCardRow
              key={card.name}
              card={card}
              categoryColor={catColor.color}
              delay={idx * 0.02}
              onHover={onHoverCard}
              isTooltipVisible={hoveredCardName === card.name}
              onClick={() => onViewCard(card.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Synergy card row - editorial data-dense design with accessibility
function SynergyCardRow({
  card,
  categoryColor,
  delay,
  onHover,
  isTooltipVisible,
  onClick,
}: {
  card: SynergyResult;
  categoryColor: string;
  delay: number;
  onHover: (card: SynergyResult | null) => void;
  isTooltipVisible: boolean;
  onClick: () => void;
}): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<"top" | "bottom">(
    "top",
  );
  const rowRef = useRef<HTMLDivElement>(null);

  // Score determines left border intensity (0.3 to 1.0 opacity)
  const scoreOpacity = 0.3 + card.score * 0.7;

  // Check what data we have available
  const hasGameplayData =
    card.synergy_lift != null || card.tier != null || card.gih_wr != null;
  const hasKeywords = card.keywords && card.keywords.length > 0;

  // Smart tooltip positioning - check if near top of viewport
  useEffect(() => {
    if (isTooltipVisible && rowRef.current) {
      const rect = rowRef.current.getBoundingClientRect();
      // If row is within 200px of top, show tooltip below
      setTooltipPosition(rect.top < 200 ? "bottom" : "top");
    }
  }, [isTooltipVisible]);

  // Hover handlers - parent manages tooltip visibility
  const handleMouseEnter = (): void => {
    setIsHovered(true);
    onHover(card);
  };

  const handleMouseLeave = (): void => {
    setIsHovered(false);
    onHover(null);
  };

  // Keyboard support
  const handleFocus = (): void => {
    setIsHovered(true);
    onHover(card);
  };

  const handleBlur = (): void => {
    setIsHovered(false);
    onHover(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent): void => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  // Generate unique ID for ARIA
  const tooltipId = `synergy-tooltip-${card.name.replace(/\s+/g, "-").toLowerCase()}`;

  return (
    <div
      ref={rowRef}
      className="group cursor-pointer relative"
      style={{
        animation: `reveal-up 0.25s ease-out ${delay}s both`,
      }}
      tabIndex={0}
      role="button"
      aria-label={`${card.name} - ${card.reason}`}
      aria-describedby={isHovered ? tooltipId : undefined}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      onClick={onClick}
    >
      {/* Main row */}
      <div
        className="flex items-center gap-3 px-3 py-2 rounded transition-all duration-150"
        style={{
          background: isHovered ? colors.void.light : "transparent",
          borderLeft: `3px solid`,
          borderLeftColor: isHovered
            ? categoryColor
            : `rgba(${hexToRgb(categoryColor)}, ${scoreOpacity})`,
          transform: isHovered ? "translateX(4px)" : "none",
        }}
      >
        {/* Card name - primary anchor */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <span
            className="font-medium truncate transition-colors duration-150"
            style={{
              color: isHovered ? colors.text.bright : colors.text.standard,
              fontSize: "13px",
              letterSpacing: "-0.01em",
            }}
          >
            {card.name}
          </span>

          {/* Mana cost inline */}
          {card.mana_cost && (
            <span className="flex-shrink-0 opacity-80">
              <ManaCost cost={card.mana_cost} size="small" />
            </span>
          )}

          {/* Tier badge if available */}
          {card.tier && (
            <span
              className="flex-shrink-0 text-xs px-1.5 py-0.5 rounded font-bold"
              style={{
                background: getTierColor(card.tier),
                color: colors.void.deepest,
                fontSize: "10px",
              }}
            >
              {card.tier}
            </span>
          )}
        </div>

        {/* Type - subtle, truncated */}
        <span
          className="hidden sm:block flex-shrink-0 truncate text-xs"
          style={{
            color: colors.text.muted,
            maxWidth: "140px",
          }}
        >
          {card.type_line
            ?.replace("Legendary ", "")
            .replace("Creature — ", "") || ""}
        </span>

        {/* Synergy reason - the star */}
        <span
          className="flex-shrink-0 text-xs px-2 py-0.5 rounded"
          style={{
            background: `${categoryColor}18`,
            color: categoryColor,
            maxWidth: "200px",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            fontWeight: 500,
            letterSpacing: "0.01em",
          }}
        >
          {card.reason}
        </span>

        {/* Score indicator - subtle dots */}
        <div className="flex-shrink-0 flex gap-0.5">
          {[1, 2, 3, 4, 5].map((level) => (
            <div
              key={level}
              className="w-1 h-1 rounded-full transition-all duration-150"
              style={{
                background:
                  level <= Math.round(card.score * 5)
                    ? categoryColor
                    : colors.void.lighter,
                opacity: level <= Math.round(card.score * 5) ? 1 : 0.3,
              }}
            />
          ))}
        </div>
      </div>

      {/* Floating tooltip on hover - smart positioning */}
      {isTooltipVisible && (
        <div
          id={tooltipId}
          role="tooltip"
          className={`absolute left-0 right-0 p-3 rounded-lg z-50 ${
            tooltipPosition === "top" ? "bottom-full mb-2" : "top-full mt-2"
          }`}
          style={{
            background: colors.void.deep,
            border: `1px solid ${categoryColor}40`,
            boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 20px ${categoryColor}15`,
            animation:
              tooltipPosition === "top"
                ? "fade-in-up 0.15s ease-out"
                : "fade-in-down 0.15s ease-out",
          }}
        >
          {/* Arrow pointer - position based on tooltip direction */}
          {tooltipPosition === "top" ? (
            <>
              <div
                className="absolute left-6 top-full w-0 h-0"
                style={{
                  borderLeft: "8px solid transparent",
                  borderRight: "8px solid transparent",
                  borderTop: `8px solid ${categoryColor}40`,
                }}
              />
              <div
                className="absolute left-6 top-full w-0 h-0"
                style={{
                  borderLeft: "7px solid transparent",
                  borderRight: "7px solid transparent",
                  borderTop: `7px solid ${colors.void.deep}`,
                  marginLeft: "1px",
                  marginTop: "-1px",
                }}
              />
            </>
          ) : (
            <>
              <div
                className="absolute left-6 bottom-full w-0 h-0"
                style={{
                  borderLeft: "8px solid transparent",
                  borderRight: "8px solid transparent",
                  borderBottom: `8px solid ${categoryColor}40`,
                }}
              />
              <div
                className="absolute left-6 bottom-full w-0 h-0"
                style={{
                  borderLeft: "7px solid transparent",
                  borderRight: "7px solid transparent",
                  borderBottom: `7px solid ${colors.void.deep}`,
                  marginLeft: "1px",
                  marginBottom: "-1px",
                }}
              />
            </>
          )}

          {/* Tooltip header with card name */}
          <div
            className="flex items-center gap-2 mb-2 pb-2"
            style={{ borderBottom: `1px solid ${colors.border.subtle}` }}
          >
            <span
              className="font-medium"
              style={{ color: colors.text.bright, fontSize: "14px" }}
            >
              {card.name}
            </span>
            {card.tier && (
              <span
                className="px-1.5 py-0.5 rounded font-bold"
                style={{
                  background: getTierColor(card.tier),
                  color: colors.void.deepest,
                  fontSize: "11px",
                }}
              >
                {card.tier}-Tier
              </span>
            )}
          </div>

          {/* Synergy reason - pull-quote style */}
          <div
            className="px-3 py-2 rounded-lg mb-3"
            style={{
              background: `${categoryColor}10`,
              borderLeft: `3px solid ${categoryColor}`,
            }}
          >
            <p
              style={{
                color: colors.text.bright,
                fontSize: "13px",
                lineHeight: 1.5,
                fontStyle: "italic",
                margin: 0,
              }}
            >
              {card.reason}
            </p>
          </div>

          {/* Card classification badges */}
          {(card.is_bomb || card.is_synergy_dependent) && (
            <div className="flex gap-2 mb-3">
              {card.is_bomb && (
                <span
                  className="px-2 py-1 rounded text-xs font-bold"
                  style={{
                    background: `${colors.status.error}20`,
                    border: `1px solid ${colors.status.error}40`,
                    color: colors.status.error,
                  }}
                >
                  💣 Bomb
                </span>
              )}
              {card.is_synergy_dependent && (
                <span
                  className="px-2 py-1 rounded text-xs font-bold"
                  style={{
                    background: `${categoryColor}20`,
                    border: `1px solid ${categoryColor}40`,
                    color: categoryColor,
                  }}
                >
                  🔗 Synergy-dependent
                </span>
              )}
            </div>
          )}

          {/* Stats row - compact horizontal layout with better sizing */}
          {(hasGameplayData ||
            card.price_usd != null ||
            card.edhrec_rank != null) && (
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {card.synergy_lift != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    Synergy lift
                  </span>
                  <span
                    className="font-bold"
                    style={{
                      color:
                        card.synergy_lift > 0
                          ? colors.status.success
                          : card.synergy_lift < -0.02
                            ? colors.status.error
                            : colors.text.standard,
                      fontSize: "14px",
                    }}
                  >
                    {card.synergy_lift > 0
                      ? "↑ +"
                      : card.synergy_lift < -0.02
                        ? "↓ "
                        : ""}
                    {(card.synergy_lift * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {card.win_rate_together != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    WR together
                  </span>
                  <span
                    className="font-bold"
                    style={{ color: colors.text.bright, fontSize: "14px" }}
                  >
                    {(card.win_rate_together * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {card.gih_wr != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    GIH WR
                  </span>
                  <span
                    className="font-bold"
                    style={{ color: colors.text.bright, fontSize: "14px" }}
                  >
                    {(card.gih_wr * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {card.iwd != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    IWD
                  </span>
                  <span
                    className="font-bold"
                    style={{
                      color:
                        card.iwd > 0
                          ? colors.status.success
                          : card.iwd < 0
                            ? colors.status.error
                            : colors.text.standard,
                      fontSize: "14px",
                    }}
                  >
                    {card.iwd > 0 ? "+" : ""}
                    {(card.iwd * 100).toFixed(1)}%
                  </span>
                </div>
              )}

              {card.sample_size != null && card.sample_size > 0 && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    Games
                  </span>
                  <span
                    style={{ color: colors.text.standard, fontSize: "14px" }}
                  >
                    {card.sample_size.toLocaleString()}
                  </span>
                </div>
              )}

              {card.price_usd != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    Price
                  </span>
                  <span
                    style={{ color: colors.gold.standard, fontSize: "14px" }}
                  >
                    ${card.price_usd.toFixed(2)}
                  </span>
                </div>
              )}

              {card.edhrec_rank != null && (
                <div className="flex items-baseline gap-1.5">
                  <span
                    style={{
                      color: colors.text.dim,
                      fontSize: "11px",
                      fontWeight: 500,
                    }}
                  >
                    EDHREC
                  </span>
                  <span
                    style={{ color: colors.text.standard, fontSize: "14px" }}
                  >
                    #{card.edhrec_rank.toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Best archetypes */}
          {card.best_archetypes && card.best_archetypes.length > 0 && (
            <div className="mt-3 flex items-center gap-2">
              <span
                style={{
                  color: colors.text.dim,
                  fontSize: "11px",
                  fontWeight: 500,
                }}
              >
                Best in:
              </span>
              <div className="flex gap-1">
                {card.best_archetypes.map((arch) => (
                  <span
                    key={arch}
                    className="px-1.5 py-0.5 rounded font-medium"
                    style={{
                      background: colors.void.lighter,
                      color: colors.text.standard,
                      fontSize: "11px",
                    }}
                  >
                    {arch}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Combo connections */}
          {card.combo_count != null && card.combo_count > 0 && (
            <div
              className="mt-3 p-2 rounded"
              style={{
                background: `${colors.gold.dim}15`,
                border: `1px solid ${colors.gold.dim}30`,
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span style={{ fontSize: "12px" }}>⚡</span>
                <span
                  style={{
                    color: colors.gold.standard,
                    fontSize: "11px",
                    fontWeight: 600,
                  }}
                >
                  {card.combo_count} known combo
                  {card.combo_count > 1 ? "s" : ""}
                </span>
              </div>
              {card.combo_preview && (
                <p
                  style={{
                    color: colors.text.dim,
                    fontSize: "11px",
                    margin: 0,
                    lineHeight: 1.4,
                  }}
                >
                  {card.combo_preview.length > 100
                    ? card.combo_preview.slice(0, 100) + "..."
                    : card.combo_preview}
                </p>
              )}
            </div>
          )}

          {/* Keywords - compact with better sizing */}
          {hasKeywords && card.keywords && (
            <div className="mt-3 flex flex-wrap gap-1">
              {card.keywords.slice(0, 6).map((kw) => (
                <span
                  key={kw}
                  className="px-1.5 py-0.5 rounded"
                  style={{
                    background: `${categoryColor}15`,
                    color: colors.text.dim,
                    fontSize: "11px",
                  }}
                >
                  {kw}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Get tier color for 17Lands tier badge
function getTierColor(tier: string): string {
  switch (tier.toUpperCase()) {
    case "S":
      return "#ff6b6b"; // Red/pink for S-tier
    case "A":
      return "#ffd93d"; // Gold for A-tier
    case "B":
      return "#6bcb77"; // Green for B-tier
    case "C":
      return "#4d96ff"; // Blue for C-tier
    case "D":
      return "#9d9d9d"; // Gray for D-tier
    case "F":
      return "#6c6c6c"; // Dark gray for F-tier
    default:
      return colors.text.muted;
  }
}

// Helper to convert hex to rgb for rgba()
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return "255, 255, 255";
  return `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`;
}

// Ambient background effect
function SynergyAmbient({
  synergies,
}: {
  synergies: SynergyCategory[];
}): ReactNode {
  // Get colors from synergy categories
  const activeColors = synergies.map((s) => getCategoryColor(s.type).color);

  return (
    <div
      className="absolute inset-0 pointer-events-none overflow-hidden"
      style={{ opacity: 0.3 }}
    >
      {/* Radial glow in center */}
      <div
        className="absolute top-1/2 left-1/3 w-96 h-96 -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl"
        style={{
          background: gradients.synergyGlow,
          animation: "pulse-glow 4s ease-in-out infinite",
        }}
      />

      {/* Category color spots */}
      {activeColors.slice(0, 3).map((color, idx) => (
        <div
          key={idx}
          className="absolute w-64 h-64 rounded-full blur-3xl"
          style={{
            background: color,
            opacity: 0.1,
            top: `${20 + idx * 25}%`,
            right: `${10 + idx * 15}%`,
            animation: `pulse-glow ${3 + idx}s ease-in-out infinite ${idx * 0.5}s`,
          }}
        />
      ))}
    </div>
  );
}

// Empty states
function EmptySourceState(): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
      <div
        className="w-16 h-16 rounded-xl flex items-center justify-center mb-4"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <i
          className="ms ms-ability-constellation"
          style={{ fontSize: 28, color: colors.text.muted, opacity: 0.5 }}
        />
      </div>
      <h3
        className="font-display text-sm mb-2"
        style={{ color: colors.text.dim }}
      >
        SELECT A CARD
      </h3>
      <p className="text-xs" style={{ color: colors.text.muted }}>
        Search for a card above to discover its synergies
      </p>
    </div>
  );
}

function EmptySynergyState(): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
      <div
        className="w-24 h-24 rounded-xl flex items-center justify-center mb-6"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <i
          className="ms ms-ability-constellation"
          style={{ fontSize: 40, color: colors.text.muted, opacity: 0.3 }}
        />
      </div>
      <h2
        className="font-display text-xl mb-3"
        style={{ color: colors.text.dim }}
      >
        DISCOVER SYNERGIES
      </h2>
      <p className="text-sm max-w-md" style={{ color: colors.text.muted }}>
        Search for a card to explore cards that synergize with it. Find hidden
        connections and build powerful combinations.
      </p>
    </div>
  );
}

function NoSynergiesState(): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-12">
      <div
        className="w-20 h-20 rounded-xl flex items-center justify-center mb-4"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <i
          className="ms ms-ability-constellation"
          style={{ fontSize: 32, color: colors.text.muted, opacity: 0.4 }}
        />
      </div>
      <h3
        className="font-display text-lg mb-2"
        style={{ color: colors.text.dim }}
      >
        NO SYNERGIES FOUND
      </h3>
      <p className="text-sm" style={{ color: colors.text.muted }}>
        Try selecting a different card or adjusting the format filter.
      </p>
    </div>
  );
}

function LoadingState(): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center">
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center mb-4"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.gold.dim}`,
          boxShadow: `0 0 20px ${colors.gold.glow}`,
          animation: "pulse-glow 1.5s ease-in-out infinite",
        }}
      >
        <i
          className="ms ms-ability-constellation"
          style={{ color: colors.gold.standard, fontSize: 24 }}
        />
      </div>
      <p className="text-sm font-display" style={{ color: colors.text.muted }}>
        DISCOVERING SYNERGIES...
      </p>
    </div>
  );
}

export default SynergyFinderScreen;
