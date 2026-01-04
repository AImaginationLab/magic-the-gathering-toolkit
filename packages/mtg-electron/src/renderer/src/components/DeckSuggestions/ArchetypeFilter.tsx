/**
 * ArchetypeFilter - Play style/archetype filter with dropdown and quick chips
 */

import { useState } from "react";
import { colors, synergyColors } from "../../theme";
import type { ReactNode } from "react";

interface ArchetypeFilterProps {
  selected: string | null;
  onChange: (archetype: string | null) => void;
}

const ARCHETYPES = [
  "Aggro",
  "Artifacts",
  "Blink",
  "Burn",
  "Clones",
  "Control",
  "Counters",
  "Discard",
  "Draw",
  "Enchantments",
  "Energy",
  "Graveyard",
  "Landfall",
  "Lands",
  "Lifegain",
  "Mill",
  "Ramp",
  "Reanimator",
  "Sacrifice",
  "Spellslinger",
  "Stax",
  "Superfriends",
  "Tokens",
  "Voltron",
];

// Popular archetypes shown as quick chips
const POPULAR_ARCHETYPES = ["Aggro", "Control", "Combo", "Tribal", "Tokens", "Sacrifice"];

export function ArchetypeFilter({ selected, onChange }: ArchetypeFilterProps): ReactNode {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <label
        className="text-xs font-display tracking-wider"
        style={{ color: colors.text.muted }}
      >
        ARCHETYPE
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
          <span>{selected || "All Styles"}</span>
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
              All Styles
            </button>
            {ARCHETYPES.map((arch) => (
              <button
                key={arch}
                onClick={() => {
                  onChange(arch);
                  setIsOpen(false);
                }}
                className="w-full px-3 py-2 text-sm text-left transition-colors"
                style={{
                  color: selected === arch ? colors.gold.standard : colors.text.dim,
                  background: selected === arch ? colors.void.light : "transparent",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = colors.void.light)}
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background =
                    selected === arch ? colors.void.light : "transparent")
                }
              >
                {arch}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Quick picks */}
      <div className="flex flex-wrap gap-1.5">
        {POPULAR_ARCHETYPES.map((arch) => {
          const isActive = selected === arch;
          return (
            <button
              key={arch}
              onClick={() => onChange(isActive ? null : arch)}
              className="px-2.5 py-1 rounded-full text-xs font-display transition-all"
              style={{
                background: isActive ? `${synergyColors.strategy.color}25` : colors.void.lighter,
                border: `1px solid ${isActive ? synergyColors.strategy.color : colors.border.subtle}`,
                color: isActive ? synergyColors.strategy.color : colors.text.dim,
                boxShadow: isActive ? `0 0 8px ${synergyColors.strategy.glow}` : "none",
              }}
            >
              {arch}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ArchetypeFilter;
