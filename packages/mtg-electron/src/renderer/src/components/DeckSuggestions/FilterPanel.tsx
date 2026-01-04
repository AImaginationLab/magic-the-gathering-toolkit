/**
 * FilterPanel - Compact horizontal filter bar with multi-select support
 * Features: card source, colors, format, themes (multi), tribals (multi), sets (multi)
 */

import { useState, useEffect, useRef } from "react";
import { colors } from "../../theme";
import type { ReactNode } from "react";
import type { components } from "../../../../shared/types/api-generated";

type SetSummary = components["schemas"]["SetSummary"];

export type CardSource = "collection" | "all";

export interface FilterState {
  cardSource: CardSource;
  selectedDeckId: number | null;
  activeColors: string[];
  archetype: string | null; // Single archetype (deprecated, kept for compat)
  archetypes: string[]; // Multi-select archetypes/themes
  tribal: string | null; // Single tribal (deprecated, kept for compat)
  tribals: string[]; // Multi-select tribals
  setCodes: string[]; // Multi-select sets
  format: string | null;
  ownedOnly: boolean;
}

// Deck summary type for dropdown
interface DeckSummary {
  id: number;
  name: string;
  format: string | null;
  card_count: number;
}

interface FilterPanelProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  onSearch: () => void;
  activeTab?: "suggestions" | "commanders" | "decks";
}

const MANA_COLORS = [
  { code: "W", bg: "#f8f6d8", text: "#1a1a1a", name: "White" },
  { code: "U", bg: "#0e68ab", text: "#ffffff", name: "Blue" },
  { code: "B", bg: "#3a3a3a", text: "#ffffff", name: "Black" },
  { code: "R", bg: "#d3202a", text: "#ffffff", name: "Red" },
  { code: "G", bg: "#00733e", text: "#ffffff", name: "Green" },
];

const FORMATS = [
  { value: "commander", label: "Commander" },
  { value: "standard", label: "Standard" },
  { value: "modern", label: "Modern" },
  { value: "pioneer", label: "Pioneer" },
  { value: "legacy", label: "Legacy" },
  { value: "vintage", label: "Vintage" },
  { value: "pauper", label: "Pauper" },
];

