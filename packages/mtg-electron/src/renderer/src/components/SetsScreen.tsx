/**
 * SetsScreen - Arcane Archives
 *
 * Browse MTG sets with the Arcane Library aesthetic.
 * Features constellation background, glowing selections, and
 * card grid with hover effects.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from "react";

import { colors } from "../theme";
import { getPriceColor } from "../utils/cardUtils";
import { ManaCost } from "./ManaSymbols";
import { CardDetailModal } from "./CardDetailModal";

import type { ReactNode, CSSProperties } from "react";
import type { components } from "../../../shared/types/api-generated";

type SetSummary = components["schemas"]["SetSummary"];
type SetDetail = components["schemas"]["SetDetail"];
type SetAnalysisResponse = components["schemas"]["SetAnalysisResponse"];
type CardSummary = components["schemas"]["CardSummary"];

// ═══════════════════════════════════════════════════════════════
// AMBIENT EFFECTS
// ═══════════════════════════════════════════════════════════════

function ConstellationBackground(): ReactNode {
  const lines = useMemo(() => {
    const points = Array.from({ length: 10 }, () => ({
      x: 10 + Math.random() * 80,
      y: 10 + Math.random() * 80,
    }));

    const connections: Array<{
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      delay: number;
    }> = [];

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = Math.hypot(
          points[i].x - points[j].x,
          points[i].y - points[j].y,
        );
        if (dist < 35 && connections.length < 12) {
          connections.push({
            x1: points[i].x,
            y1: points[i].y,
            x2: points[j].x,
            y2: points[j].y,
            delay: Math.random() * 5,
          });
        }
      }
    }

    return { points, connections };
  }, []);

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.05 }}
    >
      <defs>
        <linearGradient id="setLineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={colors.gold.dim} />
          <stop offset="100%" stopColor={colors.mana.blue.color} />
        </linearGradient>
      </defs>

      {lines.connections.map((line, i) => (
        <line
          key={`line-${i}`}
          x1={`${line.x1}%`}
          y1={`${line.y1}%`}
          x2={`${line.x2}%`}
          y2={`${line.y2}%`}
          stroke="url(#setLineGrad)"
          strokeWidth="0.5"
          style={{
            animation: `constellation-pulse 4s ease-in-out infinite`,
            animationDelay: `${line.delay}s`,
          }}
        />
      ))}

      {lines.points.map((point, i) => (
        <circle
          key={`point-${i}`}
          cx={`${point.x}%`}
          cy={`${point.y}%`}
          r="1.5"
          fill={colors.gold.dim}
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.4}s`,
          }}
        />
      ))}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════
// SET LIST ITEM
// ═══════════════════════════════════════════════════════════════

interface SetListItemProps {
  set: SetSummary;
  isSelected: boolean;
  onClick: () => void;
}

function SetListItem({
  set,
  isSelected,
  onClick,
}: SetListItemProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  // Extract year from release date
  const year = set.release_date ? set.release_date.substring(0, 4) : null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative px-4 py-3 cursor-pointer transition-all duration-300"
      style={{
        background: isSelected
          ? `linear-gradient(90deg, ${colors.gold.standard}15 0%, transparent 100%)`
          : isHovered
            ? colors.void.light
            : "transparent",
        borderBottom: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Selection accent */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 transition-all duration-300"
        style={{
          background: isSelected ? colors.gold.standard : "transparent",
          boxShadow: isSelected ? `0 0 10px ${colors.gold.glow}` : "none",
        }}
      />

      <div className="flex items-center gap-3">
        {/* Set icon using Keyrune font if available */}
        <div
          className="w-8 h-8 rounded flex items-center justify-center text-sm"
          style={{
            background: `${colors.gold.standard}15`,
            border: `1px solid ${colors.gold.standard}30`,
          }}
        >
          <i
            className={`ss ss-${set.code.toLowerCase()} ss-fw`}
            style={{
              color: isSelected ? colors.gold.bright : colors.gold.dim,
              fontSize: 16,
            }}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div
            className="font-display text-sm tracking-wide truncate transition-colors duration-300"
            style={{
              color: isSelected
                ? colors.gold.bright
                : isHovered
                  ? colors.text.bright
                  : colors.text.standard,
            }}
          >
            {set.name}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span
              className="font-mono text-xs px-1.5 py-0.5 rounded"
              style={{
                background: `${colors.mana.blue.color}20`,
                color: colors.mana.blue.color,
              }}
            >
              {set.code.toUpperCase()}
            </span>
            {year && (
              <span className="text-xs" style={{ color: colors.text.muted }}>
                {year}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SEARCH BAR
// ═══════════════════════════════════════════════════════════════

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function SearchBar({
  value,
  onChange,
  placeholder = "Search...",
}: SearchBarProps): ReactNode {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="relative">
      {/* Glow effect */}
      <div
        className="absolute -inset-1 rounded-lg transition-opacity duration-300"
        style={{
          background: `linear-gradient(135deg, ${colors.gold.dim}30 0%, ${colors.mana.blue.color}20 100%)`,
          opacity: isFocused ? 1 : 0,
          filter: "blur(8px)",
        }}
      />

      <div
        className="relative flex items-center transition-all duration-300"
        style={{
          background: colors.void.deep,
          border: `1px solid ${isFocused ? colors.gold.dim : colors.border.standard}`,
          borderRadius: 8,
        }}
      >
        <div
          className="pl-3 pr-2 transition-colors duration-300"
          style={{ color: isFocused ? colors.gold.dim : colors.text.muted }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>

        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className="flex-1 h-9 bg-transparent text-sm font-body outline-none"
          style={{ color: colors.text.standard }}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// STAT BADGE
// ═══════════════════════════════════════════════════════════════

interface StatBadgeProps {
  value: string | number;
  label: string;
  accentColor?: string;
}

function StatBadge({
  value,
  label,
  accentColor = colors.gold.standard,
}: StatBadgeProps): ReactNode {
  return (
    <div className="flex flex-col items-center">
      <span className="font-display text-2xl" style={{ color: accentColor }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </span>
      <span
        className="text-xs uppercase tracking-wider"
        style={{ color: colors.text.muted }}
      >
        {label}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CARD GRID ITEM
// ═══════════════════════════════════════════════════════════════

function getRarityStyle(rarity: string | null): {
  letter: string;
  color: string;
  glow: string;
} {
  const r = (rarity ?? "common").toLowerCase();
  switch (r) {
    case "mythic":
      return {
        letter: "M",
        color: colors.rarity.mythic.color,
        glow: colors.rarity.mythic.glow,
      };
    case "rare":
      return {
        letter: "R",
        color: colors.rarity.rare.color,
        glow: colors.rarity.rare.glow,
      };
    case "uncommon":
      return {
        letter: "U",
        color: colors.rarity.uncommon.color,
        glow: colors.rarity.uncommon.glow,
      };
    default:
      return {
        letter: "C",
        color: colors.rarity.common.color,
        glow: colors.rarity.common.glow,
      };
  }
}

// Get price color based on value tier
// getPriceColor imported from ../utils/cardUtils

interface SetCardGridItemProps {
  card: CardSummary;
  onClick: () => void;
}

function SetCardGridItem({ card, onClick }: SetCardGridItemProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const { letter, color, glow } = getRarityStyle(card.rarity ?? null);
  const price = card.price_usd ?? null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative group cursor-pointer transition-all duration-300"
      style={{
        transform: isHovered ? "translateY(-4px) scale(1.02)" : "none",
      }}
    >
      {/* Card image */}
      <div
        className="relative rounded-lg overflow-hidden"
        style={{
          aspectRatio: "488 / 680",
          background: colors.void.medium,
          boxShadow: isHovered
            ? `0 12px 40px rgba(0,0,0,0.5), 0 0 20px ${glow}`
            : "0 4px 20px rgba(0,0,0,0.3)",
        }}
      >
        {card.image || card.image_small ? (
          <img
            src={card.image || card.image_small || ""}
            alt={card.name}
            loading="lazy"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <i
              className="ms ms-planeswalker text-4xl"
              style={{ color: colors.text.muted, opacity: 0.3 }}
            />
          </div>
        )}

        {/* Hover overlay */}
        <div
          className="absolute inset-0 transition-opacity duration-300"
          style={{
            background: `linear-gradient(180deg, transparent 50%, ${colors.void.deepest}ee 100%)`,
            opacity: isHovered ? 1 : 0,
          }}
        />

        {/* Rarity badge */}
        <div
          className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300"
          style={{
            background: `${color}30`,
            color,
            border: `1px solid ${color}50`,
            boxShadow: isHovered ? `0 0 10px ${glow}` : "none",
          }}
        >
          {letter}
        </div>

        {/* Price badge */}
        {price !== null && price > 0 && (
          <div
            className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-xs font-mono font-bold"
            style={{
              background: `${colors.void.deepest}dd`,
              color: getPriceColor(price),
              border: `1px solid ${getPriceColor(price)}40`,
            }}
          >
            $
            {price < 1
              ? price.toFixed(2)
              : price < 10
                ? price.toFixed(1)
                : Math.round(price)}
          </div>
        )}
      </div>

      {/* Card info */}
      <div className="mt-2 px-1">
        <p
          className="text-xs font-display truncate transition-colors duration-300"
          style={{
            color: isHovered ? colors.text.bright : colors.text.standard,
          }}
        >
          {card.name}
        </p>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs" style={{ color: colors.text.muted }}>
            #{card.collector_number}
          </span>
          {card.mana_cost && <ManaCost cost={card.mana_cost} size="small" />}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// COMPACT ANALYTICS (inline in header)
// ═══════════════════════════════════════════════════════════════

interface CompactAnalyticsProps {
  analysis: SetAnalysisResponse | null;
  isLoading: boolean;
}

function CompactAnalytics({
  analysis,
  isLoading,
}: CompactAnalyticsProps): ReactNode {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <div
          className="w-4 h-4 rounded-full border-2 border-t-transparent"
          style={{
            borderColor: colors.gold.dim,
            borderTopColor: "transparent",
            animation: "spin 1s linear infinite",
          }}
        />
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Loading analytics...
        </span>
      </div>
    );
  }

  if (!analysis) {
    return null;
  }

  const { value_summary, rarity_distribution, type_distribution } = analysis;

  return (
    <div className="space-y-4">
      {/* Value + Rarity row */}
      <div className="flex items-center gap-6 flex-wrap">
        {/* Value stats */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-xs" style={{ color: colors.text.muted }}>
              Value:
            </span>
            <span
              className="font-display text-sm"
              style={{ color: colors.gold.bright }}
            >
              ${value_summary.total_value.toFixed(0)}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs" style={{ color: colors.text.muted }}>
              Avg:
            </span>
            <span
              className="font-display text-sm"
              style={{ color: colors.text.standard }}
            >
              ${value_summary.average_value.toFixed(2)}
            </span>
          </div>
          {value_summary.chase_card_count > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-xs" style={{ color: colors.text.muted }}>
                Chase:
              </span>
              <span
                className="font-display text-sm"
                style={{ color: colors.rarity.mythic.color }}
              >
                {value_summary.chase_card_count}
              </span>
            </div>
          )}
        </div>

        {/* Divider */}
        <div
          className="w-px h-4"
          style={{ background: colors.border.standard }}
        />

        {/* Rarity distribution - compact badges */}
        <div className="flex items-center gap-2">
          <span
            className="px-2 py-0.5 rounded text-xs font-display"
            style={{
              background: `${colors.rarity.mythic.color}20`,
              color: colors.rarity.mythic.color,
            }}
          >
            M {rarity_distribution.mythic}
          </span>
          <span
            className="px-2 py-0.5 rounded text-xs font-display"
            style={{
              background: `${colors.rarity.rare.color}20`,
              color: colors.rarity.rare.color,
            }}
          >
            R {rarity_distribution.rare}
          </span>
          <span
            className="px-2 py-0.5 rounded text-xs font-display"
            style={{
              background: `${colors.rarity.uncommon.color}20`,
              color: colors.rarity.uncommon.color,
            }}
          >
            U {rarity_distribution.uncommon}
          </span>
          <span
            className="px-2 py-0.5 rounded text-xs font-display"
            style={{
              background: `${colors.rarity.common.color}20`,
              color: colors.rarity.common.color,
            }}
          >
            C {rarity_distribution.common}
          </span>
        </div>
      </div>

      {/* Type distribution - compact inline */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Types:
        </span>
        <div className="flex items-center gap-2">
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.mana.green.color }}
          >
            <i className="ms ms-creature" style={{ fontSize: 10 }} />
            {type_distribution.creatures}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.mana.blue.color }}
          >
            <i className="ms ms-instant" style={{ fontSize: 10 }} />
            {type_distribution.instants}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.mana.red.color }}
          >
            <i className="ms ms-sorcery" style={{ fontSize: 10 }} />
            {type_distribution.sorceries}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.mana.white.color }}
          >
            <i className="ms ms-enchantment" style={{ fontSize: 10 }} />
            {type_distribution.enchantments}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.mana.colorless.color }}
          >
            <i className="ms ms-artifact" style={{ fontSize: 10 }} />
            {type_distribution.artifacts}
          </span>
          <span
            className="flex items-center gap-1 text-xs"
            style={{ color: colors.gold.dim }}
          >
            <i className="ms ms-land" style={{ fontSize: 10 }} />
            {type_distribution.lands}
          </span>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

