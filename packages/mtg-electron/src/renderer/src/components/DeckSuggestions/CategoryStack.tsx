/**
 * CategoryStack - Stacked card visualization with fan-out animation
 * Groups suggested cards by category (synergy, staple, upgrade, budget)
 */

import { useState } from "react";
import { colors, synergyColors } from "../../theme";
import { ManaCost } from "../ManaSymbols";
import type { ReactNode } from "react";
import type { components } from "../../../../shared/types/api-generated";

type SuggestedCard = components["schemas"]["SuggestedCard"];

interface CategoryStackProps {
  category: "synergy" | "staple" | "upgrade" | "budget";
  cards: SuggestedCard[];
  onCardClick: (cardName: string) => void;
}

const CATEGORY_CONFIG = {
  synergy: {
    label: "SYNERGY",
    color: synergyColors.keyword.color,
    glow: synergyColors.keyword.glow,
    icon: "ms-instant",
  },
  staple: {
    label: "STAPLE",
    color: colors.gold.standard,
    glow: colors.gold.glow,
    icon: "ms-artifact",
  },
  upgrade: {
    label: "UPGRADE",
    color: synergyColors.combo.color,
    glow: synergyColors.combo.glow,
    icon: "ms-planeswalker",
  },
  budget: {
    label: "BUDGET",
    color: synergyColors.tribal.color,
    glow: synergyColors.tribal.glow,
    icon: "ms-land",
  },
};

export function CategoryStack({
  category,
  cards,
  onCardClick,
}: CategoryStackProps): ReactNode {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const config = CATEGORY_CONFIG[category];

  if (cards.length === 0) return null;

  const topCards = cards.slice(0, 3);

  return (
    <div className="flex flex-col">
      {/* Stack header */}
      <div className="flex items-center gap-2 mb-2">
        <i className={`ms ${config.icon}`} style={{ color: config.color, fontSize: 14 }} />
        <span
          className="text-xs font-display tracking-wider"
          style={{ color: config.color }}
        >
          {config.label}
        </span>
        <span className="text-xs" style={{ color: colors.text.muted }}>
          ({cards.length})
        </span>
      </div>

      {/* Collapsed stack view */}
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="relative cursor-pointer transition-all"
          style={{
            height: 140,
            width: 120,
          }}
        >
          {/* Stacked cards */}
          {topCards.map((card, idx) => (
            <div
              key={card.name}
              className="absolute rounded-lg transition-all duration-200"
              style={{
                width: 100,
                height: 120,
                background: colors.void.medium,
                border: `1px solid ${isHovered ? config.color : colors.border.subtle}`,
                transform: isHovered
                  ? `translateY(${idx * -8}px) translateX(${idx * 8}px) rotate(${(idx - 1) * 5}deg)`
                  : `translateY(${idx * 4}px) translateX(${idx * 2}px)`,
                zIndex: topCards.length - idx,
                boxShadow: isHovered
                  ? `0 4px 16px rgba(0,0,0,0.4), 0 0 12px ${config.glow}`
                  : `0 ${2 + idx * 2}px ${8 + idx * 4}px rgba(0,0,0,${0.2 + idx * 0.1})`,
              }}
            >
              {/* Card preview content */}
              <div className="p-2 h-full flex flex-col">
                <span
                  className="text-xs font-display truncate"
                  style={{ color: colors.text.bright }}
                >
                  {card.name}
                </span>
                {card.mana_cost && (
                  <div className="mt-1">
                    <ManaCost cost={card.mana_cost} size="small" />
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Count badge */}
          {cards.length > 3 && (
            <div
              className="absolute bottom-0 right-0 px-2 py-1 rounded-full text-xs font-bold"
              style={{
                background: config.color,
                color: colors.void.deepest,
                transform: "translate(25%, 25%)",
                zIndex: 10,
              }}
            >
              +{cards.length - 3}
            </div>
          )}
        </button>
      )}

      {/* Expanded grid view */}
      {isExpanded && (
        <div className="relative">
          <button
            onClick={() => setIsExpanded(false)}
            className="absolute -top-6 right-0 text-xs transition-colors"
            style={{ color: colors.text.muted }}
            onMouseEnter={(e) => (e.currentTarget.style.color = colors.text.standard)}
            onMouseLeave={(e) => (e.currentTarget.style.color = colors.text.muted)}
          >
            Collapse ×
          </button>

          <div
            className="grid gap-3 p-3 rounded-lg"
            style={{
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              background: colors.void.medium,
              border: `1px solid ${config.color}40`,
            }}
          >
            {cards.map((card, idx) => (
              <button
                key={card.name}
                onClick={() => onCardClick(card.name)}
                className="p-3 rounded-lg text-left transition-all"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.subtle}`,
                  animation: `reveal-up 0.2s ease-out ${idx * 0.03}s both`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = config.color;
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = colors.border.subtle;
                  e.currentTarget.style.transform = "none";
                }}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span
                    className="text-sm font-display truncate"
                    style={{ color: colors.text.bright }}
                  >
                    {card.name}
                  </span>
                </div>
                {card.mana_cost && <ManaCost cost={card.mana_cost} size="small" />}
                {card.type_line && (
                  <p
                    className="text-xs truncate mt-1"
                    style={{ color: colors.text.muted }}
                  >
                    {card.type_line}
                  </p>
                )}
                <div className="flex items-center justify-between mt-2">
                  {card.price_usd !== null && card.price_usd !== undefined && (
                    <span
                      className="text-xs font-mono"
                      style={{ color: colors.gold.standard }}
                    >
                      ${card.price_usd.toFixed(2)}
                    </span>
                  )}
                </div>
                <p
                  className="text-xs mt-2 line-clamp-2"
                  style={{ color: colors.text.dim }}
                >
                  {card.reason}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default CategoryStack;
