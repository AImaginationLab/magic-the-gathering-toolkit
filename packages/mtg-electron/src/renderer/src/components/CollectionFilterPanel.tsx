/**
 * CollectionFilterPanel - Comprehensive filtering for the collection view
 *
 * Provides filters for: rarity, colors, card types, sets, price ranges,
 * and foil status with Arcane-style aesthetics.
 */
import { useState, useCallback, useMemo } from "react";

import { colors } from "../theme";

import type { ReactNode } from "react";

// Filter state interface
export interface CollectionFilters {
  search: string;
  rarities: Set<string>;
  colors: Set<string>;
  types: Set<string>;
  sets: Set<string>;
  priceMin: number | null;
  priceMax: number | null;
  foilOnly: boolean;
  nonFoilOnly: boolean;
}

// Stats for populating filter options
export interface FilterStats {
  colors: Record<string, number>;
  types: Record<string, number>;
  rarities: Record<string, number>;
  topSets: Array<{ code: string; count: number }>;
}

interface CollectionFilterPanelProps {
  filters: CollectionFilters;
  onFiltersChange: (filters: CollectionFilters) => void;
  stats: FilterStats | null;
  totalCards: number;
  filteredCount: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

// Create empty filters
export function createEmptyFilters(): CollectionFilters {
  return {
    search: "",
    rarities: new Set(),
    colors: new Set(),
    types: new Set(),
    sets: new Set(),
    priceMin: null,
    priceMax: null,
    foilOnly: false,
    nonFoilOnly: false,
  };
}

// Check if any filters are active
export function hasActiveFilters(filters: CollectionFilters): boolean {
  return (
    filters.search.length > 0 ||
    filters.rarities.size > 0 ||
    filters.colors.size > 0 ||
    filters.types.size > 0 ||
    filters.sets.size > 0 ||
    filters.priceMin !== null ||
    filters.priceMax !== null ||
    filters.foilOnly ||
    filters.nonFoilOnly
  );
}

// Filter section header
function SectionHeader({
  title,
  icon,
  count,
}: {
  title: string;
  icon: string;
  count?: number;
}): ReactNode {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span style={{ fontSize: 12 }}>{icon}</span>
      <span
        className="text-xs font-display uppercase tracking-wider"
        style={{ color: colors.gold.standard }}
      >
        {title}
      </span>
      {count !== undefined && count > 0 && (
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full"
          style={{
            background: `${colors.gold.standard}20`,
            color: colors.gold.standard,
          }}
        >
          {count}
        </span>
      )}
    </div>
  );
}

// Toggle chip component
function FilterChip({
  label,
  isActive,
  onClick,
  color,
  icon,
  count,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
  color?: string;
  icon?: ReactNode;
  count?: number;
}): ReactNode {
  const chipColor = color || colors.gold.muted;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm font-medium transition-all duration-150"
      style={{
        background: isActive ? `${chipColor}25` : colors.void.lighter,
        border: `1px solid ${isActive ? chipColor : colors.border.subtle}`,
        color: isActive ? chipColor : colors.text.standard,
      }}
    >
      {icon}
      <span>{label}</span>
      {count !== undefined && (
        <span
          className="text-xs font-semibold tabular-nums"
          style={{
            color: isActive ? chipColor : colors.text.dim,
            opacity: isActive ? 1 : 0.8,
          }}
        >
          {count.toLocaleString()}
        </span>
      )}
    </button>
  );
}

// Rarity configuration
const RARITY_CONFIG = [
  {
    key: "mythic",
    label: "Mythic",
    color: colors.rarity.mythic.color,
    icon: "★",
  },
  { key: "rare", label: "Rare", color: colors.rarity.rare.color, icon: "◆" },
  {
    key: "uncommon",
    label: "Uncommon",
    color: colors.rarity.uncommon.color,
    icon: "●",
  },
  {
    key: "common",
    label: "Common",
    color: colors.rarity.common.color,
    icon: "○",
  },
];

// Color configuration with mana symbols
const COLOR_CONFIG = [
  { key: "W", label: "White", color: colors.mana.white.color, icon: "ms-w" },
  { key: "U", label: "Blue", color: colors.mana.blue.color, icon: "ms-u" },
  { key: "B", label: "Black", color: colors.mana.black.color, icon: "ms-b" },
  { key: "R", label: "Red", color: colors.mana.red.color, icon: "ms-r" },
  { key: "G", label: "Green", color: colors.mana.green.color, icon: "ms-g" },
  { key: "C", label: "Colorless", color: "#bab1ab", icon: "ms-c" },
];

// Type icons
const TYPE_ICONS: Record<string, string> = {
  Creature: "🐉",
  Instant: "⚡",
  Sorcery: "🌟",
  Enchantment: "✨",
  Artifact: "⚙️",
  Land: "🏔️",
  Planeswalker: "👤",
};

// Price range presets
const PRICE_PRESETS = [
  { label: "< $1", min: null, max: 1 },
  { label: "$1-5", min: 1, max: 5 },
  { label: "$5-20", min: 5, max: 20 },
  { label: "$20+", min: 20, max: null },
];

