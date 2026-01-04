/**
 * ActiveFilterPills - Displays active filters as removable pills
 */

import { colors } from "../../theme";
import type { ReactNode } from "react";

interface FilterPill {
  type: "color" | "archetype" | "tribal" | "ownership";
  label: string;
  value: string;
}

interface ActiveFilterPillsProps {
  activeColors: string[];
  archetype: string | null;
  tribal: string | null;
  onRemoveColor: (color: string) => void;
  onRemoveArchetype: () => void;
  onRemoveTribal: () => void;
  onClearAll: () => void;
}

const COLOR_NAMES: Record<string, string> = {
  W: "White",
  U: "Blue",
  B: "Black",
  R: "Red",
  G: "Green",
  C: "Colorless",
};

export function ActiveFilterPills({
  activeColors,
  archetype,
  tribal,
  onRemoveColor,
  onRemoveArchetype,
  onRemoveTribal,
  onClearAll,
}: ActiveFilterPillsProps): ReactNode {
  const pills: FilterPill[] = [];

  // Add color pills
  activeColors.forEach((color) => {
    pills.push({
      type: "color",
      label: `Color: ${COLOR_NAMES[color] || color}`,
      value: color,
    });
  });

  // Add archetype pill
  if (archetype) {
    pills.push({
      type: "archetype",
      label: `Style: ${archetype}`,
      value: archetype,
    });
  }

  // Add tribal pill
  if (tribal) {
    pills.push({
      type: "tribal",
      label: `Tribal: ${tribal}`,
      value: tribal,
    });
  }

  if (pills.length === 0) {
    return null;
  }

  const handleRemove = (pill: FilterPill): void => {
    switch (pill.type) {
      case "color":
        onRemoveColor(pill.value);
        break;
      case "archetype":
        onRemoveArchetype();
        break;
      case "tribal":
        onRemoveTribal();
        break;
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <span className="text-xs" style={{ color: colors.text.muted }}>
        Active:
      </span>
      {pills.map((pill, idx) => (
        <div
          key={`${pill.type}-${pill.value}-${idx}`}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
          style={{
            background: colors.void.medium,
            border: `1px solid ${colors.gold.dim}`,
            color: colors.text.standard,
          }}
        >
          <span>{pill.label}</span>
          <button
            onClick={() => handleRemove(pill)}
            className="ml-0.5 opacity-60 hover:opacity-100 transition-opacity"
            style={{ color: colors.text.muted }}
          >
            ×
          </button>
        </div>
      ))}
      {pills.length > 1 && (
        <button
          onClick={onClearAll}
          className="text-xs px-2 py-1 rounded transition-colors"
          style={{ color: colors.text.muted }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.color = colors.gold.standard)
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.color = colors.text.muted)
          }
        >
          Clear all
        </button>
      )}
    </div>
  );
}

export default ActiveFilterPills;