// Multi-select dropdown component
function MultiSelectDropdown({
  label,
  options,
  selected,
  onChange,
  placeholder = "Any",
  maxDisplay = 2,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  maxDisplay?: number;
}): ReactNode {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
        setSearch("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter((opt) =>
    opt.toLowerCase().includes(search.toLowerCase()),
  );

  const toggleOption = (option: string): void => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const displayText =
    selected.length === 0
      ? placeholder
      : selected.length <= maxDisplay
        ? selected.join(", ")
        : `${selected.slice(0, maxDisplay).join(", ")} +${selected.length - maxDisplay}`;

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm" style={{ color: colors.text.muted }}>
        {label}:
      </span>
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="h-8 px-3 text-sm rounded flex items-center gap-2 transition-all"
          style={{
            background: colors.void.lighter,
            border: `1px solid ${isOpen || selected.length > 0 ? colors.gold.dim : colors.border.standard}`,
            color:
              selected.length > 0 ? colors.text.standard : colors.text.muted,
            minWidth: 140,
          }}
        >
          <span className="flex-1 text-left truncate">{displayText}</span>
          <span
            style={{
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.15s ease",
              fontSize: 10,
            }}
          >
            ▼
          </span>
        </button>

        {isOpen && (
          <div
            className="absolute z-50 w-56 mt-1 rounded shadow-lg"
            style={{
              background: colors.void.medium,
              border: `1px solid ${colors.border.standard}`,
              maxHeight: 280,
            }}
          >
            {/* Search input */}
            <div
              className="p-2 border-b"
              style={{ borderColor: colors.border.subtle }}
            >
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search..."
                className="w-full h-7 px-2 text-sm rounded"
                style={{
                  background: colors.void.lighter,
                  border: `1px solid ${colors.border.subtle}`,
                  color: colors.text.standard,
                  outline: "none",
                }}
                autoFocus
              />
            </div>

            {/* Selected count and clear */}
            {selected.length > 0 && (
              <div
                className="px-3 py-1.5 flex items-center justify-between border-b"
                style={{
                  borderColor: colors.border.subtle,
                  background: colors.void.light,
                }}
              >
                <span
                  className="text-xs"
                  style={{ color: colors.gold.standard }}
                >
                  {selected.length} selected
                </span>
                <button
                  onClick={() => onChange([])}
                  className="text-xs"
                  style={{ color: colors.text.muted }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.color = colors.text.standard)
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.color = colors.text.muted)
                  }
                >
                  Clear
                </button>
              </div>
            )}

            {/* Options list */}
            <div className="overflow-auto" style={{ maxHeight: 200 }}>
              {filteredOptions.length === 0 ? (
                <div
                  className="px-3 py-2 text-sm"
                  style={{ color: colors.text.muted }}
                >
                  No options found
                </div>
              ) : (
                filteredOptions.map((option) => {
                  const isSelected = selected.includes(option);
                  return (
                    <button
                      key={option}
                      onClick={() => toggleOption(option)}
                      className="w-full px-3 py-1.5 text-sm text-left flex items-center gap-2 transition-colors"
                      style={{
                        color: isSelected
                          ? colors.gold.standard
                          : colors.text.dim,
                        background: isSelected
                          ? colors.void.light
                          : "transparent",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected)
                          e.currentTarget.style.background = colors.void.light;
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected)
                          e.currentTarget.style.background = "transparent";
                      }}
                    >
                      <span
                        className="w-4 h-4 rounded border flex items-center justify-center text-xs"
                        style={{
                          borderColor: isSelected
                            ? colors.gold.standard
                            : colors.border.subtle,
                          background: isSelected
                            ? colors.gold.standard
                            : "transparent",
                          color: isSelected
                            ? colors.void.deepest
                            : "transparent",
                        }}
                      >
                        ✓
                      </span>
                      <span>{option}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function FilterPanel({
  filters,
  onChange,
  onSearch,
  activeTab = "suggestions",
}: FilterPanelProps): ReactNode {
  // API-loaded filter options
  const [themeOptions, setThemeOptions] = useState<string[]>([]);
  const [tribalOptions, setTribalOptions] = useState<string[]>([]);
  const [setOptions, setSetOptions] = useState<SetSummary[]>([]);
  const [deckOptions, setDeckOptions] = useState<DeckSummary[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);

  // Load filter options from API
  useEffect(() => {
    const loadOptions = async (): Promise<void> => {
      try {
        const [filterOpts, setsResult, decksResult] = await Promise.all([
          window.electronAPI.api.recommendations.getFilterOptions(),
          window.electronAPI.sets.list(),
          window.electronAPI.decks.list(),
        ]);
        setThemeOptions(filterOpts.themes);
        setTribalOptions(filterOpts.tribals);
        // Exclude non-playable sets (tokens, promos, art series, memorabilia)
        const excludedTypes = new Set([
          "token",
          "promo",
          "memorabilia",
          "minigame",
          "funny",
          "vanguard",
          "treasure_chest",
        ]);
        const filteredSets = setsResult.sets.filter(
          (s: SetSummary) => s.type && !excludedTypes.has(s.type),
        );
        setSetOptions(filteredSets);
        setDeckOptions(decksResult || []);
      } catch (err) {
        console.error("Failed to load filter options:", err);
      } finally {
        setIsLoadingOptions(false);
      }
    };
    loadOptions();
  }, []);

  const handleSourceChange = (source: CardSource): void => {
    onChange({ ...filters, cardSource: source, selectedDeckId: null });
  };

  const handleDeckChange = (deckId: number | null): void => {
    onChange({ ...filters, selectedDeckId: deckId });
  };

  const toggleColor = (code: string): void => {
    const newColors = filters.activeColors.includes(code)
      ? filters.activeColors.filter((c) => c !== code)
      : [...filters.activeColors, code];
    onChange({ ...filters, activeColors: newColors });
  };

  const hasActiveFilters =
    filters.activeColors.length > 0 ||
    filters.archetypes.length > 0 ||
    filters.tribals.length > 0 ||
    filters.setCodes.length > 0 ||
    filters.format !== null;

  const clearAllFilters = (): void => {
    onChange({
      ...filters,
      activeColors: [],
      archetype: null,
      archetypes: [],
      tribal: null,
      tribals: [],
      setCodes: [],
      format: null,
    });
  };

  // Format set options for dropdown (code - name)
  const setDisplayOptions = setOptions.map(
    (s) => `${s.code.toUpperCase()} - ${s.name}`,
  );
  const setCodeMap = new Map(
    setOptions.map((s) => [`${s.code.toUpperCase()} - ${s.name}`, s.code]),
  );
  const reverseSetCodeMap = new Map(
    setOptions.map((s) => [s.code, `${s.code.toUpperCase()} - ${s.name}`]),
  );

  return (
    <div
      className="px-6 py-4 border-b"
      style={{
        background: colors.void.deep,
        borderColor: colors.border.subtle,
      }}
    >
      {/* Row 1: Source + Colors */}
      <div className="flex items-center gap-6 mb-4">
        {/* Card Source - Show deck dropdown only on suggestions tab */}
        {activeTab === "suggestions" ? (
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: colors.text.muted }}>
              Suggest for:
            </span>
            <select
              value={filters.selectedDeckId ?? ""}
              onChange={(e) => {
                const val = e.target.value;
                handleDeckChange(val ? parseInt(val, 10) : null);
              }}
              className="h-8 px-3 text-sm rounded cursor-pointer"
              style={{
                background: colors.void.lighter,
                border: `1px solid ${filters.selectedDeckId ? colors.gold.dim : colors.border.standard}`,
                color: filters.selectedDeckId
                  ? colors.text.standard
                  : colors.text.muted,
                minWidth: 180,
              }}
            >
              <option value="">Select a deck...</option>
              {deckOptions.map((deck) => (
                <option key={deck.id} value={deck.id}>
                  {deck.name} ({deck.card_count} cards)
                </option>
              ))}
            </select>

            {/* Source toggle for suggestions */}
            <div
              className="flex rounded-lg overflow-hidden ml-2"
              style={{ border: `1px solid ${colors.border.standard}` }}
            >
              <button
                onClick={() => handleSourceChange("collection")}
                className="px-3 py-1.5 text-xs font-medium transition-colors"
                style={{
                  background:
                    filters.cardSource === "collection"
                      ? colors.gold.standard
                      : colors.void.medium,
                  color:
                    filters.cardSource === "collection"
                      ? colors.void.deepest
                      : colors.text.dim,
                }}
                title="Suggest cards from your collection"
              >
                From Collection
              </button>
              <button
                onClick={() => handleSourceChange("all")}
                className="px-3 py-1.5 text-xs font-medium transition-colors"
                style={{
                  background:
                    filters.cardSource === "all"
                      ? colors.gold.standard
                      : colors.void.medium,
                  color:
                    filters.cardSource === "all"
                      ? colors.void.deepest
                      : colors.text.dim,
                  borderLeft: `1px solid ${colors.border.standard}`,
                }}
                title="Suggest any cards (not just owned)"
              >
                All Cards
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: colors.text.muted }}>
              Source:
            </span>
            <div
              className="flex rounded-lg overflow-hidden"
              style={{ border: `1px solid ${colors.border.standard}` }}
            >
              <button
                onClick={() => handleSourceChange("collection")}
                className="px-4 py-2 text-sm font-medium transition-colors"
                style={{
                  background:
                    filters.cardSource === "collection"
                      ? colors.gold.standard
                      : colors.void.medium,
                  color:
                    filters.cardSource === "collection"
                      ? colors.void.deepest
                      : colors.text.dim,
                }}
              >
                My Collection
              </button>
              <button
                onClick={() => handleSourceChange("all")}
                className="px-4 py-2 text-sm font-medium transition-colors"
                style={{
                  background:
                    filters.cardSource === "all"
                      ? colors.gold.standard
                      : colors.void.medium,
                  color:
                    filters.cardSource === "all"
                      ? colors.void.deepest
                      : colors.text.dim,
                  borderLeft: `1px solid ${colors.border.standard}`,
                }}
              >
                All Cards
              </button>
            </div>
          </div>
        )}

        {/* Vertical divider */}
        <div
          className="h-8 w-px"
          style={{ background: colors.border.subtle }}
        />

        {/* Color Filters */}
        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: colors.text.muted }}>
            Colors:
          </span>
          <div className="flex gap-1">
            {MANA_COLORS.map((mana) => {
              const isActive = filters.activeColors.includes(mana.code);
              return (
                <button
                  key={mana.code}
                  onClick={() => toggleColor(mana.code)}
                  className="w-8 h-8 rounded flex items-center justify-center text-sm font-bold transition-all"
                  style={{
                    background: isActive ? mana.bg : colors.void.medium,
                    color: isActive ? mana.text : colors.text.muted,
                    border: `2px solid ${isActive ? mana.bg : colors.border.subtle}`,
                    transform: isActive ? "scale(1.1)" : "scale(1)",
                  }}
                  title={mana.name}
                >
                  {mana.code}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Row 2: Format, Themes, Tribals, Sets, Clear, Search */}
      <div className="flex items-center gap-4 flex-wrap">
        {/* Format */}
        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: colors.text.muted }}>
            Format:
          </span>
          <select
            value={filters.format ?? ""}
            onChange={(e) =>
              onChange({ ...filters, format: e.target.value || null })
            }
            className="h-8 px-3 text-sm rounded cursor-pointer"
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.standard}`,
              color: colors.text.standard,
              minWidth: 120,
            }}
          >
            <option value="">Any</option>
            {FORMATS.map((fmt) => (
              <option key={fmt.value} value={fmt.value}>
                {fmt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Themes (multi-select) */}
        {!isLoadingOptions && themeOptions.length > 0 && (
          <MultiSelectDropdown
            label="Themes"
            options={themeOptions}
            selected={filters.archetypes}
            onChange={(archetypes) => onChange({ ...filters, archetypes })}
            placeholder="Any"
            maxDisplay={2}
          />
        )}

        {/* Tribals (multi-select) */}
        {!isLoadingOptions && tribalOptions.length > 0 && (
          <MultiSelectDropdown
            label="Tribals"
            options={tribalOptions}
            selected={filters.tribals}
            onChange={(tribals) => onChange({ ...filters, tribals })}
            placeholder="Any"
            maxDisplay={2}
          />
        )}

        {/* Sets (multi-select) */}
        {!isLoadingOptions && setOptions.length > 0 && (
          <MultiSelectDropdown
            label="Sets"
            options={setDisplayOptions}
            selected={filters.setCodes.map(
              (code) => reverseSetCodeMap.get(code) ?? code,
            )}
            onChange={(displayValues) => {
              const codes = displayValues.map((dv) => setCodeMap.get(dv) ?? dv);
              onChange({ ...filters, setCodes: codes });
            }}
            placeholder="Any"
            maxDisplay={1}
          />
        )}

        {/* Clear filters */}
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="px-3 py-1.5 rounded text-sm transition-colors"
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.subtle}`,
              color: colors.text.muted,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = colors.gold.dim;
              e.currentTarget.style.color = colors.gold.standard;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = colors.border.subtle;
              e.currentTarget.style.color = colors.text.muted;
            }}
          >
            Clear
          </button>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search button */}
        <button
          onClick={onSearch}
          className="px-5 py-1.5 rounded text-sm font-medium transition-colors"
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
          Search
        </button>
      </div>
    </div>
  );
}

export default FilterPanel;