export function CollectionFilterPanel({
  filters,
  onFiltersChange,
  stats,
  totalCards,
  filteredCount,
  isCollapsed = false,
  onToggleCollapse,
}: CollectionFilterPanelProps): ReactNode {
  const [showAllSets, setShowAllSets] = useState(false);

  // Toggle helpers
  const toggleSet = useCallback(
    <K extends keyof CollectionFilters>(key: K, value: string) => {
      if (filters[key] instanceof Set) {
        const newSet = new Set(filters[key] as Set<string>);
        if (newSet.has(value)) {
          newSet.delete(value);
        } else {
          newSet.add(value);
        }
        onFiltersChange({ ...filters, [key]: newSet });
      }
    },
    [filters, onFiltersChange],
  );

  const toggleBoolean = useCallback(
    (key: "foilOnly" | "nonFoilOnly") => {
      // Mutually exclusive toggles
      if (key === "foilOnly") {
        onFiltersChange({
          ...filters,
          foilOnly: !filters.foilOnly,
          nonFoilOnly: false,
        });
      } else {
        onFiltersChange({
          ...filters,
          nonFoilOnly: !filters.nonFoilOnly,
          foilOnly: false,
        });
      }
    },
    [filters, onFiltersChange],
  );

  const setPriceRange = useCallback(
    (min: number | null, max: number | null) => {
      // Toggle off if same range is clicked
      if (filters.priceMin === min && filters.priceMax === max) {
        onFiltersChange({ ...filters, priceMin: null, priceMax: null });
      } else {
        onFiltersChange({ ...filters, priceMin: min, priceMax: max });
      }
    },
    [filters, onFiltersChange],
  );

  const clearFilters = useCallback(() => {
    onFiltersChange(createEmptyFilters());
  }, [onFiltersChange]);

  // Sorted sets by card count
  const sortedSets = useMemo(() => {
    if (!stats?.topSets) return [];
    return [...stats.topSets].sort((a, b) => b.count - a.count);
  }, [stats?.topSets]);

  const displayedSets = showAllSets ? sortedSets : sortedSets.slice(0, 8);

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.rarities.size > 0) count += filters.rarities.size;
    if (filters.colors.size > 0) count += filters.colors.size;
    if (filters.types.size > 0) count += filters.types.size;
    if (filters.sets.size > 0) count += filters.sets.size;
    if (filters.priceMin !== null || filters.priceMax !== null) count += 1;
    if (filters.foilOnly || filters.nonFoilOnly) count += 1;
    return count;
  }, [filters]);

  const hasFilters = hasActiveFilters(filters);

  if (isCollapsed) {
    return (
      <div
        className="px-4 py-2 flex items-center justify-between cursor-pointer transition-colors duration-150"
        style={{
          background: colors.void.medium,
          borderBottom: `1px solid ${colors.border.subtle}`,
        }}
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-3">
          <span style={{ color: colors.gold.standard }}>▼</span>
          <span
            className="text-xs font-display uppercase tracking-wider"
            style={{ color: colors.text.muted }}
          >
            Filters
          </span>
          {activeFilterCount > 0 && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full"
              style={{
                background: `${colors.gold.standard}20`,
                color: colors.gold.standard,
              }}
            >
              {activeFilterCount} active
            </span>
          )}
        </div>
        <span className="text-xs" style={{ color: colors.mana.blue.color }}>
          {filteredCount}/{totalCards}
        </span>
      </div>
    );
  }

  return (
    <div
      className="px-4 py-3 overflow-y-auto"
      style={{
        background: `linear-gradient(180deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
        borderBottom: `1px solid ${colors.border.subtle}`,
        maxHeight: "45vh",
      }}
    >
      {/* Header with collapse toggle - animated gradient background */}
      <div
        className="flex items-center justify-between mb-3 -mx-4 -mt-3 px-4 py-2 relative overflow-hidden"
        style={{
          borderBottom: `1px solid ${colors.border.subtle}`,
        }}
      >
        {/* Animated gradient background */}
        <div
          className="absolute inset-0"
          style={{
            background: `linear-gradient(90deg, ${colors.gold.standard}15, ${colors.mana.blue.color}15, ${colors.mana.red.color}15, ${colors.gold.standard}15)`,
            backgroundSize: "300% 100%",
            animation: "gradient-shift 8s linear infinite",
          }}
        />
        <div
          className="flex items-center gap-3 cursor-pointer relative z-10"
          onClick={onToggleCollapse}
        >
          <span style={{ color: colors.gold.standard }}>▲</span>
          <span
            className="text-sm font-display uppercase tracking-wider font-semibold"
            style={{ color: colors.gold.standard }}
          >
            Filters
          </span>
          {activeFilterCount > 0 && (
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{
                background: `${colors.gold.standard}30`,
                color: colors.gold.standard,
              }}
            >
              {activeFilterCount} active
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 relative z-10">
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs px-2.5 py-1 rounded transition-colors duration-150 font-medium"
              style={{
                background: `${colors.status.error}20`,
                color: colors.status.error,
                border: `1px solid ${colors.status.error}40`,
              }}
            >
              Clear All
            </button>
          )}
          <span
            className="text-sm px-2.5 py-1 rounded font-semibold"
            style={{
              background: `${colors.mana.blue.color}20`,
              color: colors.mana.blue.color,
            }}
          >
            {filteredCount.toLocaleString()}/{totalCards.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Filter grid - 2 rows */}
      <div className="space-y-3">
        {/* Row 1: Rarity, Colors, Foil */}
        <div className="grid grid-cols-3 gap-4">
          {/* Rarity */}
          <div>
            <SectionHeader
              title="Rarity"
              icon="💎"
              count={filters.rarities.size}
            />
            <div className="flex flex-wrap gap-1.5">
              {RARITY_CONFIG.map(({ key, label, color, icon }) => (
                <FilterChip
                  key={key}
                  label={label}
                  isActive={filters.rarities.has(key)}
                  onClick={() => toggleSet("rarities", key)}
                  color={color}
                  icon={<span style={{ fontSize: 14, color }}>{icon}</span>}
                  count={stats?.rarities?.[label]}
                />
              ))}
            </div>
          </div>

          {/* Colors */}
          <div>
            <SectionHeader
              title="Colors"
              icon="🎨"
              count={filters.colors.size}
            />
            <div className="flex flex-wrap gap-1.5">
              {COLOR_CONFIG.map(({ key, label, color, icon }) => (
                <FilterChip
                  key={key}
                  label={label}
                  isActive={filters.colors.has(key)}
                  onClick={() => toggleSet("colors", key)}
                  color={color}
                  icon={
                    <i
                      className={`ms ${icon} ms-cost`}
                      style={{ fontSize: 14 }}
                    />
                  }
                  count={stats?.colors?.[key]}
                />
              ))}
            </div>
          </div>

          {/* Foil */}
          <div>
            <SectionHeader title="Foil Status" icon="✨" />
            <div className="flex flex-wrap gap-1.5">
              <FilterChip
                label="Foils Only"
                isActive={filters.foilOnly}
                onClick={() => toggleBoolean("foilOnly")}
                color="#b86fce"
                icon={<span style={{ fontSize: 10 }}>✨</span>}
              />
              <FilterChip
                label="Non-Foil Only"
                isActive={filters.nonFoilOnly}
                onClick={() => toggleBoolean("nonFoilOnly")}
              />
            </div>
          </div>
        </div>

        {/* Row 2: Types, Price */}
        <div className="grid grid-cols-3 gap-4">
          {/* Types */}
          <div>
            <SectionHeader title="Types" icon="📋" count={filters.types.size} />
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(TYPE_ICONS).map(([typeName, icon]) => (
                <FilterChip
                  key={typeName}
                  label={typeName}
                  isActive={filters.types.has(typeName)}
                  onClick={() => toggleSet("types", typeName)}
                  icon={<span style={{ fontSize: 10 }}>{icon}</span>}
                  count={stats?.types?.[typeName]}
                />
              ))}
            </div>
          </div>

          {/* Price */}
          <div>
            <SectionHeader title="Price" icon="💰" />
            <div className="flex flex-wrap gap-1.5">
              {PRICE_PRESETS.map(({ label, min, max }) => (
                <FilterChip
                  key={label}
                  label={label}
                  isActive={
                    filters.priceMin === min && filters.priceMax === max
                  }
                  onClick={() => setPriceRange(min, max)}
                  color={colors.gold.standard}
                  icon={<span style={{ fontSize: 14 }}>💵</span>}
                />
              ))}
            </div>
          </div>

          {/* Empty cell for grid alignment */}
          <div />
        </div>
      </div>

      {/* Sets row (below the grid) */}
      {sortedSets.length > 0 && (
        <div
          className="mt-3 pt-3"
          style={{ borderTop: `1px solid ${colors.border.subtle}` }}
        >
          <SectionHeader title="Sets" icon="📦" count={filters.sets.size} />
          <div className="flex flex-wrap gap-1.5">
            {displayedSets.map(({ code, count }) => (
              <FilterChip
                key={code}
                label={code.toUpperCase()}
                isActive={filters.sets.has(code)}
                onClick={() => toggleSet("sets", code)}
                icon={
                  <i
                    className={`ss ss-${code.toLowerCase()} ss-grad ss-mythic`}
                    style={{ fontSize: 14 }}
                  />
                }
                count={count}
              />
            ))}
            {sortedSets.length > 8 && (
              <button
                onClick={() => setShowAllSets(!showAllSets)}
                className="text-[10px] px-2 py-1 rounded transition-colors duration-150"
                style={{
                  background: colors.void.lighter,
                  color: colors.text.muted,
                  border: `1px solid ${colors.border.subtle}`,
                }}
              >
                {showAllSets ? "Show Less" : `+${sortedSets.length - 8} more`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default CollectionFilterPanel;
