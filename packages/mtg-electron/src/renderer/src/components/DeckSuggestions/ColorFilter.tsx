/**
 * ColorFilter - Mana color toggle buttons for filtering
 * Visual mana pip buttons with glow effects when active
 */

import { colors } from "../../theme";
import type { ReactNode } from "react";

interface ColorFilterProps {
  activeColors: string[];
  onChange: (colors: string[]) => void;
}

const MANA_COLORS = [
  { code: "W", name: "White", color: colors.mana.white.color, glow: colors.mana.white.glow },
  { code: "U", name: "Blue", color: colors.mana.blue.color, glow: colors.mana.blue.glow },
  { code: "B", name: "Black", color: colors.mana.black.color, glow: colors.mana.black.glow },
  { code: "R", name: "Red", color: colors.mana.red.color, glow: colors.mana.red.glow },
  { code: "G", name: "Green", color: colors.mana.green.color, glow: colors.mana.green.glow },
  { code: "C", name: "Colorless", color: colors.mana.colorless.color, glow: colors.mana.colorless.glow },
];

export function ColorFilter({ activeColors, onChange }: ColorFilterProps): ReactNode {
  const toggleColor = (code: string): void => {
    if (activeColors.includes(code)) {
      onChange(activeColors.filter((c) => c !== code));
    } else {
      onChange([...activeColors, code]);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <label
        className="text-xs font-display tracking-wider"
        style={{ color: colors.text.muted }}
      >
        COLORS
      </label>
      <div className="flex flex-wrap gap-2">
        {MANA_COLORS.map((mana) => {
          const isActive = activeColors.includes(mana.code);
          return (
            <button
              key={mana.code}
              onClick={() => toggleColor(mana.code)}
              title={mana.name}
              className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200"
              style={{
                background: isActive ? mana.color : colors.void.lighter,
                border: `2px solid ${isActive ? mana.color : colors.border.subtle}`,
                boxShadow: isActive ? `0 0 12px ${mana.glow}` : "none",
                transform: isActive ? "scale(1.1)" : "scale(1)",
              }}
            >
              <i
                className={`ms ms-${mana.code.toLowerCase()} ms-cost`}
                style={{
                  fontSize: 16,
                  color: isActive
                    ? mana.code === "W"
                      ? colors.void.deep
                      : colors.void.deepest
                    : colors.text.dim,
                }}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ColorFilter;