const PAGE_SIZE = 50;

interface SetsScreenProps {
  onOpenGallery?: (cardName: string) => void;
}

export function SetsScreen({ onOpenGallery }: SetsScreenProps = {}): ReactNode {
  const [sets, setSets] = useState<SetSummary[]>([]);
  const [filteredSets, setFilteredSets] = useState<SetSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSetCode, setSelectedSetCode] = useState<string | null>(null);
  const [selectedSet, setSelectedSet] = useState<SetDetail | null>(null);
  const [setCards, setSetCards] = useState<CardSummary[]>([]);
  const [analysis, setAnalysis] = useState<SetAnalysisResponse | null>(null);
  const [isLoadingSets, setIsLoadingSets] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isLoadingCards, setIsLoadingCards] = useState(false);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [cardsPage, setCardsPage] = useState(1);
  const [totalCards, setTotalCards] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);

  const cardsContainerRef = useRef<HTMLDivElement>(null);

  // Load all sets on mount
  useEffect(() => {
    async function loadSets(): Promise<void> {
      setIsLoadingSets(true);
      setError(null);
      try {
        const result = await window.electronAPI.sets.list();
        if (!result?.sets) {
          throw new Error(
            "Invalid API response - please restart the app to reload the API server",
          );
        }
        // Sort by release date (newest first)
        const sorted = [...result.sets].sort((a, b) => {
          const dateA = a.release_date ?? "0000-00-00";
          const dateB = b.release_date ?? "0000-00-00";
          return dateB.localeCompare(dateA);
        });
        setSets(sorted);
        setFilteredSets(sorted);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoadingSets(false);
      }
    }
    loadSets();
  }, []);

  // Filter sets when search query changes
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredSets(sets);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = sets.filter(
      (s) =>
        s.name.toLowerCase().includes(query) ||
        s.code.toLowerCase().includes(query),
    );
    setFilteredSets(filtered);
  }, [searchQuery, sets]);

  // Load set details when selection changes
  const loadSetDetails = useCallback(async (code: string) => {
    setIsLoadingDetail(true);
    setIsLoadingCards(true);
    setIsLoadingAnalysis(true);
    setSetCards([]);
    setCardsPage(1);
    setAnalysis(null);

    try {
      // Load set details, cards, and analysis in parallel
      const [detailResult, cardsResult, analysisResult] = await Promise.all([
        window.electronAPI.sets.get(code),
        window.electronAPI.sets.getCards(code, 1, PAGE_SIZE),
        window.electronAPI.sets.getAnalysis(code).catch(() => null),
      ]);

      setSelectedSet(detailResult);
      setSetCards(cardsResult.cards);
      setTotalCards(cardsResult.total_count);
      setAnalysis(analysisResult);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoadingDetail(false);
      setIsLoadingCards(false);
      setIsLoadingAnalysis(false);
    }
  }, []);

  const handleSelectSet = (code: string): void => {
    setSelectedSetCode(code);
    loadSetDetails(code);
  };

  const handleLoadMoreCards = async (): Promise<void> => {
    if (!selectedSetCode || isLoadingCards) return;

    const nextPage = cardsPage + 1;
    setIsLoadingCards(true);

    try {
      const result = await window.electronAPI.sets.getCards(
        selectedSetCode,
        nextPage,
        PAGE_SIZE,
      );
      setSetCards((prev) => [...prev, ...result.cards]);
      setCardsPage(nextPage);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoadingCards(false);
    }
  };

  const handleCardClick = (card: CardSummary): void => {
    setSelectedCardName(card.name);
  };

  const handleCloseModal = (): void => {
    setSelectedCardName(null);
  };

  const hasMoreCards = setCards.length < totalCards;

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 100% 80% at 0% 0%, ${colors.mana.blue.color}08 0%, transparent 50%),
      radial-gradient(ellipse 80% 60% at 100% 100%, ${colors.gold.glow}10 0%, transparent 50%),
      ${colors.void.deepest}
    `,
  };

  return (
    <div className="h-full flex flex-col relative" style={containerStyle}>
      {/* Background effect */}
      <ConstellationBackground />

      {/* Header */}
      <div
        className="relative z-10 p-6 border-b"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <i
                className="ss ss-dmu ss-2x"
                style={{ color: colors.mana.blue.color, opacity: 0.8 }}
              />
              <h1
                className="font-display text-2xl tracking-widest"
                style={{
                  background: `linear-gradient(135deg, ${colors.mana.blue.color} 0%, ${colors.gold.standard} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                ARCHIVES
              </h1>
            </div>
            <p className="text-sm font-body" style={{ color: colors.text.dim }}>
              Explore the history of Magic sets
            </p>
          </div>

          <div className="w-64">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search sets..."
            />
          </div>
        </div>
      </div>

      {error && (
        <div
          className="relative z-10 mx-6 mt-4 p-3 rounded-lg text-sm"
          style={{
            background: `${colors.status.error}15`,
            border: `1px solid ${colors.status.error}30`,
            color: colors.status.error,
          }}
        >
          {error}
        </div>
      )}

      {/* Main content - split view */}
      <div className="relative z-10 flex-1 flex min-h-0">
        {/* Left panel - Set list */}
        <div
          className="w-80 border-r flex flex-col"
          style={{ borderColor: colors.border.subtle }}
        >
          {/* List header */}
          <div
            className="px-4 py-3 flex items-center justify-between"
            style={{
              background: `${colors.void.medium}80`,
              borderBottom: `1px solid ${colors.border.subtle}`,
            }}
          >
            <span
              className="text-xs font-display uppercase tracking-wider"
              style={{ color: colors.text.muted }}
            >
              Sets
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: `${colors.mana.blue.color}20`,
                color: colors.mana.blue.color,
              }}
            >
              {filteredSets.length.toLocaleString()}
            </span>
          </div>

          {/* Set list */}
          <div className="flex-1 overflow-auto">
            {isLoadingSets ? (
              <div className="p-8 text-center">
                <div
                  className="w-6 h-6 mx-auto mb-3 rounded-full border-2 border-t-transparent"
                  style={{
                    borderColor: colors.gold.dim,
                    borderTopColor: "transparent",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <span style={{ color: colors.text.muted }}>
                  Loading sets...
                </span>
              </div>
            ) : filteredSets.length === 0 ? (
              <div className="p-8 text-center">
                <i
                  className="ss ss-default ss-3x mb-3"
                  style={{ color: colors.text.muted, opacity: 0.3 }}
                />
                <p style={{ color: colors.text.muted }}>No sets found</p>
              </div>
            ) : (
              filteredSets.map((set) => (
                <SetListItem
                  key={set.code}
                  set={set}
                  isSelected={selectedSetCode === set.code}
                  onClick={() => handleSelectSet(set.code)}
                />
              ))
            )}
          </div>
        </div>

        {/* Right panel - Set details */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedSetCode ? (
            <div className="flex-1 flex flex-col items-center justify-center">
              <i
                className="ss ss-default ss-6x mb-4"
                style={{ color: colors.gold.dim, opacity: 0.2 }}
              />
              <p
                className="font-display text-lg tracking-wide"
                style={{ color: colors.text.muted }}
              >
                Select a set to explore its cards
              </p>
            </div>
          ) : isLoadingDetail ? (
            <div className="flex-1 flex items-center justify-center">
              <div
                className="w-8 h-8 rounded-full border-2 border-t-transparent"
                style={{
                  borderColor: colors.gold.dim,
                  borderTopColor: "transparent",
                  animation: "spin 1s linear infinite",
                }}
              />
            </div>
          ) : selectedSet ? (
            <>
              {/* Set header */}
              <div
                className="p-6 border-b"
                style={{ borderColor: colors.border.subtle }}
              >
                <div className="flex items-start gap-4 mb-4">
                  <div
                    className="w-16 h-16 rounded-lg flex items-center justify-center"
                    style={{
                      background: `${colors.gold.standard}15`,
                      border: `1px solid ${colors.gold.standard}30`,
                    }}
                  >
                    <i
                      className={`ss ss-${selectedSet.code.toLowerCase()} ss-3x`}
                      style={{ color: colors.gold.bright }}
                    />
                  </div>
                  <div className="flex-1">
                    <h2
                      className="font-display text-2xl tracking-wide mb-1"
                      style={{ color: colors.text.bright }}
                    >
                      {selectedSet.name}
                    </h2>
                    <div className="flex items-center gap-4 text-sm">
                      <span
                        className="font-mono px-2 py-0.5 rounded"
                        style={{
                          background: `${colors.mana.blue.color}20`,
                          color: colors.mana.blue.color,
                        }}
                      >
                        {selectedSet.code.toUpperCase()}
                      </span>
                      <span style={{ color: colors.text.dim }}>
                        {selectedSet.release_date ?? "Unknown date"}
                      </span>
                      {selectedSet.type && (
                        <span
                          className="capitalize"
                          style={{ color: colors.gold.standard }}
                        >
                          {selectedSet.type}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Size stats - moved to right side */}
                  <div className="flex gap-6">
                    <StatBadge
                      value={selectedSet.base_set_size ?? 0}
                      label="Base Size"
                      accentColor={colors.gold.standard}
                    />
                    <StatBadge
                      value={selectedSet.total_set_size ?? 0}
                      label="Total Size"
                      accentColor={colors.mana.blue.color}
                    />
                    {selectedSet.block && (
                      <StatBadge
                        value={selectedSet.block}
                        label="Block"
                        accentColor={colors.mana.green.color}
                      />
                    )}
                  </div>
                </div>

                {/* Compact analytics inline */}
                <CompactAnalytics
                  analysis={analysis}
                  isLoading={isLoadingAnalysis}
                />
              </div>

              {/* Cards grid */}
              <div ref={cardsContainerRef} className="flex-1 overflow-auto p-6">
                {/* Section header */}
                <div className="flex items-center gap-3 mb-4">
                  <span
                    className="w-8 h-px"
                    style={{ background: colors.border.standard }}
                  />
                  <span
                    className="text-xs font-display uppercase tracking-widest"
                    style={{ color: colors.text.muted }}
                  >
                    Cards ({setCards.length} of {totalCards})
                  </span>
                  <span
                    className="flex-1 h-px"
                    style={{ background: colors.border.standard }}
                  />
                </div>

                {isLoadingCards && setCards.length === 0 ? (
                  <div className="flex items-center justify-center py-12">
                    <div
                      className="w-8 h-8 rounded-full border-2 border-t-transparent"
                      style={{
                        borderColor: colors.gold.dim,
                        borderTopColor: "transparent",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                  </div>
                ) : setCards.length === 0 ? (
                  <div className="text-center py-12">
                    <p style={{ color: colors.text.muted }}>No cards found</p>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                      {setCards.map((card) => (
                        <SetCardGridItem
                          key={card.uuid ?? card.name}
                          card={card}
                          onClick={() => handleCardClick(card)}
                        />
                      ))}
                    </div>

                    {hasMoreCards && (
                      <div className="mt-6 text-center">
                        <button
                          onClick={handleLoadMoreCards}
                          disabled={isLoadingCards}
                          className="px-6 py-2 rounded-lg font-display text-sm tracking-wide transition-all duration-300"
                          style={{
                            background: colors.void.lighter,
                            border: `1px solid ${colors.border.standard}`,
                            color: isLoadingCards
                              ? colors.text.muted
                              : colors.gold.standard,
                          }}
                          onMouseEnter={(e) => {
                            if (!isLoadingCards) {
                              e.currentTarget.style.borderColor =
                                colors.gold.standard;
                              e.currentTarget.style.boxShadow = `0 0 15px ${colors.gold.glow}`;
                            }
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor =
                              colors.border.standard;
                            e.currentTarget.style.boxShadow = "none";
                          }}
                        >
                          {isLoadingCards
                            ? "Loading..."
                            : `Load More (${(totalCards - setCards.length).toLocaleString()} remaining)`}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          ) : null}
        </div>
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

export default SetsScreen;
