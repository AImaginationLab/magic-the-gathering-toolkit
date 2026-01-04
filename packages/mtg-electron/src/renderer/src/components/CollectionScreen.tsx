/**
 * CollectionScreen - The Collector's Vault
 *
 * Browse and manage your MTG collection with Arcane-style aesthetics.
 * Features collapsible tree view with prices grouped by card name.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from "react";

import { colors } from "../theme";
import {
  formatPrice,
  getPriceColor,
  getNameColorForRarity,
} from "../utils/cardUtils";
import { CollectionImportModal } from "./CollectionImportModal";
import { CollectionEditModal } from "./CollectionEditModal";
import { CardDetailModal } from "./CardDetailModal";
import { BulkActionsBar } from "./BulkActionsBar";
import { DeckSelectorDropdown } from "./DeckSelectorDropdown";
import type { BulkCardSelection } from "./DeckSelectorDropdown";
import {
  CollectionFilterPanel,
  createEmptyFilters,
  hasActiveFilters,
} from "./CollectionFilterPanel";
import type { CollectionFilters } from "./CollectionFilterPanel";

import type { ReactNode, CSSProperties } from "react";
import type { components } from "../../../shared/types/api-generated";

type PriceCollectionResponse = components["schemas"]["PriceCollectionResponse"];
type PricedCard = components["schemas"]["PricedCard"];

// Sort options for the collection
type SortField =
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
type SortOrder = "asc" | "desc";

const SORT_OPTIONS: Array<{
  value: SortField;
  label: string;
  defaultOrder: SortOrder;
  group?: string;
}> = [
  // Basic sorts
  { value: "name", label: "Name", defaultOrder: "asc", group: "Basic" },
  {
    value: "dateAdded",
    label: "Date Added",
    defaultOrder: "desc",
    group: "Basic",
  },
  {
    value: "quantity",
    label: "Quantity",
    defaultOrder: "desc",
    group: "Basic",
  },
  { value: "setCode", label: "Set", defaultOrder: "asc", group: "Basic" },
  // Card metadata
  { value: "price", label: "Price", defaultOrder: "desc", group: "Card" },
  { value: "rarity", label: "Rarity", defaultOrder: "desc", group: "Card" },
  { value: "cmc", label: "Mana Value", defaultOrder: "desc", group: "Card" },
  { value: "color", label: "Color", defaultOrder: "asc", group: "Card" },
  { value: "type", label: "Type", defaultOrder: "asc", group: "Card" },
  // Gameplay / Limited stats
  {
    value: "winRate",
    label: "Win Rate",
    defaultOrder: "desc",
    group: "Gameplay",
  },
  {
    value: "tier",
    label: "Tier Grade",
    defaultOrder: "desc",
    group: "Gameplay",
  },
  {
    value: "draftPick",
    label: "Draft Pick",
    defaultOrder: "asc",
    group: "Gameplay",
  },
];

// Types matching the API response (enriched with card data from worker)
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
  // Gameplay stats from 17Lands
  winRate: number | null;
  tier: string | null;
  draftPick: number | null;
}

// Grouped card for collapsible tree display
interface GroupedCard {
  cardName: string;
  totalQuantity: number;
  totalFoilQuantity: number;
  totalPrice: number;
  maxCardPrice: number; // Highest single-card price (for "Top Cards" ranking)
  rarity: string | null;
  printings: CollectionCard[];
  hasMultiplePrintings: boolean;
  // Metadata from first printing (for display)
  cmc: number;
  typeLine: string | null;
  colors: string[];
  winRate: number | null;
  tier: string | null;
  draftPick: number | null;
}

// Price lookup helper - creates composite key for specific printings
function getPriceKey(
  cardName: string,
  setCode: string | null,
  collectorNumber: string | null,
): string {
  if (setCode && collectorNumber) {
    return `${cardName}|${setCode.toUpperCase()}|${collectorNumber}`;
  }
  return cardName;
}

// Build price map from priced cards
function buildPriceMap(
  pricedCards: PricedCard[] | undefined,
): Map<string, number> {
  const map = new Map<string, number>();
  if (!pricedCards) return map;

  for (const card of pricedCards) {
    if (card.card_name && card.price_usd != null) {
      const key = getPriceKey(
        card.card_name,
        card.set_code ?? null,
        card.collector_number ?? null,
      );
      map.set(key, card.price_usd);
    }
  }
  return map;
}

// Group collection cards by name
function groupCollectionCards(
  cards: CollectionCard[],
  priceMap: Map<string, number>,
  sortBy: SortField,
  sortOrder: SortOrder,
): GroupedCard[] {
  const groups = new Map<string, GroupedCard>();

  for (const card of cards) {
    const existing = groups.get(card.cardName);
    const priceKey = getPriceKey(
      card.cardName,
      card.setCode,
      card.collectorNumber,
    );
    const cardPrice = priceMap.get(priceKey) ?? 0;
    const totalCards = card.quantity + card.foilQuantity;

    if (existing) {
      existing.totalQuantity += card.quantity;
      existing.totalFoilQuantity += card.foilQuantity;
      existing.totalPrice += cardPrice * totalCards;
      existing.maxCardPrice = Math.max(existing.maxCardPrice, cardPrice);
      existing.printings.push(card);
      existing.hasMultiplePrintings = true;
    } else {
      groups.set(card.cardName, {
        cardName: card.cardName,
        totalQuantity: card.quantity,
        totalFoilQuantity: card.foilQuantity,
        totalPrice: cardPrice * totalCards,
        maxCardPrice: cardPrice,
        rarity: card.rarity ?? null,
        printings: [card],
        hasMultiplePrintings: false,
        // Metadata from first printing
        cmc: card.cmc,
        typeLine: card.typeLine,
        colors: card.colors,
        winRate: card.winRate,
        tier: card.tier,
        draftPick: card.draftPick,
      });
    }
  }

  // Sort grouped cards client-side based on sort field
  // All data is fetched at once, so we do full sorting here
  const grouped = Array.from(groups.values());
  const direction = sortOrder === "asc" ? 1 : -1;

  // Rarity order for sorting (higher = better)
  const rarityOrder: Record<string, number> = {
    mythic: 4,
    rare: 3,
    uncommon: 2,
    common: 1,
  };

  // Tier order for sorting (higher = better)
  const tierOrder: Record<string, number> = {
    S: 6,
    A: 5,
    B: 4,
    C: 3,
    D: 2,
    F: 1,
  };

  // Color order (WUBRG, then multicolor, then colorless)
  const colorOrder = (colors: string[]): number => {
    if (colors.length === 0) return 7; // Colorless last
    if (colors.length > 1) return 6; // Multicolor
    const order: Record<string, number> = { W: 1, U: 2, B: 3, R: 4, G: 5 };
    return order[colors[0]] ?? 6;
  };

  grouped.sort((a, b) => {
    let cmp = 0;

    switch (sortBy) {
      case "name":
        cmp = a.cardName.localeCompare(b.cardName);
        break;
      case "quantity":
        cmp =
          a.totalQuantity +
          a.totalFoilQuantity -
          (b.totalQuantity + b.totalFoilQuantity);
        break;
      case "dateAdded":
        cmp = (a.printings[0]?.addedAt ?? "").localeCompare(
          b.printings[0]?.addedAt ?? "",
        );
        break;
      case "setCode":
        cmp = (a.printings[0]?.setCode ?? "").localeCompare(
          b.printings[0]?.setCode ?? "",
        );
        break;
      case "price":
        cmp = a.totalPrice - b.totalPrice;
        break;
      case "rarity":
        cmp =
          (rarityOrder[a.rarity?.toLowerCase() ?? ""] ?? 0) -
          (rarityOrder[b.rarity?.toLowerCase() ?? ""] ?? 0);
        break;
      case "cmc":
        cmp = a.cmc - b.cmc;
        break;
      case "type":
        cmp = (a.typeLine ?? "").localeCompare(b.typeLine ?? "");
        break;
      case "color":
        cmp = colorOrder(a.colors) - colorOrder(b.colors);
        break;
      case "winRate":
        // Nulls always last, regardless of sort direction
        if (a.winRate == null && b.winRate == null) cmp = 0;
        else if (a.winRate == null)
          return 1; // a goes after b (null last)
        else if (b.winRate == null)
          return -1; // b goes after a (null last)
        else cmp = a.winRate - b.winRate;
        break;
      case "tier":
        // Nulls always last, regardless of sort direction
        if (!a.tier && !b.tier) cmp = 0;
        else if (!a.tier) return 1;
        else if (!b.tier) return -1;
        else cmp = (tierOrder[a.tier] ?? 0) - (tierOrder[b.tier] ?? 0);
        break;
      case "draftPick":
        // Nulls always last, regardless of sort direction
        if (a.draftPick == null && b.draftPick == null) cmp = 0;
        else if (a.draftPick == null) return 1;
        else if (b.draftPick == null) return -1;
        else cmp = a.draftPick - b.draftPick;
        break;
      default:
        cmp = a.cardName.localeCompare(b.cardName);
    }

    // Secondary sort by name for stability
    if (cmp === 0) {
      cmp = a.cardName.localeCompare(b.cardName);
    }

    return cmp * direction;
  });

  // Sort printings within each group using the same sort criteria
  for (const group of grouped) {
    group.printings.sort((a, b) => {
      let cmp = 0;

      switch (sortBy) {
        case "quantity":
          cmp = a.quantity + a.foilQuantity - (b.quantity + b.foilQuantity);
          break;
        case "dateAdded":
          cmp = (a.addedAt ?? "").localeCompare(b.addedAt ?? "");
          break;
        case "setCode":
          cmp = (a.setCode ?? "").localeCompare(b.setCode ?? "");
          break;
        case "price":
          cmp = (a.priceUsd ?? 0) - (b.priceUsd ?? 0);
          break;
        default:
          // For other fields, sort by quantity desc then set code
          cmp = b.quantity + b.foilQuantity - (a.quantity + a.foilQuantity);
          if (cmp === 0) {
            cmp = (a.setCode ?? "").localeCompare(b.setCode ?? "");
          }
          return cmp; // Don't apply direction for default
      }

      // Secondary sort by set code for stability
      if (cmp === 0) {
        cmp = (a.setCode ?? "").localeCompare(b.setCode ?? "");
      }

      return cmp * direction;
    });
  }

  return grouped;
}

// Helper to get card name color based on rarity
// Utility functions moved to ../utils/cardUtils.ts

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
  topKeywords?: Array<{ keyword: string; count: number }>;
  topArtists?: Array<{ artist: string; count: number }>;
  legendaries?: { creatures: number; other: number; total: number };
  error?: string;
}

// ═══════════════════════════════════════════════════════════════
// AMBIENT EFFECTS
// ═══════════════════════════════════════════════════════════════

function ConstellationBackground(): ReactNode {
  const lines = useMemo(() => {
    const points = Array.from({ length: 18 }, () => ({
      x: 5 + Math.random() * 90,
      y: 5 + Math.random() * 90,
      brightness: 0.3 + Math.random() * 0.7,
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
        if (dist < 28 && connections.length < 22) {
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
      style={{ opacity: 0.06 }}
    >
      <defs>
        <linearGradient id="vaultLineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={colors.gold.dim} />
          <stop offset="50%" stopColor={colors.mana.green.color} />
          <stop offset="100%" stopColor={colors.mana.blue.color} />
        </linearGradient>
        <filter id="vaultGlow">
          <feGaussianBlur stdDeviation="1" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {lines.connections.map((line, i) => (
        <line
          key={`line-${i}`}
          x1={`${line.x1}%`}
          y1={`${line.y1}%`}
          x2={`${line.x2}%`}
          y2={`${line.y2}%`}
          stroke="url(#vaultLineGrad)"
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
          r={1 + point.brightness * 1.5}
          fill={
            i % 3 === 0
              ? colors.gold.dim
              : i % 3 === 1
                ? colors.mana.green.color
                : colors.mana.blue.color
          }
          filter="url(#vaultGlow)"
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.2}s`,
            opacity: point.brightness,
          }}
        />
      ))}
    </svg>
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
    <div className="relative flex-1">
      {/* Prismatic glow on focus */}
      <div
        className="absolute -inset-1 rounded-xl transition-all duration-500"
        style={{
          background: isFocused
            ? `linear-gradient(135deg, ${colors.gold.glow}40 0%, ${colors.mana.green.glow}30 50%, ${colors.mana.blue.glow}40 100%)`
            : "transparent",
          filter: "blur(10px)",
          opacity: isFocused ? 1 : 0,
        }}
      />

      <div
        className="relative flex items-center transition-all duration-300"
        style={{
          background: `linear-gradient(135deg, ${colors.void.deep} 0%, ${colors.void.medium} 100%)`,
          border: `1px solid ${isFocused ? colors.gold.dim : colors.border.standard}`,
          borderRadius: 10,
          boxShadow: isFocused
            ? `0 0 20px ${colors.gold.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`
            : `inset 0 1px 0 rgba(255,255,255,0.03)`,
        }}
      >
        <div
          className="pl-4 pr-2 transition-colors duration-300"
          style={{ color: isFocused ? colors.gold.dim : colors.text.muted }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
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
          className="flex-1 h-11 bg-transparent text-sm font-body outline-none pr-4"
          style={{ color: colors.text.standard }}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// STAT ORB
// ═══════════════════════════════════════════════════════════════

interface StatOrbProps {
  label: string;
  value: string | number;
  icon: string;
  color: string;
  glow?: string;
}

function StatOrb({ label, value, icon, color, glow }: StatOrbProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="relative flex flex-col items-center cursor-default transition-transform duration-200"
      style={{ transform: isHovered ? "translateY(-2px)" : "none" }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className="relative w-12 h-12 rounded-full flex flex-col items-center justify-center transition-all duration-200"
        style={{
          background: `radial-gradient(circle at 30% 30%, ${colors.void.lighter} 0%, ${colors.void.medium} 100%)`,
          border: `1px solid ${isHovered ? color : colors.border.subtle}`,
          boxShadow: isHovered ? `0 0 12px ${glow || color}30` : "none",
        }}
      >
        <i
          className={`ms ms-${icon}`}
          style={{ fontSize: 11, color: isHovered ? color : colors.text.muted }}
        />
        <span
          className="font-display text-sm leading-tight"
          style={{ color: isHovered ? color : colors.text.bright }}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </span>
      </div>
      <span
        className="text-[9px] mt-1 uppercase tracking-wider font-display"
        style={{ color: isHovered ? color : colors.text.muted }}
      >
        {label}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// COMPACT ANALYTICS PANEL COMPONENTS
// ═══════════════════════════════════════════════════════════════

const panelStyle = {
  background: `linear-gradient(145deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
  border: `1px solid ${colors.border.subtle}`,
};

interface PriceTiersPanelProps {
  priceData: PriceCollectionResponse | null;
  isLoading: boolean;
}

function PriceTiersPanel({
  priceData,
  isLoading,
}: PriceTiersPanelProps): ReactNode {
  const totalValue = priceData?.total_value ?? 0;

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="mb-2">
        <span
          className="text-sm font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Value
        </span>
      </div>
      {isLoading ? (
        <div className="text-xs" style={{ color: colors.text.muted }}>
          Loading...
        </div>
      ) : (
        <div className="flex items-baseline gap-2">
          <div
            className="font-display text-2xl font-bold leading-tight"
            style={{
              background: `linear-gradient(135deg, ${colors.gold.bright} 0%, ${colors.gold.standard} 100%)`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            $
            {totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <div className="text-[10px]" style={{ color: colors.text.dim }}>
            ({priceData?.cards_with_prices ?? 0} priced)
          </div>
        </div>
      )}
    </div>
  );
}

interface TopCardsPanelProps {
  groupedCards: GroupedCard[];
  isLoading: boolean;
}

function TopCardsPanel({
  groupedCards,
  isLoading,
}: TopCardsPanelProps): ReactNode {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  // Compute top 5 cards by single-card price (not total value of all copies)
  const topCards = useMemo(() => {
    return [...groupedCards]
      .sort((a, b) => b.maxCardPrice - a.maxCardPrice)
      .slice(0, 5)
      .map((g) => ({ name: g.cardName, price: g.maxCardPrice }));
  }, [groupedCards]);
  const maxPrice = topCards[0]?.price ?? 1;

  // getPriceColor imported from ../utils/cardUtils

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Top Cards
        </span>
      </div>
      {isLoading ? (
        <div className="text-xs" style={{ color: colors.text.muted }}>
          Loading...
        </div>
      ) : topCards.length > 0 ? (
        <div className="space-y-1.5">
          {topCards.map((card, idx) => {
            const pct = maxPrice > 0 ? (card.price / maxPrice) * 100 : 0;
            const priceColor = getPriceColor(card.price);
            const isHovered = hoveredIdx === idx;
            return (
              <div
                key={`${card.name}-${idx}`}
                className="relative cursor-default"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                {/* Background bar */}
                <div
                  className="absolute inset-y-0 left-0 rounded transition-all duration-150"
                  style={{
                    width: isHovered ? `${Math.max(pct, 100)}%` : `${pct}%`,
                    background: isHovered
                      ? `${priceColor}35`
                      : `${priceColor}20`,
                  }}
                />
                {/* Content */}
                <div className="relative flex items-center gap-2 py-0.5 px-1">
                  <span
                    className="w-4 text-right font-mono transition-all duration-150"
                    style={{
                      fontSize: isHovered ? 11 : 10,
                      color: isHovered ? colors.gold.standard : colors.gold.dim,
                    }}
                  >
                    {idx + 1}
                  </span>
                  <span
                    className="flex-1 truncate transition-all duration-150"
                    style={{
                      fontSize: isHovered ? 13 : 12,
                      color: isHovered
                        ? colors.text.bright
                        : colors.text.standard,
                      fontWeight: isHovered ? 500 : 400,
                    }}
                    title={card.name}
                  >
                    {card.name}
                  </span>
                  <span
                    className="font-mono font-semibold shrink-0 transition-all duration-150"
                    style={{
                      fontSize: isHovered ? 13 : 12,
                      color: priceColor,
                      textShadow: isHovered ? `0 0 8px ${priceColor}` : "none",
                    }}
                  >
                    ${card.price.toFixed(0)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs" style={{ color: colors.text.dim }}>
          No data
        </div>
      )}
    </div>
  );
}

interface TypeCompositionPanelProps {
  types: Record<string, number>;
}

function TypeCompositionPanel({ types }: TypeCompositionPanelProps): ReactNode {
  const [hoveredType, setHoveredType] = useState<string | null>(null);
  const sortedTypes = Object.entries(types)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);
  const maxCount = sortedTypes[0]?.[1] ?? 1;

  const typeConfig: Record<string, { color: string; icon: string }> = {
    Creature: { color: colors.mana.green.color, icon: "ms-creature" },
    Instant: { color: colors.mana.blue.color, icon: "ms-instant" },
    Sorcery: { color: colors.mana.red.color, icon: "ms-sorcery" },
    Enchantment: { color: colors.mana.white.color, icon: "ms-enchantment" },
    Artifact: { color: "#bab1ab", icon: "ms-artifact" },
    Land: { color: colors.gold.dim, icon: "ms-land" },
    Planeswalker: {
      color: colors.rarity.mythic.color,
      icon: "ms-planeswalker",
    },
  };

  return (
    <div className="p-3 rounded-lg overflow-hidden" style={panelStyle}>
      <div className="mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Types
        </span>
      </div>
      <div className="space-y-1.5">
        {sortedTypes.map(([typeName, count]) => {
          const config = typeConfig[typeName] || {
            color: colors.text.muted,
            icon: "ms-creature",
          };
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          const isHovered = hoveredType === typeName;
          return (
            <div
              key={typeName}
              className="flex items-center gap-2 text-xs cursor-default"
              onMouseEnter={() => setHoveredType(typeName)}
              onMouseLeave={() => setHoveredType(null)}
            >
              <i
                className={`ms ${config.icon} transition-all duration-150`}
                style={{
                  color: config.color,
                  fontSize: isHovered ? 14 : 12,
                  width: 14,
                  filter: isHovered
                    ? `drop-shadow(0 0 4px ${config.color})`
                    : "none",
                }}
              />
              <div
                className="flex-1 relative transition-all duration-150"
                style={{ height: isHovered ? 20 : 16 }}
              >
                {/* Background track */}
                <div
                  className="absolute inset-0 rounded"
                  style={{ background: colors.void.lighter }}
                />
                {/* Filled bar */}
                <div
                  className="absolute inset-y-0 left-0 rounded transition-all duration-150"
                  style={{
                    width: `${pct}%`,
                    background: `linear-gradient(90deg, ${config.color}90 0%, ${config.color} 100%)`,
                    minWidth: count > 0 ? 2 : 0,
                    boxShadow: isHovered ? `0 0 8px ${config.color}60` : "none",
                  }}
                />
                {/* Label overlay */}
                <div className="absolute inset-0 flex items-center justify-between px-2">
                  <span
                    className="transition-all duration-150"
                    style={{
                      color: isHovered
                        ? colors.text.bright
                        : colors.text.standard,
                      fontSize: isHovered ? 13 : 12,
                      fontWeight: isHovered ? 500 : 400,
                    }}
                  >
                    {typeName}
                  </span>
                  <span
                    className="font-mono transition-all duration-150"
                    style={{
                      color: isHovered
                        ? colors.text.bright
                        : colors.text.standard,
                      fontSize: isHovered ? 13 : 12,
                      fontWeight: isHovered ? 600 : 400,
                    }}
                  >
                    {count}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface RarityCompositionPanelProps {
  rarities: Record<string, number>;
}

function RarityCompositionPanel({
  rarities,
}: RarityCompositionPanelProps): ReactNode {
  const [hoveredRarity, setHoveredRarity] = useState<string | null>(null);
  const rarityConfig = [
    { key: "Mythic", color: colors.rarity.mythic.color, icon: "★" },
    { key: "Rare", color: colors.rarity.rare.color, icon: "◆" },
    { key: "Uncommon", color: colors.rarity.uncommon.color, icon: "●" },
    { key: "Common", color: colors.rarity.common.color, icon: "○" },
  ];
  const maxCount = Math.max(...Object.values(rarities), 1);

  return (
    <div className="p-3 rounded-lg overflow-hidden" style={panelStyle}>
      <div className="mb-3">
        <span
          className="text-sm font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Rarity
        </span>
      </div>
      <div className="space-y-1.5">
        {rarityConfig.map(({ key, color, icon }) => {
          const count = rarities[key] || 0;
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          const isHovered = hoveredRarity === key;
          return (
            <div
              key={key}
              className="flex items-center gap-2 text-xs cursor-default"
              onMouseEnter={() => setHoveredRarity(key)}
              onMouseLeave={() => setHoveredRarity(null)}
            >
              <span
                className="transition-all duration-150"
                style={{
                  color,
                  fontSize: isHovered ? 14 : 12,
                  width: 14,
                  filter: isHovered ? `drop-shadow(0 0 4px ${color})` : "none",
                }}
              >
                {icon}
              </span>
              <div
                className="flex-1 relative transition-all duration-150"
                style={{ height: isHovered ? 20 : 16 }}
              >
                {/* Background track */}
                <div
                  className="absolute inset-0 rounded"
                  style={{ background: colors.void.lighter }}
                />
                {/* Filled bar */}
                <div
                  className="absolute inset-y-0 left-0 rounded transition-all duration-150"
                  style={{
                    width: `${pct}%`,
                    background: `linear-gradient(90deg, ${color}90 0%, ${color} 100%)`,
                    minWidth: count > 0 ? 2 : 0,
                    boxShadow: isHovered ? `0 0 8px ${color}60` : "none",
                  }}
                />
                {/* Label overlay */}
                <div className="absolute inset-0 flex items-center justify-between px-2">
                  <span
                    className="transition-all duration-150"
                    style={{
                      color: isHovered
                        ? colors.text.bright
                        : colors.text.standard,
                      fontSize: isHovered ? 13 : 12,
                      fontWeight: isHovered ? 500 : 400,
                    }}
                  >
                    {key}
                  </span>
                  <span
                    className="font-mono transition-all duration-150"
                    style={{
                      color: isHovered
                        ? colors.text.bright
                        : colors.text.standard,
                      fontSize: isHovered ? 13 : 12,
                      fontWeight: isHovered ? 600 : 400,
                    }}
                  >
                    {count}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface ColorBreakdownPanelProps {
  colorData: Record<string, number>;
}

function ColorBreakdownPanel({
  colorData,
}: ColorBreakdownPanelProps): ReactNode {
  const [hoveredColor, setHoveredColor] = useState<string | null>(null);
  // MTG color wheel order: W-U-B-R-G (clockwise)
  const colorConfig = [
    { key: "W", name: "White", color: colors.mana.white.color },
    { key: "U", name: "Blue", color: colors.mana.blue.color },
    { key: "B", name: "Black", color: colors.mana.black.color },
    { key: "R", name: "Red", color: colors.mana.red.color },
    { key: "G", name: "Green", color: colors.mana.green.color },
    { key: "C", name: "Colorless", color: "#bab1ab" },
  ];

  const total = colorConfig.reduce(
    (sum, { key }) => sum + (colorData[key] || 0),
    0,
  );

  // Calculate donut segments
  const segments: Array<{
    key: string;
    name: string;
    color: string;
    count: number;
    startAngle: number;
    endAngle: number;
  }> = [];
  let currentAngle = -90; // Start at top

  colorConfig.forEach(({ key, name, color }) => {
    const count = colorData[key] || 0;
    if (count > 0) {
      const angle = (count / total) * 360;
      segments.push({
        key,
        name,
        color,
        count,
        startAngle: currentAngle,
        endAngle: currentAngle + angle,
      });
      currentAngle += angle;
    }
  });

  // SVG arc path helper
  const describeArc = (
    cx: number,
    cy: number,
    r: number,
    startAngle: number,
    endAngle: number,
  ): string => {
    const start = {
      x: cx + r * Math.cos((Math.PI * startAngle) / 180),
      y: cy + r * Math.sin((Math.PI * startAngle) / 180),
    };
    const end = {
      x: cx + r * Math.cos((Math.PI * endAngle) / 180),
      y: cy + r * Math.sin((Math.PI * endAngle) / 180),
    };
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
  };

  const size = 70;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 30;
  const innerR = 18;

  return (
    <div className="p-3 rounded-lg overflow-hidden" style={panelStyle}>
      <div className="mb-3">
        <span
          className="text-sm font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Colors
        </span>
      </div>
      <div className="flex items-start gap-3">
        {/* Donut chart */}
        <svg width={size} height={size} className="shrink-0">
          <defs>
            <filter id="colorGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          {/* Background ring */}
          <circle
            cx={cx}
            cy={cy}
            r={(outerR + innerR) / 2}
            fill="none"
            stroke={colors.void.lighter}
            strokeWidth={outerR - innerR}
          />
          {/* Colored segments */}
          {segments.map((seg) => {
            const isHovered = hoveredColor === seg.key;
            // Handle full circle case
            if (seg.endAngle - seg.startAngle >= 359.9) {
              return (
                <circle
                  key={seg.key}
                  cx={cx}
                  cy={cy}
                  r={(outerR + innerR) / 2}
                  fill="none"
                  stroke={seg.color}
                  strokeWidth={
                    isHovered ? outerR - innerR + 4 : outerR - innerR
                  }
                  filter={isHovered ? "url(#colorGlow)" : undefined}
                  style={{ transition: "all 0.15s ease" }}
                />
              );
            }
            return (
              <path
                key={seg.key}
                d={describeArc(
                  cx,
                  cy,
                  (outerR + innerR) / 2,
                  seg.startAngle,
                  seg.endAngle - 1,
                )}
                fill="none"
                stroke={seg.color}
                strokeWidth={isHovered ? outerR - innerR + 4 : outerR - innerR}
                strokeLinecap="round"
                filter={isHovered ? "url(#colorGlow)" : undefined}
                style={{ transition: "all 0.15s ease" }}
              />
            );
          })}
          {/* Center text */}
          <text
            x={cx}
            y={cy}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={hoveredColor ? colors.text.bright : colors.text.muted}
            fontSize={hoveredColor ? "11" : "10"}
            fontFamily="monospace"
            style={{ transition: "all 0.15s ease" }}
          >
            {hoveredColor
              ? (segments.find((s) => s.key === hoveredColor)?.count ?? total)
              : total}
          </text>
        </svg>
        {/* Legend */}
        <div className="flex-1 space-y-0.5">
          {segments.map(({ key, name, color, count }) => {
            const isHovered = hoveredColor === key;
            return (
              <div
                key={key}
                className="flex items-center gap-1.5 text-xs cursor-default"
                onMouseEnter={() => setHoveredColor(key)}
                onMouseLeave={() => setHoveredColor(null)}
              >
                <i
                  className={`ms ms-${key.toLowerCase()} transition-all duration-150`}
                  style={{
                    color,
                    fontSize: isHovered ? 13 : 11,
                    filter: isHovered
                      ? `drop-shadow(0 0 4px ${color})`
                      : "none",
                  }}
                />
                <span
                  className="transition-all duration-150"
                  style={{
                    color: isHovered ? colors.text.standard : colors.text.muted,
                    fontSize: isHovered ? 13 : 12,
                  }}
                >
                  {name}
                </span>
                <span
                  className="font-mono ml-auto transition-all duration-150"
                  style={{
                    color,
                    fontSize: isHovered ? 13 : 12,
                    fontWeight: isHovered ? 600 : 400,
                    textShadow: isHovered ? `0 0 6px ${color}` : "none",
                  }}
                >
                  {count}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface ManaCurvePanelProps {
  manaCurve: Record<number, number>;
}

function ManaCurvePanel({ manaCurve }: ManaCurvePanelProps): ReactNode {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const curveData = Array.from({ length: 8 }, (_, i) => ({
    cmc: i,
    label: i === 7 ? "7+" : String(i),
    count:
      i === 7
        ? Object.entries(manaCurve)
            .filter(([k]) => parseInt(k) >= 7)
            .reduce((sum, [, v]) => sum + v, 0)
        : manaCurve[i] || 0,
  }));
  const maxCount = Math.max(...curveData.map((d) => d.count), 1);
  const totalCards = curveData.reduce((sum, d) => sum + d.count, 0);
  const maxBarHeight = 32;

  // Calculate weighted average CMC
  const avgCmc =
    totalCards > 0
      ? curveData.reduce((sum, d) => sum + d.cmc * d.count, 0) / totalCards
      : 0;

  // Calculate position of average marker (0-7 maps to bar positions)
  const avgPosition = Math.min(avgCmc, 7);

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Mana Curve
        </span>
        <span
          className="text-xs font-mono"
          style={{ color: colors.text.muted }}
        >
          Avg {avgCmc.toFixed(1)}
        </span>
      </div>
      {/* Bar chart with counts and labels */}
      <div className="flex items-end gap-0.5">
        {curveData.map(({ label, count }, idx) => {
          const barHeight =
            maxCount > 0 ? (count / maxCount) * maxBarHeight : 0;
          const isAtAvg = Math.abs(idx - avgPosition) < 0.5;
          const isHovered = hoveredIdx === idx;
          return (
            <div
              key={label}
              className="flex-1 flex flex-col items-center cursor-default"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              {/* Count above bar */}
              <div
                className="font-mono mb-0.5 transition-all duration-150"
                style={{
                  fontSize: isHovered ? 12 : 10,
                  color: isHovered
                    ? colors.text.bright
                    : count > 0
                      ? colors.text.muted
                      : colors.text.dim,
                  fontWeight: isHovered ? 600 : 400,
                }}
              >
                {count > 0 ? count : ""}
              </div>
              {/* Bar */}
              <div
                className="w-full max-w-[18px] rounded-t transition-all duration-150"
                style={{
                  height: isHovered ? barHeight + 4 : barHeight,
                  minHeight: count > 0 ? 2 : 0,
                  background: isAtAvg
                    ? colors.gold.standard
                    : isHovered
                      ? colors.mana.blue.glow
                      : colors.mana.blue.color,
                  boxShadow: isHovered
                    ? `0 0 8px ${isAtAvg ? colors.gold.glow : colors.mana.blue.glow}`
                    : "none",
                }}
              />
              {/* CMC label */}
              <div
                className="font-mono mt-0.5 transition-all duration-150"
                style={{
                  fontSize: isHovered ? 12 : 10,
                  color: isHovered ? colors.text.standard : colors.text.dim,
                }}
              >
                {label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SETS REPRESENTED PANEL
// ═══════════════════════════════════════════════════════════════

interface SetsRepresentedPanelProps {
  topSets: Array<{ code: string; count: number }>;
}

function SetsRepresentedPanel({
  topSets,
}: SetsRepresentedPanelProps): ReactNode {
  const [hoveredSet, setHoveredSet] = useState<string | null>(null);
  const maxCount = topSets[0]?.count ?? 1;

  if (topSets.length === 0) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Sets
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.dim }}>
          No set data
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Sets
        </span>
        <span
          className="text-xs font-mono"
          style={{ color: colors.text.muted }}
        >
          {topSets.length} sets
        </span>
      </div>
      <div className="space-y-1.5">
        {topSets.slice(0, 6).map(({ code, count }) => {
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          const isHovered = hoveredSet === code;
          return (
            <div
              key={code}
              className="flex items-center gap-2 cursor-default"
              onMouseEnter={() => setHoveredSet(code)}
              onMouseLeave={() => setHoveredSet(null)}
            >
              {/* Set icon - use ss-grad for gradient coloring */}
              <i
                className={`ss ss-${code.toLowerCase()} ss-grad ss-rare transition-all duration-150`}
                style={{
                  fontSize: isHovered ? 16 : 14,
                  filter: isHovered
                    ? `drop-shadow(0 0 4px ${colors.gold.glow})`
                    : "none",
                  width: 18,
                }}
              />
              {/* Set code */}
              <span
                className="font-mono w-10 transition-all duration-150"
                style={{
                  fontSize: isHovered ? 13 : 12,
                  color: isHovered ? colors.text.bright : colors.text.standard,
                  fontWeight: isHovered ? 500 : 400,
                }}
              >
                {code.toUpperCase()}
              </span>
              {/* Bar */}
              <div
                className="flex-1 h-2 rounded-full overflow-hidden"
                style={{ background: colors.void.lighter }}
              >
                <div
                  className="h-full rounded-full transition-all duration-150"
                  style={{
                    width: `${pct}%`,
                    background: isHovered
                      ? colors.gold.standard
                      : colors.mana.blue.color,
                    minWidth: count > 0 ? 4 : 0,
                    boxShadow: isHovered
                      ? `0 0 6px ${colors.gold.glow}`
                      : "none",
                  }}
                />
              </div>
              {/* Count */}
              <span
                className="font-mono w-8 text-right transition-all duration-150"
                style={{
                  fontSize: isHovered ? 13 : 12,
                  color: isHovered ? colors.text.bright : colors.text.muted,
                }}
              >
                {count}
              </span>
            </div>
          );
        })}
      </div>
      {topSets.length > 6 && (
        <div
          className="text-[11px] mt-2 text-center"
          style={{ color: colors.text.dim }}
        >
          +{topSets.length - 6} more sets
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TOP KEYWORDS PANEL
// ═══════════════════════════════════════════════════════════════

interface TopKeywordsPanelProps {
  topKeywords: Array<{ keyword: string; count: number }>;
}

function TopKeywordsPanel({ topKeywords }: TopKeywordsPanelProps): ReactNode {
  const [hoveredKeyword, setHoveredKeyword] = useState<string | null>(null);

  if (topKeywords.length === 0) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Keywords
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.dim }}>
          No keyword data
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Keywords
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {topKeywords.map(({ keyword, count }) => {
          const isHovered = hoveredKeyword === keyword;
          return (
            <div
              key={keyword}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full cursor-default transition-all duration-150"
              style={{
                background: isHovered
                  ? `${colors.gold.standard}30`
                  : colors.void.light,
                border: `1px solid ${isHovered ? colors.gold.standard : colors.border.subtle}`,
                transform: isHovered ? "scale(1.05)" : "scale(1)",
              }}
              onMouseEnter={() => setHoveredKeyword(keyword)}
              onMouseLeave={() => setHoveredKeyword(null)}
            >
              <span
                className="text-xs transition-all duration-150"
                style={{
                  color: isHovered ? colors.text.bright : colors.text.standard,
                }}
              >
                {keyword}
              </span>
              <span
                className="text-xs font-mono px-1 rounded transition-all duration-150"
                style={{
                  background: isHovered
                    ? colors.gold.standard
                    : `${colors.mana.blue.color}40`,
                  color: isHovered ? colors.void.deep : colors.text.standard,
                }}
              >
                {count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TOP ARTISTS PANEL
// ═══════════════════════════════════════════════════════════════

interface TopArtistsPanelProps {
  topArtists: Array<{ artist: string; count: number }>;
}

function TopArtistsPanel({ topArtists }: TopArtistsPanelProps): ReactNode {
  const [hoveredArtist, setHoveredArtist] = useState<string | null>(null);
  const maxCount = topArtists[0]?.count ?? 1;

  if (topArtists.length === 0) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Top Artists
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.dim }}>
          No artist data
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Top Artists
        </span>
      </div>
      <div className="space-y-1">
        {topArtists.map(({ artist, count }) => {
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          const isHovered = hoveredArtist === artist;
          return (
            <div
              key={artist}
              className="relative cursor-default"
              onMouseEnter={() => setHoveredArtist(artist)}
              onMouseLeave={() => setHoveredArtist(null)}
            >
              {/* Background bar */}
              <div
                className="absolute inset-y-0 left-0 rounded transition-all duration-150"
                style={{
                  width: `${pct}%`,
                  background: isHovered
                    ? `${colors.rarity.mythic.color}30`
                    : `${colors.rarity.mythic.color}15`,
                }}
              />
              {/* Content */}
              <div className="relative flex items-center gap-2 py-0.5 px-1">
                {/* Paintbrush icon */}
                <svg
                  className="w-3 h-3 shrink-0 transition-all duration-150"
                  viewBox="0 0 16 16"
                  fill="none"
                  style={{ color: colors.rarity.mythic.color }}
                >
                  <path
                    d="M11.5 1.5L14.5 4.5L6 13H3V10L11.5 1.5Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M9.5 3.5L12.5 6.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
                <span
                  className="flex-1 truncate transition-all duration-150"
                  style={{
                    fontSize: isHovered ? 13 : 12,
                    color: isHovered
                      ? colors.text.bright
                      : colors.text.standard,
                  }}
                  title={artist}
                >
                  {artist}
                </span>
                <span
                  className="font-mono shrink-0 transition-all duration-150"
                  style={{
                    fontSize: isHovered ? 13 : 12,
                    color: isHovered
                      ? colors.rarity.mythic.color
                      : colors.text.muted,
                  }}
                >
                  {count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// LEGENDARIES PANEL
// ═══════════════════════════════════════════════════════════════

interface LegendariesPanelProps {
  legendaries: { creatures: number; other: number; total: number };
}

function LegendariesPanel({ legendaries }: LegendariesPanelProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  if (legendaries.total === 0) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Legendaries
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.dim }}>
          No legendaries
        </div>
      </div>
    );
  }

  const creaturePct =
    legendaries.total > 0
      ? (legendaries.creatures / legendaries.total) * 100
      : 0;

  return (
    <div
      className="p-3 rounded-lg cursor-default transition-all duration-150"
      style={{
        ...panelStyle,
        boxShadow: isHovered ? `0 0 12px ${colors.gold.glow}20` : "none",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Legendaries
        </span>
        <div
          className="flex items-center gap-1 transition-all duration-150"
          style={{
            color: isHovered ? colors.gold.bright : colors.gold.standard,
            filter: isHovered
              ? `drop-shadow(0 0 4px ${colors.gold.glow})`
              : "none",
          }}
        >
          {/* Crown icon */}
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 12L3.5 5L6 8L8 4L10 8L12.5 5L14 12H2Z" />
            <path d="M2 13H14V14H2V13Z" />
          </svg>
          <span className="text-xs font-mono">{legendaries.total}</span>
        </div>
      </div>

      {/* Stacked bar */}
      <div
        className="h-3 rounded-full overflow-hidden flex mb-2"
        style={{ background: colors.void.lighter }}
      >
        <div
          className="transition-all duration-300"
          style={{
            width: `${creaturePct}%`,
            background: colors.mana.green.color,
          }}
          title={`${legendaries.creatures} creatures`}
        />
        <div
          className="transition-all duration-300"
          style={{
            width: `${100 - creaturePct}%`,
            background: colors.mana.blue.color,
          }}
          title={`${legendaries.other} other`}
        />
      </div>

      {/* Breakdown */}
      <div className="flex justify-between text-xs">
        <div className="flex items-center gap-1">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: colors.mana.green.color }}
          />
          <span style={{ color: colors.text.muted }}>Creatures</span>
          <span className="font-mono" style={{ color: colors.text.standard }}>
            {legendaries.creatures}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: colors.mana.blue.color }}
          />
          <span style={{ color: colors.text.muted }}>Other</span>
          <span className="font-mono" style={{ color: colors.text.standard }}>
            {legendaries.other}
          </span>
        </div>
      </div>

      {legendaries.creatures > 0 && (
        <div
          className="mt-2 pt-2 text-[11px] text-center"
          style={{
            borderTop: `1px solid ${colors.border.subtle}`,
            color: colors.text.dim,
          }}
        >
          {legendaries.creatures} potential commanders
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// VALUE OVER TIME PANEL
// ═══════════════════════════════════════════════════════════════

interface ValueHistoryEntry {
  date: string;
  totalValue: number;
  cardCount: number;
}

interface ValueOverTimePanelProps {
  valueHistory: ValueHistoryEntry[];
  isLoading: boolean;
}

function ValueOverTimePanel({
  valueHistory,
  isLoading,
}: ValueOverTimePanelProps): ReactNode {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Value History
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.muted }}>
          Loading...
        </div>
      </div>
    );
  }

  if (valueHistory.length < 2) {
    return (
      <div className="p-3 rounded-lg" style={panelStyle}>
        <div className="mb-2">
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Value History
          </span>
        </div>
        <div className="text-xs" style={{ color: colors.text.dim }}>
          {valueHistory.length === 0
            ? "No price history yet. Record prices to start tracking."
            : "Need more data points to show trend."}
        </div>
      </div>
    );
  }

  // Get min/max for scaling
  const values = valueHistory.map((h) => h.totalValue);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const valueRange = maxValue - minValue || 1;

  // Chart dimensions
  const chartHeight = 60;

  // Calculate trend (absolute change)
  const firstValue = valueHistory[0]?.totalValue ?? 0;
  const lastValue = valueHistory[valueHistory.length - 1]?.totalValue ?? 0;
  const change = lastValue - firstValue;
  const isPositive = change >= 0;

  // Format date for display
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  };

  // Build SVG path for area chart
  const buildPath = (): { linePath: string; areaPath: string } => {
    if (valueHistory.length === 0) return { linePath: "", areaPath: "" };

    const points = valueHistory.map((h, i) => {
      const x = (i / (valueHistory.length - 1)) * 100;
      const y =
        chartHeight -
        ((h.totalValue - minValue) / valueRange) * (chartHeight - 10);
      return { x, y };
    });

    const linePath = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
      .join(" ");

    const areaPath = `${linePath} L 100 ${chartHeight} L 0 ${chartHeight} Z`;

    return { linePath, areaPath };
  };

  const { linePath, areaPath } = buildPath();

  return (
    <div className="p-3 rounded-lg" style={panelStyle}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Value History
        </span>
        <div
          className="flex items-center gap-1 text-xs font-mono"
          style={{
            color: isPositive ? colors.mana.green.color : colors.mana.red.color,
          }}
        >
          <span>{isPositive ? "▲" : "▼"}</span>
          <span>
            {isPositive ? "+" : "-"}$
            {Math.abs(change).toLocaleString(undefined, {
              maximumFractionDigits: 0,
            })}
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="relative" style={{ height: chartHeight }}>
        <svg
          viewBox={`0 0 100 ${chartHeight}`}
          preserveAspectRatio="none"
          className="w-full h-full"
        >
          <defs>
            <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={
                  isPositive ? colors.mana.green.color : colors.mana.red.color
                }
                stopOpacity="0.3"
              />
              <stop
                offset="100%"
                stopColor={
                  isPositive ? colors.mana.green.color : colors.mana.red.color
                }
                stopOpacity="0.05"
              />
            </linearGradient>
          </defs>
          {/* Area fill */}
          <path d={areaPath} fill="url(#valueGradient)" />
          {/* Line */}
          <path
            d={linePath}
            fill="none"
            stroke={
              isPositive ? colors.mana.green.color : colors.mana.red.color
            }
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
          {/* Data points (interactive) */}
          {valueHistory.map((h, i) => {
            const x = (i / (valueHistory.length - 1)) * 100;
            const y =
              chartHeight -
              ((h.totalValue - minValue) / valueRange) * (chartHeight - 10);
            const isHovered = hoveredIdx === i;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={isHovered ? 4 : 2}
                fill={
                  isPositive ? colors.mana.green.color : colors.mana.red.color
                }
                stroke={colors.void.deep}
                strokeWidth="1"
                style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}
        </svg>

        {/* Hover tooltip */}
        {hoveredIdx !== null && valueHistory[hoveredIdx] && (
          <div
            className="absolute px-2 py-1 rounded text-xs pointer-events-none"
            style={{
              left: `${(hoveredIdx / (valueHistory.length - 1)) * 100}%`,
              top: -28,
              transform: "translateX(-50%)",
              background: colors.void.medium,
              border: `1px solid ${colors.border.subtle}`,
              whiteSpace: "nowrap",
            }}
          >
            <span style={{ color: colors.text.bright }}>
              $
              {valueHistory[hoveredIdx].totalValue.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </span>
            <span style={{ color: colors.text.dim, marginLeft: 4 }}>
              {formatDate(valueHistory[hoveredIdx].date)}
            </span>
          </div>
        )}
      </div>

      {/* Date range */}
      <div
        className="flex justify-between mt-1 text-[10px]"
        style={{ color: colors.text.dim }}
      >
        <span>{formatDate(valueHistory[0]?.date ?? "")}</span>
        <span>
          {formatDate(valueHistory[valueHistory.length - 1]?.date ?? "")}
        </span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// COLLECTION ROW - Collapsible tree with prices
// ═══════════════════════════════════════════════════════════════

const ROW_HEIGHT = 36;
const CHILD_ROW_HEIGHT = 32;

interface GroupedCardRowProps {
  group: GroupedCard;
  priceMap: Map<string, number>;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onSelect: (card: CollectionCard) => void;
  onEdit: (card: CollectionCard) => void;
  selectedCards: Set<string>;
  onToggleSelection: (card: CollectionCard) => void;
  sortBy: SortField;
}

// Helper to format sort field value for display
function formatSortValue(
  sortBy: SortField,
  group: GroupedCard,
  _priceMap: Map<string, number>,
): { label: string; value: string; color: string } | null {
  // Don't show extra column for basic/default sorts
  if (["name", "dateAdded", "quantity", "setCode"].includes(sortBy)) {
    return null;
  }

  switch (sortBy) {
    case "price": {
      const price = group.totalPrice;
      return {
        label: "Price",
        value: price > 0 ? `$${price.toFixed(2)}` : "-",
        color:
          price > 10
            ? colors.gold.standard
            : price > 1
              ? colors.text.standard
              : colors.text.muted,
      };
    }
    case "rarity":
      return {
        label: "Rarity",
        value: group.rarity
          ? group.rarity.charAt(0).toUpperCase() + group.rarity.slice(1)
          : "-",
        color:
          group.rarity === "mythic"
            ? colors.rarity.mythic.color
            : group.rarity === "rare"
              ? colors.rarity.rare.color
              : group.rarity === "uncommon"
                ? colors.rarity.uncommon.color
                : colors.text.muted,
      };
    case "cmc":
      return {
        label: "MV",
        value: group.cmc.toString(),
        color: colors.mana.blue.color,
      };
    case "type":
      return {
        label: "Type",
        value: group.typeLine?.split("—")[0].trim() ?? "-",
        color: colors.text.standard,
      };
    case "color": {
      const colorStr = group.colors.length > 0 ? group.colors.join("") : "C";
      return {
        label: "Color",
        value: colorStr,
        color:
          group.colors.length === 1
            ? ((colors.mana as Record<string, { color: string }>)[
                group.colors[0].toLowerCase()
              ]?.color ?? colors.text.muted)
            : group.colors.length > 1
              ? colors.gold.standard
              : colors.text.muted,
      };
    }
    case "winRate":
      return {
        label: "WR",
        value:
          group.winRate != null ? `${(group.winRate * 100).toFixed(1)}%` : "-",
        color:
          group.winRate != null && group.winRate > 0.55
            ? colors.mana.green.color
            : group.winRate != null && group.winRate < 0.45
              ? colors.mana.red.color
              : colors.text.standard,
      };
    case "tier":
      return {
        label: "Tier",
        value: group.tier ?? "-",
        color:
          group.tier === "S" || group.tier === "A"
            ? colors.gold.standard
            : group.tier === "B"
              ? colors.mana.green.color
              : group.tier === "C"
                ? colors.text.standard
                : colors.text.muted,
      };
    case "draftPick":
      return {
        label: "ATA",
        value: group.draftPick != null ? group.draftPick.toFixed(1) : "-",
        color:
          group.draftPick != null && group.draftPick < 3
            ? colors.gold.standard
            : group.draftPick != null && group.draftPick < 6
              ? colors.mana.green.color
              : colors.text.muted,
      };
    default:
      return null;
  }
}

function GroupedCardRow({
  group,
  priceMap,
  isExpanded,
  onToggleExpand,
  onSelect,
  onEdit,
  selectedCards,
  onToggleSelection,
  sortBy,
}: GroupedCardRowProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const totalCards = group.totalQuantity + group.totalFoilQuantity;
  const hasMultiple = group.hasMultiplePrintings;

  // Check if any/all printings are selected
  const selectedCount = group.printings.filter((p) => {
    const key = getPriceKey(p.cardName, p.setCode, p.collectorNumber);
    return selectedCards.has(key);
  }).length;
  const isFullySelected = selectedCount === group.printings.length;
  const isPartiallySelected = selectedCount > 0 && !isFullySelected;

  return (
    <div>
      {/* Parent row */}
      <div
        className="flex items-center px-3 gap-2 transition-all duration-100 cursor-pointer"
        style={{
          height: ROW_HEIGHT,
          background: isHovered ? colors.void.lighter : "transparent",
          borderBottom: `1px solid ${colors.border.subtle}`,
          borderLeft: isExpanded
            ? `2px solid ${colors.gold.standard}`
            : isHovered
              ? `2px solid ${colors.gold.dim}`
              : "2px solid transparent",
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={() => {
          if (hasMultiple) {
            onToggleExpand();
          } else {
            onSelect(group.printings[0]);
          }
        }}
      >
        {/* Checkbox for selection */}
        <div
          className="w-5 flex items-center justify-center cursor-pointer"
          onClick={(e) => {
            e.stopPropagation();
            // Toggle all printings in the group
            group.printings.forEach((p) => onToggleSelection(p));
          }}
        >
          <div
            className="w-4 h-4 rounded border flex items-center justify-center transition-all duration-150"
            style={{
              borderColor:
                isFullySelected || isPartiallySelected
                  ? colors.gold.standard
                  : colors.border.subtle,
              background: isFullySelected
                ? colors.gold.standard
                : isPartiallySelected
                  ? `${colors.gold.standard}40`
                  : "transparent",
              boxShadow:
                isFullySelected || isPartiallySelected
                  ? `0 0 6px ${colors.gold.glow}60`
                  : `0 1px 3px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)`,
            }}
          >
            {isFullySelected && (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                <path
                  d="M2 5l2 2 4-4"
                  stroke={colors.void.deepest}
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
            {isPartiallySelected && (
              <div
                className="w-2 h-0.5 rounded-full"
                style={{ background: colors.gold.standard }}
              />
            )}
          </div>
        </div>

        {/* Expand/collapse icon for multiple printings */}
        {hasMultiple ? (
          <div
            className="w-4 flex items-center justify-center transition-transform duration-150"
            style={{
              color: colors.text.muted,
              transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <path d="M3 1l4 4-4 4V1z" />
            </svg>
          </div>
        ) : (
          <div className="w-4" />
        )}

        {/* Quantity badge */}
        <div
          className="font-mono text-sm font-bold w-9 text-center py-0.5 rounded"
          style={{
            background: hasMultiple
              ? `${colors.mana.blue.color}20`
              : `${colors.gold.standard}20`,
            color: hasMultiple ? colors.mana.blue.color : colors.gold.standard,
          }}
        >
          {totalCards}x
        </div>

        {/* Card name - colored by rarity */}
        <div
          className="flex-1 font-display text-base truncate"
          style={{
            color: isHovered
              ? colors.text.bright
              : getNameColorForRarity(group.rarity),
          }}
        >
          {group.cardName}
        </div>

        {/* Multiple printings indicator */}
        {hasMultiple && (
          <div
            className="text-sm px-2 py-0.5 rounded"
            style={{
              background: `${colors.void.lighter}`,
              color: colors.text.muted,
            }}
          >
            {group.printings.length} prints
          </div>
        )}

        {/* Single printing set info */}
        {!hasMultiple && group.printings[0]?.setCode && (
          <div
            className="flex items-center gap-1.5 text-sm"
            style={{ color: colors.text.muted }}
          >
            <i
              className={`ss ss-${group.printings[0].setCode.toLowerCase()}`}
              style={{ fontSize: 16 }}
            />
            <span>{group.printings[0].setCode.toUpperCase()}</span>
          </div>
        )}

        {/* Foil indicator */}
        {group.totalFoilQuantity > 0 && (
          <div
            className="flex items-center gap-1 text-sm"
            style={{ color: "#b86fce" }}
          >
            <span>✨</span>
            <span>{group.totalFoilQuantity}</span>
          </div>
        )}

        {/* Sort field value (when sorting by metadata/gameplay fields) */}
        {(() => {
          const sortValue = formatSortValue(sortBy, group, priceMap);
          if (!sortValue || sortBy === "price") return null; // Price shown separately

          // Special rendering for color - use mana icons (no background)
          if (sortBy === "color") {
            const cardColors = group.colors;
            if (cardColors.length === 0) {
              // Colorless
              return (
                <div
                  className="flex items-center gap-0.5 px-2 py-0.5"
                  title="Colorless"
                >
                  <i
                    className="ms ms-c ms-cost"
                    style={{ fontSize: 14, color: colors.text.muted }}
                  />
                </div>
              );
            }
            return (
              <div
                className="flex items-center gap-0.5 px-2 py-0.5"
                title={sortValue.label}
              >
                {cardColors.map((c, i) => (
                  <i
                    key={i}
                    className={`ms ms-${c.toLowerCase()} ms-cost`}
                    style={{ fontSize: 14 }}
                  />
                ))}
              </div>
            );
          }

          return (
            <div
              className="font-mono text-sm min-w-[50px] text-right px-2 py-0.5 rounded"
              style={{
                color: sortValue.color,
                background: `${sortValue.color}15`,
              }}
              title={sortValue.label}
            >
              {sortValue.value}
            </div>
          );
        })()}

        {/* Price */}
        {group.totalPrice > 0 && (
          <div
            className="font-mono text-sm font-semibold min-w-[60px] text-right"
            style={{ color: getPriceColor(group.totalPrice) }}
          >
            {formatPrice(group.totalPrice)}
          </div>
        )}

        {/* Edit button for single printing */}
        {!hasMultiple && (
          <button
            className="p-1 rounded transition-opacity duration-100"
            style={{
              opacity: isHovered ? 1 : 0,
              background: colors.void.lighter,
              color: colors.text.muted,
            }}
            onClick={(e) => {
              e.stopPropagation();
              onEdit(group.printings[0]);
            }}
            title="Edit card"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        )}
      </div>

      {/* Child rows (printings) when expanded */}
      {isExpanded &&
        group.printings.map((printing, idx) => {
          const printingKey = getPriceKey(
            printing.cardName,
            printing.setCode,
            printing.collectorNumber,
          );
          return (
            <PrintingRow
              key={`${printing.setCode}-${printing.collectorNumber}-${idx}`}
              card={printing}
              price={priceMap.get(printingKey) ?? 0}
              onSelect={onSelect}
              onEdit={onEdit}
              isSelected={selectedCards.has(printingKey)}
              onToggleSelection={onToggleSelection}
            />
          );
        })}
    </div>
  );
}

interface PrintingRowProps {
  card: CollectionCard;
  price: number;
  onSelect: (card: CollectionCard) => void;
  onEdit: (card: CollectionCard) => void;
  isSelected: boolean;
  onToggleSelection: (card: CollectionCard) => void;
}

function PrintingRow({
  card,
  price,
  onSelect,
  onEdit,
  isSelected,
  onToggleSelection,
}: PrintingRowProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const totalCards = card.quantity + card.foilQuantity;
  const totalValue = price * totalCards;

  return (
    <div
      className="flex items-center pl-9 pr-3 gap-2 transition-all duration-100 cursor-pointer"
      style={{
        height: CHILD_ROW_HEIGHT,
        background: isHovered
          ? `${colors.gold.glow}10`
          : `${colors.void.deep}50`,
        borderBottom: `1px solid ${colors.border.subtle}20`,
        borderLeft: `2px solid ${colors.gold.dim}40`,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onSelect(card)}
    >
      {/* Checkbox for selection */}
      <div
        className="w-5 flex items-center justify-center"
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelection(card);
        }}
      >
        <div
          className="w-4 h-4 rounded border flex items-center justify-center transition-all duration-150"
          style={{
            borderColor: isSelected
              ? colors.gold.standard
              : colors.border.subtle,
            background: isSelected ? colors.gold.standard : "transparent",
            boxShadow: isSelected
              ? `0 0 6px ${colors.gold.glow}60`
              : `0 1px 3px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)`,
          }}
        >
          {isSelected && (
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path
                d="M2 5l2 2 4-4"
                stroke={colors.void.deepest}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Quantity */}
      <div
        className="font-mono text-sm w-7 text-center"
        style={{ color: colors.text.muted }}
      >
        {totalCards}x
      </div>

      {/* Set icon and code */}
      <div
        className="flex items-center gap-2 min-w-[110px]"
        style={{ color: isHovered ? colors.text.standard : colors.text.muted }}
      >
        {card.setCode && (
          <>
            <i
              className={`ss ss-${card.setCode.toLowerCase()}`}
              style={{ fontSize: 16 }}
            />
            <span className="text-sm font-mono">
              {card.setCode.toUpperCase()}
            </span>
          </>
        )}
        {card.collectorNumber && (
          <span className="text-sm" style={{ color: colors.text.dim }}>
            #{card.collectorNumber}
          </span>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Foil indicator */}
      {card.foilQuantity > 0 && (
        <div
          className="flex items-center gap-1 text-xs"
          style={{ color: "#b86fce" }}
        >
          <span>✨</span>
          <span>{card.foilQuantity}</span>
        </div>
      )}

      {/* Unit price */}
      {price > 0 && (
        <div
          className="text-xs min-w-[45px] text-right"
          style={{ color: colors.text.muted }}
        >
          @{formatPrice(price)}
        </div>
      )}

      {/* Total value */}
      {totalValue > 0 && (
        <div
          className="font-mono text-xs font-semibold min-w-[55px] text-right"
          style={{ color: getPriceColor(totalValue) }}
        >
          {formatPrice(totalValue)}
        </div>
      )}

      {/* Edit button */}
      <button
        className="p-0.5 rounded transition-opacity duration-100"
        style={{
          opacity: isHovered ? 1 : 0,
          background: colors.void.lighter,
          color: colors.text.muted,
        }}
        onClick={(e) => {
          e.stopPropagation();
          onEdit(card);
        }}
        title="Edit printing"
      >
        <svg
          width="11"
          height="11"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

export function CollectionScreen(): ReactNode {
  const [filters, setFilters] =
    useState<CollectionFilters>(createEmptyFilters());
  const [isFilterPanelCollapsed, setIsFilterPanelCollapsed] = useState(true);
  const [isAnalyticsSidebarOpen, setIsAnalyticsSidebarOpen] = useState(true);
  const [collection, setCollection] = useState<CollectionCard[]>([]);
  const [stats, setStats] = useState<CollectionStatsDetailed | null>(null);
  const [priceData, setPriceData] = useState<PriceCollectionResponse | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isPricingLoading, setIsPricingLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [editingCard, setEditingCard] = useState<CollectionCard | null>(null);
  const [viewingCardName, setViewingCardName] = useState<string | null>(null);
  const [viewingSetCode, setViewingSetCode] = useState<string | null>(null);
  const [viewingCollectorNumber, setViewingCollectorNumber] = useState<
    string | null
  >(null);
  const [isRecordingPrices, setIsRecordingPrices] = useState(false);
  const [priceRecordStatus, setPriceRecordStatus] = useState<string | null>(
    null,
  );
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const [valueHistory, setValueHistory] = useState<
    Array<{ date: string; totalValue: number; cardCount: number }>
  >([]);
  const [isValueHistoryLoading, setIsValueHistoryLoading] = useState(false);

  // Sort state
  const [sortBy, setSortBy] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");

  // Multi-select state for bulk operations
  const [selectedCards, setSelectedCards] = useState<Set<string>>(new Set());

  // Prevent double initialization from React StrictMode
  const initializedRef = useRef(false);

  // Fetch collection list and stats (fetches ALL cards, sorting done client-side)
  const fetchCollectionData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all cards sorted by name - client-side sorting handles the rest
      // This avoids re-fetching when sort changes
      const [listResult, statsResult] = await Promise.all([
        window.electronAPI.collection.listSorted({
          sortBy: "name",
          sortOrder: "asc",
          pageSize: 10000, // Fetch all cards for client-side sorting
        }),
        window.electronAPI.collection.stats(),
      ]);

      // Transform API response (snake_case) to component format (camelCase)
      const transformedCards: CollectionCard[] = listResult.cards.map(
        (card) => ({
          cardName: card.card_name,
          quantity: card.quantity,
          foilQuantity: card.foil_quantity,
          setCode: card.set_code,
          setName: null, // Not in API response
          collectorNumber: card.collector_number,
          addedAt: card.added_at,
          colors: card.colors ?? [],
          typeLine: card.type_line ?? null,
          rarity: card.rarity ?? null,
          cmc: card.cmc ?? 0,
          priceUsd: card.price_usd ?? null,
          priceUsdFoil: null,
          // Gameplay stats
          winRate: card.win_rate ?? null,
          tier: card.tier ?? null,
          draftPick: card.draft_pick ?? null,
        }),
      );
      setCollection(transformedCards);

      if (statsResult && !statsResult.error) {
        setStats(statsResult);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  }, []); // No dependencies - fetch once, sort client-side

  // Fetch pricing data in background
  const fetchPricingData = useCallback(async () => {
    setIsPricingLoading(true);

    try {
      const priceResult = await window.electronAPI.collection.getValue();
      if (priceResult) {
        setPriceData(priceResult);
      }
    } catch (err) {
      console.warn("Failed to fetch pricing data:", err);
    } finally {
      setIsPricingLoading(false);
    }
  }, []);

  // Fetch collection value history (90 days)
  const fetchValueHistory = useCallback(async () => {
    setIsValueHistoryLoading(true);
    try {
      const history = await window.electronAPI.collection.valueHistory(90);
      setValueHistory(history);
    } catch (err) {
      console.error("Failed to fetch value history:", err);
    } finally {
      setIsValueHistoryLoading(false);
    }
  }, []);

  // Initial data load and refetch when sort changes
  useEffect(() => {
    // Skip pricing on subsequent sort changes (only fetch on first load)
    const isInitialLoad = !initializedRef.current;
    initializedRef.current = true;

    fetchCollectionData().then(() => {
      if (isInitialLoad) {
        fetchPricingData();
        fetchValueHistory();
      }
    });
  }, [fetchCollectionData, fetchPricingData, fetchValueHistory]);

  // Manual refresh function for user-triggered reloads
  const fetchData = useCallback(async () => {
    await fetchCollectionData();
    fetchPricingData();
  }, [fetchCollectionData, fetchPricingData]);

  // Sort change handler
  const handleSortChange = useCallback(
    (field: SortField) => {
      if (field === sortBy) {
        // Toggle order if same field
        setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        // Set new field with its default order
        const option = SORT_OPTIONS.find((o) => o.value === field);
        setSortBy(field);
        setSortOrder(option?.defaultOrder ?? "asc");
      }
    },
    [sortBy],
  );

  // Selection handlers
  const handleToggleCardSelection = useCallback((card: CollectionCard) => {
    const key = getPriceKey(card.cardName, card.setCode, card.collectorNumber);
    setSelectedCards((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedCards(new Set());
  }, []);

  // Bulk action state
  const [showBulkDeckSelector, setShowBulkDeckSelector] = useState(false);
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [bulkActionStatus, setBulkActionStatus] = useState<string | null>(null);
  const [lastSelectedDeckId, setLastSelectedDeckId] = useState<number | null>(
    null,
  );

  // Load last selected deck ID
  useEffect(() => {
    window.electronAPI.store
      .get<number | null>("lastSelectedDeckId")
      .then(setLastSelectedDeckId)
      .catch(() => setLastSelectedDeckId(null));
  }, []);

  // Get selected cards from collection as BulkCardSelection for the dropdown
  const getSelectedCardsForBulk = useCallback((): BulkCardSelection[] => {
    return collection
      .filter((card) => {
        const key = getPriceKey(
          card.cardName,
          card.setCode,
          card.collectorNumber,
        );
        return selectedCards.has(key);
      })
      .map((card) => ({
        cardName: card.cardName,
        setCode: card.setCode,
        collectorNumber: card.collectorNumber,
        availableQuantity: card.quantity + card.foilQuantity,
        selectedQuantity: card.quantity + card.foilQuantity, // Default to all
        enabled: true, // All selected cards enabled by default
      }));
  }, [collection, selectedCards]);

  // Bulk add to deck handler - now accepts quantities map from dropdown
  const handleBulkAddToDeck = useCallback(
    async (
      deckId: number,
      deckName: string,
      quantities?: Map<string, number>,
    ): Promise<void> => {
      const cardsToAdd = getSelectedCardsForBulk();

      // Calculate total cards being added
      let totalAdding = 0;
      for (const card of cardsToAdd) {
        const key = getPriceKey(
          card.cardName,
          card.setCode,
          card.collectorNumber,
        );
        const qty = quantities?.get(key) ?? card.availableQuantity;
        totalAdding += qty;
      }

      setBulkActionStatus(`Adding ${totalAdding} cards to ${deckName}...`);

      try {
        for (const card of cardsToAdd) {
          const key = getPriceKey(
            card.cardName,
            card.setCode,
            card.collectorNumber,
          );
          const quantity = quantities?.get(key) ?? card.availableQuantity;

          if (quantity > 0) {
            await window.electronAPI.decks.addCard(deckId, {
              card_name: card.cardName,
              quantity,
              set_code: card.setCode ?? undefined,
              collector_number: card.collectorNumber ?? undefined,
            });
          }
        }

        // Persist deck selection
        await window.electronAPI.store.set("lastSelectedDeckId", deckId);
        setLastSelectedDeckId(deckId);
        setShowBulkDeckSelector(false);
        handleClearSelection();
        setBulkActionStatus(`Added ${totalAdding} cards to ${deckName}`);
        setTimeout(() => setBulkActionStatus(null), 3000);
      } catch (err) {
        setBulkActionStatus(
          `Error: ${err instanceof Error ? err.message : "Failed to add cards"}`,
        );
        setTimeout(() => setBulkActionStatus(null), 5000);
      }
    },
    [getSelectedCardsForBulk, handleClearSelection],
  );

  // Bulk delete handler
  const handleBulkDelete = useCallback(async (): Promise<void> => {
    const cardsToDelete = getSelectedCardsForBulk();
    setBulkActionStatus(`Deleting ${cardsToDelete.length} cards...`);

    try {
      for (const card of cardsToDelete) {
        await window.electronAPI.collection.delete({
          cardName: card.cardName,
          setCode: card.setCode,
          collectorNumber: card.collectorNumber,
        });
      }

      setShowBulkDeleteConfirm(false);
      handleClearSelection();
      setBulkActionStatus(`Deleted ${cardsToDelete.length} cards`);
      setTimeout(() => setBulkActionStatus(null), 3000);
      fetchData(); // Refresh collection
    } catch (err) {
      setBulkActionStatus(
        `Error: ${err instanceof Error ? err.message : "Failed to delete cards"}`,
      );
      setTimeout(() => setBulkActionStatus(null), 5000);
    }
  }, [getSelectedCardsForBulk, handleClearSelection, fetchData]);

  // Basic stats
  const basicStats = {
    unique: stats?.unique ?? collection.length,
    total:
      stats?.total ??
      collection.reduce((sum, c) => sum + c.quantity + c.foilQuantity, 0),
    foils:
      stats?.foils ?? collection.reduce((sum, c) => sum + c.foilQuantity, 0),
    avgCmc: stats?.avgCmc ?? 0,
  };

  // Build price map from priced cards
  const priceMap = useMemo(
    () => buildPriceMap(priceData?.cards),
    [priceData?.cards],
  );

  // Filter collection using comprehensive filters
  const filteredCollection = useMemo(() => {
    return collection.filter((card) => {
      // Search filter
      if (
        filters.search &&
        !card.cardName.toLowerCase().includes(filters.search.toLowerCase())
      ) {
        return false;
      }

      // Rarity filter
      if (filters.rarities.size > 0) {
        const cardRarity = card.rarity?.toLowerCase() || "";
        if (!filters.rarities.has(cardRarity)) {
          return false;
        }
      }

      // Set filter
      if (filters.sets.size > 0) {
        if (!card.setCode || !filters.sets.has(card.setCode.toLowerCase())) {
          return false;
        }
      }

      // Foil filters
      if (filters.foilOnly && card.foilQuantity === 0) {
        return false;
      }
      if (filters.nonFoilOnly && card.quantity === 0) {
        return false;
      }

      // Price filters (need to look up price)
      if (filters.priceMin !== null || filters.priceMax !== null) {
        const priceKey = getPriceKey(
          card.cardName,
          card.setCode,
          card.collectorNumber,
        );
        const price = priceMap.get(priceKey) ?? 0;

        if (filters.priceMin !== null && price < filters.priceMin) {
          return false;
        }
        if (filters.priceMax !== null && price > filters.priceMax) {
          return false;
        }
      }

      // Color filter - card must have at least one of the selected colors
      if (filters.colors.size > 0) {
        const cardColors = card.colors || [];
        // If card is colorless and colorless is selected, it matches
        if (cardColors.length === 0) {
          if (!filters.colors.has("C")) {
            return false;
          }
        } else {
          // Card must have at least one of the selected colors
          const hasMatchingColor = cardColors.some((c) =>
            filters.colors.has(c.toUpperCase()),
          );
          if (!hasMatchingColor) {
            return false;
          }
        }
      }

      // Type filter - card's type line must contain at least one of the selected types
      if (filters.types.size > 0) {
        const typeLine = (card.typeLine || "").toLowerCase();
        const typeMatches = Array.from(filters.types).some((t) =>
          typeLine.includes(t.toLowerCase()),
        );
        if (!typeMatches) {
          return false;
        }
      }

      return true;
    });
  }, [collection, filters, priceMap]);

  // Group filtered collection by card name and re-sort based on current sort field
  const groupedCards = useMemo(
    () => groupCollectionCards(filteredCollection, priceMap, sortBy, sortOrder),
    [filteredCollection, priceMap, sortBy, sortOrder],
  );

  // Toggle card expansion
  const toggleCardExpanded = useCallback((cardName: string) => {
    setExpandedCards((prev) => {
      const next = new Set(prev);
      if (next.has(cardName)) {
        next.delete(cardName);
      } else {
        next.add(cardName);
      }
      return next;
    });
  }, []);

  // Handle card click - open detail modal with specific printing
  const handleCardSelect = (card: CollectionCard): void => {
    setViewingCardName(card.cardName);
    setViewingSetCode(card.setCode);
    setViewingCollectorNumber(card.collectorNumber);
  };

  const handleCardEdit = (card: CollectionCard): void => {
    setEditingCard(card);
  };

  const handleCardSave = useCallback((updated: CollectionCard): void => {
    setCollection((prev) =>
      prev.map((c) =>
        c.cardName === updated.cardName &&
        c.setCode === updated.setCode &&
        c.collectorNumber === updated.collectorNumber
          ? updated
          : c,
      ),
    );
    setEditingCard(null);
  }, []);

  const handleCardDelete = useCallback((): void => {
    if (!editingCard) return;

    setCollection((prev) =>
      prev.filter(
        (c) =>
          !(
            c.cardName === editingCard.cardName &&
            c.setCode === editingCard.setCode &&
            c.collectorNumber === editingCard.collectorNumber
          ),
      ),
    );
    setEditingCard(null);
    fetchData();
  }, [editingCard, fetchData]);

  const handleImport = useCallback(
    async (text: string, mode: "replace" | "add") => {
      try {
        const result = await window.electronAPI.collection.import(text, mode);
        if (result.errors && result.errors.length > 0) {
          console.warn("Import completed with errors:", result.errors);
        }
        console.log(
          `Imported ${result.added_count} cards (${result.total_cards} total)`,
        );
      } catch (error) {
        console.error("Import failed:", error);
      } finally {
        setIsImportModalOpen(false);
        fetchData();
      }
    },
    [fetchData],
  );

  const handleRecordPrices = useCallback(async () => {
    setIsRecordingPrices(true);
    setPriceRecordStatus(null);

    try {
      const result = await window.electronAPI.collection.recordPrices();
      if (result.success) {
        setPriceRecordStatus(
          `Recorded prices for ${result.cardsRecorded} cards`,
        );
        setTimeout(() => setPriceRecordStatus(null), 3000);
      } else {
        setPriceRecordStatus(result.error || "Failed to record prices");
      }
    } catch (err) {
      setPriceRecordStatus(`Error: ${String(err)}`);
    } finally {
      setIsRecordingPrices(false);
    }
  }, []);

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 100% 80% at 0% 0%, ${colors.mana.green.color}06 0%, transparent 50%),
      radial-gradient(ellipse 80% 60% at 100% 100%, ${colors.gold.glow}08 0%, transparent 50%),
      radial-gradient(ellipse 60% 40% at 50% 50%, ${colors.mana.blue.color}04 0%, transparent 60%),
      ${colors.void.deepest}
    `,
  };

  if (isLoading) {
    return (
      <div
        className="h-full flex items-center justify-center relative"
        style={containerStyle}
      >
        <ConstellationBackground />
        <div className="text-center relative z-10">
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
            Opening vault...
          </p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative" style={containerStyle}>
      <ConstellationBackground />

      {/* Compact Header */}
      <div
        className="relative z-10 px-4 py-3 border-b"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{
                background: `linear-gradient(135deg, ${colors.gold.glow}20 0%, ${colors.mana.green.glow}15 100%)`,
                border: `1px solid ${colors.gold.dim}40`,
              }}
            >
              <i
                className="ms ms-e"
                style={{ color: colors.gold.standard, fontSize: 16 }}
              />
            </div>
            <div>
              <h1
                className="font-display text-lg tracking-widest leading-tight"
                style={{
                  background: `linear-gradient(135deg, ${colors.gold.standard} 0%, ${colors.mana.green.color} 50%, ${colors.mana.blue.color} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                THE VAULT
              </h1>
              <p
                className="text-xs font-body"
                style={{ color: colors.text.dim }}
              >
                {basicStats.total.toLocaleString()} cards ·{" "}
                {basicStats.unique.toLocaleString()} unique
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {priceRecordStatus && (
              <span
                className="text-[10px] px-2 py-1 rounded"
                style={{
                  background: priceRecordStatus.startsWith("Error")
                    ? `${colors.status.error}20`
                    : `${colors.status.success}20`,
                  color: priceRecordStatus.startsWith("Error")
                    ? colors.status.error
                    : colors.status.success,
                }}
              >
                {priceRecordStatus}
              </span>
            )}
            <button
              onClick={handleRecordPrices}
              disabled={isRecordingPrices || collection.length === 0}
              className="px-3 py-1.5 font-display text-xs tracking-wide rounded-lg transition-all duration-200"
              style={{
                background: colors.void.lighter,
                color:
                  isRecordingPrices || collection.length === 0
                    ? colors.text.muted
                    : colors.text.standard,
                border: `1px solid ${colors.border.standard}`,
                cursor:
                  isRecordingPrices || collection.length === 0
                    ? "not-allowed"
                    : "pointer",
                opacity: isRecordingPrices ? 0.7 : 1,
              }}
            >
              {isRecordingPrices ? "Recording..." : "Record Prices"}
            </button>
            <button
              onClick={() => setIsImportModalOpen(true)}
              className="px-3 py-1.5 font-display text-xs tracking-wide rounded-lg transition-all duration-200 flex items-center gap-1"
              style={{
                background: `linear-gradient(135deg, ${colors.gold.standard} 0%, ${colors.gold.dim} 100%)`,
                color: colors.void.deepest,
              }}
            >
              + Add
            </button>
          </div>
        </div>

        {error && (
          <div
            className="mb-3 p-2 rounded-lg text-xs flex items-center gap-2"
            style={{
              background: `${colors.status.error}15`,
              border: `1px solid ${colors.status.error}30`,
              color: colors.status.error,
            }}
          >
            <i className="ms ms-ability-menace" />
            {error}
          </div>
        )}

        {/* Compact stats row */}
        <div className="flex items-center justify-center gap-6">
          <StatOrb
            label="Value"
            value={
              isPricingLoading
                ? "..."
                : `$${(priceData?.total_value ?? 0).toFixed(0)}`
            }
            icon="e"
            color={colors.gold.bright}
            glow={colors.gold.glow}
          />
          <StatOrb
            label="Unique"
            value={basicStats.unique}
            icon="c"
            color={colors.mana.blue.color}
            glow={colors.mana.blue.glow}
          />
          <StatOrb
            label="Total"
            value={basicStats.total}
            icon="infinity"
            color={colors.mana.green.color}
            glow={colors.mana.green.glow}
          />
          <StatOrb
            label="Foils"
            value={basicStats.foils}
            icon="dfc-spark"
            color={colors.rarity.mythic.color}
            glow={colors.rarity.mythic.glow}
          />
          <StatOrb
            label="Avg CMC"
            value={basicStats.avgCmc.toFixed(1)}
            icon="tap"
            color={colors.text.standard}
          />
        </div>
      </div>

      {/* Search bar */}
      <div
        className="relative z-10 px-4 py-2 border-b flex items-center gap-3"
        style={{
          background: `${colors.void.medium}80`,
          borderColor: colors.border.subtle,
        }}
      >
        <SearchBar
          value={filters.search}
          onChange={(value) => setFilters({ ...filters, search: value })}
          placeholder="Search your vault..."
        />

        {/* Sort dropdown */}
        <div className="relative">
          <select
            value={sortBy}
            onChange={(e) => handleSortChange(e.target.value as SortField)}
            className="appearance-none pl-3 pr-8 py-1.5 text-xs font-display rounded cursor-pointer"
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.subtle}`,
              color: colors.text.standard,
              outline: "none",
            }}
          >
            <optgroup label="Basic">
              {SORT_OPTIONS.filter((o) => o.group === "Basic").map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Card">
              {SORT_OPTIONS.filter((o) => o.group === "Card").map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Gameplay">
              {SORT_OPTIONS.filter((o) => o.group === "Gameplay").map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
          </select>
          {/* Dropdown arrow */}
          <div
            className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
            style={{ color: colors.text.muted }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <path d="M2 3l3 4 3-4H2z" />
            </svg>
          </div>
        </div>

        {/* Sort order toggle */}
        <button
          onClick={() =>
            setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
          }
          className="flex items-center justify-center w-8 h-8 rounded transition-all duration-150"
          style={{
            background: colors.void.lighter,
            border: `1px solid ${colors.border.subtle}`,
            color: colors.text.muted,
          }}
          title={sortOrder === "asc" ? "Ascending" : "Descending"}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{
              transform: sortOrder === "desc" ? "scaleY(-1)" : "none",
              transition: "transform 0.15s ease",
            }}
          >
            <path d="M12 5v14M5 12l7-7 7 7" />
          </svg>
        </button>

        {/* Filter toggle button */}
        <button
          onClick={() => setIsFilterPanelCollapsed(!isFilterPanelCollapsed)}
          className="flex items-center gap-2 px-3 py-1.5 rounded transition-all duration-150"
          style={{
            background: hasActiveFilters(filters)
              ? `${colors.gold.standard}20`
              : colors.void.lighter,
            border: `1px solid ${hasActiveFilters(filters) ? colors.gold.standard : colors.border.subtle}`,
            color: hasActiveFilters(filters)
              ? colors.gold.standard
              : colors.text.muted,
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          <span className="text-xs font-display">Filters</span>
          {hasActiveFilters(filters) && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full"
              style={{
                background: colors.gold.standard,
                color: colors.void.deepest,
              }}
            >
              {filters.rarities.size +
                filters.colors.size +
                filters.types.size +
                filters.sets.size +
                (filters.foilOnly || filters.nonFoilOnly ? 1 : 0) +
                (filters.priceMin !== null || filters.priceMax !== null
                  ? 1
                  : 0)}
            </span>
          )}
        </button>

        <div
          className="text-xs px-2 py-1 rounded"
          style={{
            background: `${colors.mana.blue.color}15`,
            color: colors.mana.blue.color,
          }}
        >
          {filteredCollection.length}/{collection.length}
        </div>

        {/* Analytics toggle button */}
        <button
          onClick={() => setIsAnalyticsSidebarOpen(!isAnalyticsSidebarOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded transition-all duration-150"
          style={{
            background: isAnalyticsSidebarOpen
              ? `${colors.gold.standard}20`
              : colors.void.lighter,
            border: `1px solid ${isAnalyticsSidebarOpen ? colors.gold.standard : colors.border.subtle}`,
            color: isAnalyticsSidebarOpen
              ? colors.gold.standard
              : colors.text.muted,
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
          <span className="text-xs font-display">Analytics</span>
        </button>
      </div>

      {/* Main content area with optional sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Card list */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Comprehensive Filter Panel */}
          <CollectionFilterPanel
            filters={filters}
            onFiltersChange={setFilters}
            stats={
              stats
                ? {
                    colors: stats.colors,
                    types: stats.types,
                    rarities: stats.rarities,
                    topSets: stats.topSets,
                  }
                : null
            }
            totalCards={collection.length}
            filteredCount={filteredCollection.length}
            isCollapsed={isFilterPanelCollapsed}
            onToggleCollapse={() =>
              setIsFilterPanelCollapsed(!isFilterPanelCollapsed)
            }
          />

          {/* List header */}
          <div
            className="relative z-10 flex items-center px-5 py-1.5 text-[10px] font-display uppercase tracking-wider"
            style={{
              background: colors.void.light,
              borderBottom: `1px solid ${colors.border.subtle}`,
              color: colors.text.muted,
            }}
          >
            <div className="w-4" />
            <div className="w-7 text-center">Qty</div>
            <div className="flex-1 pl-2">Card Name</div>
            <div className="w-16 text-right">Price</div>
            <div className="w-8" />
          </div>

          {/* Collection list */}
          <div
            className="relative z-10 flex-1 overflow-y-auto"
            style={{ scrollbarGutter: "stable" }}
          >
            {groupedCards.length === 0 ? (
              <div className="flex items-center justify-center py-16 h-full">
                <div className="text-center">
                  <i
                    className="ms ms-e"
                    style={{
                      fontSize: 56,
                      color: colors.gold.dim,
                      opacity: 0.2,
                    }}
                  />
                  <p
                    className="mt-6 font-display text-lg tracking-wide"
                    style={{ color: colors.text.muted }}
                  >
                    {hasActiveFilters(filters)
                      ? "No cards match your filters"
                      : "Your vault is empty"}
                  </p>
                  {!hasActiveFilters(filters) && (
                    <button
                      onClick={() => setIsImportModalOpen(true)}
                      className="mt-6 px-5 py-2.5 font-display text-sm tracking-wide rounded-lg"
                      style={{
                        background: `linear-gradient(135deg, ${colors.gold.standard} 0%, ${colors.gold.dim} 100%)`,
                        color: colors.void.deepest,
                      }}
                    >
                      Add Your First Cards
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div>
                {groupedCards.map((group) => (
                  <GroupedCardRow
                    key={group.cardName}
                    group={group}
                    priceMap={priceMap}
                    isExpanded={expandedCards.has(group.cardName)}
                    onToggleExpand={() => toggleCardExpanded(group.cardName)}
                    onSelect={handleCardSelect}
                    onEdit={handleCardEdit}
                    selectedCards={selectedCards}
                    onToggleSelection={handleToggleCardSelection}
                    sortBy={sortBy}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Analytics Sidebar */}
        {isAnalyticsSidebarOpen && stats && (
          <div
            className="w-80 border-l flex flex-col overflow-y-auto"
            style={{
              borderColor: colors.border.subtle,
              background: colors.void.deep,
            }}
          >
            <div className="p-3 space-y-3">
              <PriceTiersPanel
                priceData={priceData}
                isLoading={isPricingLoading}
              />
              <ValueOverTimePanel
                valueHistory={valueHistory}
                isLoading={isValueHistoryLoading}
              />
              <TopCardsPanel
                groupedCards={groupedCards}
                isLoading={isPricingLoading}
              />
              <ManaCurvePanel manaCurve={stats.manaCurve} />
              <ColorBreakdownPanel colorData={stats.colors} />
              <RarityCompositionPanel rarities={stats.rarities} />
              <TypeCompositionPanel types={stats.types} />
              <SetsRepresentedPanel topSets={stats.topSets} />
              <TopKeywordsPanel topKeywords={stats.topKeywords ?? []} />
              <LegendariesPanel
                legendaries={
                  stats.legendaries ?? { creatures: 0, other: 0, total: 0 }
                }
              />
              <TopArtistsPanel topArtists={stats.topArtists ?? []} />
            </div>
          </div>
        )}
      </div>

      {/* Import Modal */}
      <CollectionImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
        existingCards={collection}
      />

      {/* Edit Modal */}
      {editingCard && (
        <CollectionEditModal
          card={editingCard}
          onClose={() => setEditingCard(null)}
          onSave={handleCardSave}
          onDelete={handleCardDelete}
        />
      )}

      {/* Card Detail Modal */}
      {viewingCardName && (
        <CardDetailModal
          cardName={viewingCardName}
          setCode={viewingSetCode}
          collectorNumber={viewingCollectorNumber}
          onClose={() => {
            setViewingCardName(null);
            setViewingSetCode(null);
            setViewingCollectorNumber(null);
          }}
        />
      )}

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectedCards.size}
        onAddToDeck={() => setShowBulkDeckSelector(true)}
        onDelete={() => setShowBulkDeleteConfirm(true)}
        onClearSelection={handleClearSelection}
      />

      {/* Bulk Deck Selector */}
      {showBulkDeckSelector && (
        <DeckSelectorDropdown
          onSelect={handleBulkAddToDeck}
          onCancel={() => setShowBulkDeckSelector(false)}
          defaultDeckId={lastSelectedDeckId}
          cardCount={selectedCards.size}
          bulkCards={getSelectedCardsForBulk()}
        />
      )}

      {/* Bulk Delete Confirmation */}
      {showBulkDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0, 0, 0, 0.6)" }}
          onClick={() => setShowBulkDeleteConfirm(false)}
        >
          <div
            className="p-6 rounded-lg max-w-md"
            style={{
              background: colors.void.deep,
              border: `1px solid ${colors.border.standard}`,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3
              className="text-lg font-semibold mb-4"
              style={{ color: colors.text.bright }}
            >
              Delete {selectedCards.size} cards?
            </h3>
            <p className="mb-6" style={{ color: colors.text.dim }}>
              This will remove these cards from your collection. This action
              cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowBulkDeleteConfirm(false)}
                className="px-4 py-2 rounded text-sm"
                style={{
                  background: "transparent",
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.dim,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                className="px-4 py-2 rounded text-sm font-semibold"
                style={{
                  background: colors.status.error,
                  color: colors.void.deepest,
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Action Status */}
      {bulkActionStatus && (
        <div
          className="fixed bottom-20 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 rounded-lg"
          style={{
            background: colors.void.deep,
            border: `1px solid ${colors.border.standard}`,
            color: bulkActionStatus.startsWith("Error")
              ? colors.status.error
              : colors.text.standard,
          }}
        >
          {bulkActionStatus}
        </div>
      )}

      {/* Global animations */}
      <style>{`
        @keyframes constellation-pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        @keyframes star-twinkle {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.3); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default CollectionScreen;
