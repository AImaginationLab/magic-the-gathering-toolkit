/**
 * TribalFilter - Creature type filter with dropdown and collection-based smart chips
 */

import { useState } from "react";
import { colors, synergyColors } from "../../theme";
import type { ReactNode } from "react";

interface TribalFilterProps {
  selected: string | null;
  onChange: (tribal: string | null) => void;
  collectionCounts?: Record<string, number>; // creature type -> count in collection
}

const TRIBAL_TYPES = [
  "Angel",
  "Artifact",
  "Beast",
  "Bird",
  "Cat",
  "Cleric",
  "Demon",
  "Dinosaur",
  "Dog",
  "Dragon",
  "Elemental",
  "Elf",
  "Faerie",
  "Fungus",
  "Giant",
  "Goblin",
  "Horror",
  "Human",
  "Hydra",
  "Knight",
  "Merfolk",
  "Ninja",
  "Pirate",
  "Rat",
  "Rogue",
  "Shaman",
  "Skeleton",
  "Sliver",
  "Snake",
  "Soldier",
  "Spider",
  "Spirit",
  "Treefolk",
  "Vampire",
  "Warrior",
  "Wizard",
  "Wolf",
  "Zombie",
];

export function TribalFilter({
  selected,
  onChange,
  collectionCounts = {},
}: TribalFilterProps): ReactNode {
  const [isOpen, setIsOpen] = useState(false);

  // Get top tribes from collection (5+ cards)
  const topTribes = Object.entries(collectionCounts)
    .filter(([, count]) => count >= 5)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <div className="flex flex-col gap-2">
      <label
        className="text-xs font-display tracking-wider"
        style={{ color: colors.text.muted }}
      >
        CREATURE TYPE
      </label>

      {/* Dropdown */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full h-9 px-3 text-sm rounded flex items-center justify-between transition-all"
          style={{
            background: colors.void.medium,
            border: `1px solid ${isOpen ? colors.gold.dim : colors.border.standard}`,
            color: selected ? colors.text.standard : colors.text.muted,
          }}
        >
          <span>{selected || "All Types"}</span>
          <span
            style={{
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          >
            ▼
          </span>
        </button>

        {isOpen && (
          <div
            className="absolute z-10 w-full mt-1 rounded shadow-lg max-h-48 overflow-auto"
            style={{
              background: colors.void.medium,
              border: `1px solid ${colors.border.standard}`,
            }}
          >
            <button
              onClick={() => {
                onChange(null);
                setIsOpen(false);
              }}
              className="w-full px-3 py-2 text-sm text-left transition-colors"
              style={{
                color: !selected ? colors.gold.standard : colors.text.dim,
                background: !selected ? colors.void.light : "transparent",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = colors.void.light)}
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = !selected ? colors.void.light : "transparent")
              }
            >
              All Types
            </button>
            {TRIBAL_TYPES.map((type) => {
              const count = collectionCounts[type];
              return (
                <button
                  key={type}
                  onClick={() => {
                    onChange(type);
                    setIsOpen(false);
                  }}
                  className="w-full px-3 py-2 text-sm text-left transition-colors flex justify-between"
                  style={{
                    color: selected === type ? colors.gold.standard : colors.text.dim,
                    background: selected === type ? colors.void.light : "transparent",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = colors.void.light)}
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background =
                      selected === type ? colors.void.light : "transparent")
                  }
                >
                  <span>{type}</span>
                  {count !== undefined && count > 0 && (
                    <span style={{ color: colors.text.muted }}>({count})</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Collection-based smart chips */}
      {topTribes.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs" style={{ color: colors.text.muted }}>
            In Collection:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {topTribes.map(([type, count]) => {
              const isActive = selected === type;
              return (
                <button
                  key={type}
                  onClick={() => onChange(isActive ? null : type)}
                  className="px-2.5 py-1 rounded-full text-xs font-display transition-all"
                  style={{
                    background: isActive ? `${synergyColors.tribal.color}25` : colors.void.lighter,
                    border: `1px solid ${isActive ? synergyColors.tribal.color : colors.border.subtle}`,
                    color: isActive ? synergyColors.tribal.color : colors.text.dim,
                    boxShadow: isActive ? `0 0 8px ${synergyColors.tribal.glow}` : "none",
                  }}
                >
                  {type} ({count})
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default TribalFilter;
