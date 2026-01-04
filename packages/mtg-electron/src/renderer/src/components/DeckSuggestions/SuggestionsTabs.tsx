/**
 * SuggestionsTabs - Enhanced visual tab navigation
 * Each tab has distinct styling and preview content
 */

import { colors, synergyColors } from "../../theme";
import type { ReactNode } from "react";

type TabMode = "suggestions" | "commanders" | "decks";

interface SuggestionsTabsProps {
  activeTab: TabMode;
  onChange: (tab: TabMode) => void;
}

const TAB_CONFIG: Record<
  TabMode,
  {
    label: string;
    description: string;
    icon: string;
    color: string;
    glow: string;
  }
> = {
  suggestions: {
    label: "Card Suggestions",
    description: "Find upgrades for your deck",
    icon: "ms-instant",
    color: synergyColors.keyword.color,
    glow: synergyColors.keyword.glow,
  },
  commanders: {
    label: "Commander Finder",
    description: "Match commanders to your collection",
    icon: "ms-planeswalker",
    color: colors.gold.standard,
    glow: colors.gold.glow,
  },
  decks: {
    label: "Deck Ideas",
    description: "Discover buildable archetypes",
    icon: "ms-saga",
    color: synergyColors.combo.color,
    glow: synergyColors.combo.glow,
  },
};

export function SuggestionsTabs({ activeTab, onChange }: SuggestionsTabsProps): ReactNode {
  return (
    <div className="flex items-stretch gap-3">
      {(Object.keys(TAB_CONFIG) as TabMode[]).map((tab) => {
        const config = TAB_CONFIG[tab];
        const isActive = activeTab === tab;

        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className="flex-1 p-4 rounded-lg text-left transition-all duration-200"
            style={{
              background: isActive ? `${config.color}12` : colors.void.light,
              border: `1px solid ${isActive ? config.color : colors.border.subtle}`,
              boxShadow: isActive ? `0 0 20px ${config.glow}, 0 4px 16px rgba(0,0,0,0.3)` : "none",
              transform: isActive ? "translateY(-2px)" : "none",
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = `${config.color}60`;
                e.currentTarget.style.background = colors.void.medium;
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive) {
                e.currentTarget.style.borderColor = colors.border.subtle;
                e.currentTarget.style.background = colors.void.light;
              }
            }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{
                  background: isActive ? `${config.color}25` : colors.void.lighter,
                  border: `1px solid ${isActive ? config.color : colors.border.subtle}`,
                }}
              >
                <i
                  className={`ms ${config.icon}`}
                  style={{
                    fontSize: 20,
                    color: isActive ? config.color : colors.text.muted,
                  }}
                />
              </div>
              <div>
                <h3
                  className="font-display text-sm tracking-wide"
                  style={{ color: isActive ? config.color : colors.text.dim }}
                >
                  {config.label}
                </h3>
                <p className="text-xs mt-0.5" style={{ color: colors.text.muted }}>
                  {config.description}
                </p>
              </div>
            </div>

            {/* Active indicator bar */}
            {isActive && (
              <div
                className="h-0.5 mt-3 rounded-full"
                style={{
                  background: `linear-gradient(90deg, ${config.color}, transparent)`,
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

export default SuggestionsTabs;
