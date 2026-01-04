/**
 * SearchFilters - Visual filter bar for card search
 * Complements the text-based search with clickable filter options
 */

import { useState, useEffect, useRef } from "react";
import { colors } from "../theme";
import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

type SetSummary = components["schemas"]["SetSummary"];

export interface SearchFilterState {
  colors: string[];
  setCodes: string[];
  format: string | null;
  rarity: string | null;
  type: string | null;
}

interface SearchFiltersProps {
  filters: SearchFilterState;
  onChange: (filters: SearchFilterState) => void;
  collapsed?: boolean;
}

const MANA_COLORS = [
  { code: "W", bg: "#f8f6d8", text: "#1a1a1a", name: "White" },
  { code: "U", bg: "#0e68ab", text: "#ffffff", name: "Blue" },
  { code: "B", bg: "#3a3a3a", text: "#ffffff", name: "Black" },
  { code: "R", bg: "#d3202a", text: "#ffffff", name: "Red" },
  { code: "G", bg: "#00733e", text: "#ffffff", name: "Green" },
  { code: "C", bg: "#bab1ab", text: "#1a1a1a", name: "Colorless" },
];

const FORMATS = [
  { value: "standard", label: "Standard" },
  { value: "modern", label: "Modern" },
  { value: "pioneer", label: "Pioneer" },
  { value: "legacy", label: "Legacy" },
  { value: "vintage", label: "Vintage" },
  { value: "commander", label: "Commander" },
  { value: "pauper", label: "Pauper" },
];

const RARITIES = [
  { value: "common", label: "Common", color: "#888888" },
  { value: "uncommon", label: "Uncommon", color: "#c0c0c0" },
  { value: "rare", label: "Rare", color: "#c9a227" },
  { value: "mythic", label: "Mythic", color: "#e65c00" },
];

const TYPES = [
  "Creature",
  "Instant",
  "Sorcery",
  "Enchantment",
  "Artifact",
  "Planeswalker",
  "Land",
];

// Single-select dropdown component
function Dropdown({
  value,
  options,
  placeholder,
  onChange,
}: {
  value: string | null;
  options: Array<{ value: string; label: string }>;
  placeholder: string;
  onChange: (value: string | null) => void;
}): ReactNode {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedOption = options.find((o) => o.value === value);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="h-7 px-2 text-xs rounded flex items-center gap-1.5 transition-all min-w-[70px]"
        style={{
          background: colors.void.lighter,
          border: `1px solid ${isOpen || value ? colors.gold.dim : colors.border.subtle}`,
          color: value ? colors.text.standard : colors.text.muted,
        }}
      >
        <span className="flex-1 text-left">
          {selectedOption?.label || placeholder}
        </span>
        <span
          style={{
            fontSize: 8,
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
          }}
        >
          ▼
        </span>
      </button>

      {isOpen && (
        <div
          className="absolute z-50 w-full mt-1 rounded shadow-lg"
          style={{
            background: colors.void.medium,
            border: `1px solid ${colors.border.standard}`,
            minWidth: "100px",
          }}
        >
          <button
            onClick={() => {
              onChange(null);
              setIsOpen(false);
            }}
            className="w-full px-2 py-1.5 text-xs text-left transition-colors"
            style={{
              color: !value ? colors.gold.standard : colors.text.dim,
              background: !value ? colors.void.light : "transparent",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = colors.void.light)
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = !value
                ? colors.void.light
                : "transparent")
            }
          >
            {placeholder}
          </button>
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                onChange(opt.value);
                setIsOpen(false);
              }}
              className="w-full px-2 py-1.5 text-xs text-left transition-colors"
              style={{
                color:
                  value === opt.value ? colors.gold.standard : colors.text.dim,
                background:
                  value === opt.value ? colors.void.light : "transparent",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = colors.void.light)
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background =
                  value === opt.value ? colors.void.light : "transparent")
              }
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Multi-select dropdown for sets
function SetMultiSelect({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (codes: string[]) => void;
}): ReactNode {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [sets, setSets] = useState<SetSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load sets on mount
  useEffect(() => {
    let cancelled = false;

    const loadSets = async (): Promise<void> => {
      try {
        const result = await window.electronAPI.sets.list();
        if (cancelled) return;
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
        const filtered = result.sets.filter(
          (s: SetSummary) => s.type && !excludedTypes.has(s.type),
        );
        setSets(filtered);
      } catch (err) {
        if (!cancelled) {
          console.error("Failed to load sets:", err);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    loadSets();

    return () => {
      cancelled = true;
    };
  }, []);

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

  const filteredSets = sets.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.code.toLowerCase().includes(search.toLowerCase()),
  );

  const toggleSet = (code: string): void => {
    if (selected.includes(code)) {
      onChange(selected.filter((c) => c !== code));
    } else {
      onChange([...selected, code]);
    }
  };

  const displayText =
    selected.length === 0
      ? "Any Set"
      : selected.length === 1
        ? selected[0].toUpperCase()
        : `${selected.length} sets`;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="h-7 px-2 text-xs rounded flex items-center gap-1.5 transition-all"
        style={{
          background: colors.void.lighter,
          border: `1px solid ${isOpen || selected.length > 0 ? colors.gold.dim : colors.border.subtle}`,
          color: selected.length > 0 ? colors.text.standard : colors.text.muted,
        }}
      >
        <span>{displayText}</span>
        <span style={{ fontSize: 8 }}>▼</span>
      </button>

      {isOpen && (
        <div
          className="absolute z-50 w-52 mt-1 rounded shadow-lg"
          style={{
            background: colors.void.medium,
            border: `1px solid ${colors.border.standard}`,
          }}
        >
          <div
            className="p-2 border-b"
            style={{ borderColor: colors.border.subtle }}
          >
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sets..."
              className="w-full h-6 px-2 text-xs rounded"
              style={{
                background: colors.void.lighter,
                border: `1px solid ${colors.border.subtle}`,
                color: colors.text.standard,
                outline: "none",
              }}
              autoFocus
            />
          </div>

          {selected.length > 0 && (
            <div
              className="px-2 py-1 flex items-center justify-between border-b"
              style={{
                borderColor: colors.border.subtle,
                background: colors.void.light,
              }}
            >
              <span className="text-xs" style={{ color: colors.gold.standard }}>
                {selected.length} selected
              </span>
              <button
                onClick={() => onChange([])}
                className="text-xs"
                style={{ color: colors.text.muted }}
              >
                Clear
              </button>
            </div>
          )}

          <div className="overflow-auto" style={{ maxHeight: 180 }}>
            {isLoading ? (
              <div
                className="px-2 py-2 text-xs"
                style={{ color: colors.text.muted }}
              >
                Loading...
              </div>
            ) : filteredSets.length === 0 ? (
              <div
                className="px-2 py-2 text-xs"
                style={{ color: colors.text.muted }}
              >
                No sets found
              </div>
            ) : (
              filteredSets.slice(0, 50).map((set) => {
                const isSelected = selected.includes(set.code);
                return (
                  <button
                    key={set.code}
                    onClick={() => toggleSet(set.code)}
                    className="w-full px-2 py-1 text-xs text-left flex items-center gap-2 transition-colors"
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
                    <i
                      className={`ss ss-${set.code.toLowerCase()}`}
                      style={{ fontSize: 12 }}
                    />
                    <span className="flex-1 truncate">{set.name}</span>
                    <span style={{ color: colors.text.muted }}>
                      {set.code.toUpperCase()}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function SearchFilters({
  filters,
  onChange,
  collapsed = false,
}: SearchFiltersProps): ReactNode {
  if (collapsed) return null;

  const toggleColor = (code: string): void => {
    const newColors = filters.colors.includes(code)
      ? filters.colors.filter((c) => c !== code)
      : [...filters.colors, code];
    onChange({ ...filters, colors: newColors });
  };

  const hasActiveFilters =
    filters.colors.length > 0 ||
    filters.setCodes.length > 0 ||
    filters.format !== null ||
    filters.rarity !== null ||
    filters.type !== null;

  const clearAll = (): void => {
    onChange({
      colors: [],
      setCodes: [],
      format: null,
      rarity: null,
      type: null,
    });
  };

  return (
    <div
      className="flex items-center gap-4 flex-wrap py-2"
      style={{ borderTop: `1px solid ${colors.border.subtle}` }}
    >
      {/* Colors */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Colors:
        </span>
        <div className="flex gap-0.5">
          {MANA_COLORS.map((mana) => {
            const isActive = filters.colors.includes(mana.code);
            return (
              <button
                key={mana.code}
                onClick={() => toggleColor(mana.code)}
                className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold transition-all"
                style={{
                  background: isActive ? mana.bg : colors.void.medium,
                  color: isActive ? mana.text : colors.text.muted,
                  border: `1px solid ${isActive ? mana.bg : colors.border.subtle}`,
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

      {/* Sets */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Set:
        </span>
        <SetMultiSelect
          selected={filters.setCodes}
          onChange={(setCodes) => onChange({ ...filters, setCodes })}
        />
      </div>

      {/* Format */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Format:
        </span>
        <Dropdown
          value={filters.format}
          options={FORMATS}
          placeholder="Any"
          onChange={(format) => onChange({ ...filters, format })}
        />
      </div>

      {/* Rarity */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Rarity:
        </span>
        <div className="flex gap-0.5">
          {RARITIES.map((r) => {
            const isActive = filters.rarity === r.value;
            return (
              <button
                key={r.value}
                onClick={() =>
                  onChange({
                    ...filters,
                    rarity: isActive ? null : r.value,
                  })
                }
                className="px-2 h-6 rounded text-xs transition-all"
                style={{
                  background: isActive ? r.color + "30" : colors.void.medium,
                  color: isActive ? r.color : colors.text.muted,
                  border: `1px solid ${isActive ? r.color : colors.border.subtle}`,
                }}
                title={r.label}
              >
                {r.label[0]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Type */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs" style={{ color: colors.text.muted }}>
          Type:
        </span>
        <Dropdown
          value={filters.type}
          options={TYPES.map((t) => ({ value: t, label: t }))}
          placeholder="Any"
          onChange={(type) => onChange({ ...filters, type })}
        />
      </div>

      {/* Clear all */}
      {hasActiveFilters && (
        <button
          onClick={clearAll}
          className="px-2 py-1 rounded text-xs transition-colors"
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
    </div>
  );
}

export default SearchFilters;
