/**
 * DeckImpactTooltip - Shows what changes when adding a card to a deck.
 * Inspired by WoW item comparison tooltips.
 */

import { colors } from "../theme";

import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

type DeckImpact = components["schemas"]["DeckImpact"];
type StatChange = components["schemas"]["StatChange"];

interface DeckImpactTooltipProps {
  impact: DeckImpact | null;
  isLoading?: boolean;
}

// Helper to format display text (replace underscores with spaces)
const formatText = (text: string): string => text.replace(/_/g, " ");

// Impact indicator colors
const impactColors = {
  positive: "#4CAF50", // Material green
  negative: "#E54545", // Soft red
  neutral: "#40C4D0", // Soft cyan
  keyword: "#9040C0", // Muted purple
  theme: "#E67300", // Warm orange
  tribal: "#50B050", // Muted green
};

function StatChangeDisplay({ change }: { change: StatChange }): ReactNode {
  const isPositive = change.is_positive === true;
  const isNegative = change.is_positive === false;
  const color = isPositive
    ? impactColors.positive
    : isNegative
      ? impactColors.negative
      : impactColors.neutral;

  // Format delta display
  let deltaStr = "";
  if (
    typeof change.old_value === "number" &&
    typeof change.new_value === "number"
  ) {
    const delta = change.new_value - change.old_value;
    if (Number.isInteger(delta)) {
      deltaStr = delta > 0 ? `+${delta}` : `${delta}`;
    } else {
      deltaStr = delta > 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2);
    }
  }

  return (
    <div className="flex items-center gap-2 text-sm" style={{ color }}>
      <span className="font-medium">{change.name}:</span>
      <span>{deltaStr}</span>
      <span className="text-xs" style={{ color: colors.text.muted }}>
        ({change.old_value} → {change.new_value})
      </span>
    </div>
  );
}

export function DeckImpactTooltip({
  impact,
  isLoading,
}: DeckImpactTooltipProps): ReactNode {
  if (isLoading) {
    return (
      <div
        className="p-3 rounded-lg"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <div className="text-xs" style={{ color: colors.text.muted }}>
          Calculating impact...
        </div>
      </div>
    );
  }

  if (!impact) {
    return null;
  }

  // Filter out themes that duplicate keywords (e.g., "ward" keyword + "ward" theme)
  const keywordsLower = new Set(
    impact.keywords_added.map((kw) => kw.toLowerCase()),
  );
  const filteredThemes = impact.themes_strengthened.filter(
    (theme) => !keywordsLower.has(theme.toLowerCase().replace(/_/g, " ")),
  );

  // Check if there's any impact to show
  const hasImpact =
    impact.keywords_added.length > 0 ||
    filteredThemes.length > 0 ||
    impact.tribal_boost ||
    impact.power_added > 0 ||
    impact.toughness_added > 0 ||
    impact.changes.length > 0 ||
    (impact.matchup_improvements?.length ?? 0) > 0;

  if (!hasImpact) {
    // Show a minimal tooltip even with no specific impact
    return (
      <div
        className="p-3 rounded-lg"
        style={{
          background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
        }}
      >
        <div
          className="text-xs font-display uppercase tracking-wider"
          style={{ color: colors.gold.standard }}
        >
          Adding {impact.card_name}
        </div>
        <div className="text-xs mt-1" style={{ color: colors.text.muted }}>
          No significant deck changes
        </div>
      </div>
    );
  }

  return (
    <div
      className="p-3 rounded-lg space-y-2"
      style={{
        background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
        border: `1px solid ${colors.border.standard}`,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.4)",
      }}
    >
      {/* Header */}
      <div
        className="text-xs font-display uppercase tracking-wider pb-1 border-b"
        style={{
          color: colors.gold.standard,
          borderColor: colors.border.subtle,
        }}
      >
        Adding {impact.card_name}
      </div>

      {/* Keywords */}
      {impact.keywords_added.length > 0 && (
        <div className="space-y-1">
          {impact.keywords_added.map((kw) => (
            <div
              key={kw}
              className="flex items-center gap-2 text-sm font-medium"
              style={{ color: impactColors.keyword }}
            >
              <span>+</span>
              <span className="capitalize">{formatText(kw)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Combat stats */}
      {(impact.power_added > 0 || impact.toughness_added > 0) && (
        <div
          className="flex items-center gap-3 text-sm font-medium"
          style={{ color: impactColors.positive }}
        >
          {impact.power_added > 0 && <span>+{impact.power_added} Power</span>}
          {impact.toughness_added > 0 && (
            <span>+{impact.toughness_added} Toughness</span>
          )}
        </div>
      )}

      {/* Themes (filtered to remove duplicates of keywords) */}
      {filteredThemes.length > 0 && (
        <div className="space-y-1">
          {filteredThemes.map((theme) => (
            <div
              key={theme}
              className="flex items-center gap-2 text-sm"
              style={{ color: impactColors.theme }}
            >
              <span>↑</span>
              <span className="capitalize">{formatText(theme)} Theme</span>
            </div>
          ))}
        </div>
      )}

      {/* Tribal */}
      {impact.tribal_boost && (
        <div
          className="flex items-center gap-2 text-sm font-medium"
          style={{ color: impactColors.tribal }}
        >
          <span>★</span>
          <span>Strengthens {impact.tribal_boost} tribal</span>
        </div>
      )}

      {/* Matchup improvements */}
      {impact.matchup_improvements &&
        impact.matchup_improvements.length > 0 && (
          <div
            className="flex items-center gap-2 text-sm"
            style={{ color: impactColors.positive }}
          >
            <span>⚔</span>
            <span>Strong vs {impact.matchup_improvements.join(", ")}</span>
          </div>
        )}

      {/* Stat changes */}
      {impact.changes.length > 0 && (
        <div
          className="space-y-1 pt-1 border-t"
          style={{ borderColor: colors.border.subtle }}
        >
          {impact.changes.slice(0, 5).map((change, idx) => (
            <StatChangeDisplay key={`${change.name}-${idx}`} change={change} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Compact inline version for search result rows
 */
export function DeckImpactBadges({
  impact,
}: {
  impact: DeckImpact | null;
}): ReactNode {
  if (!impact) return null;

  // Filter out themes that duplicate keywords
  const keywordsLower = new Set(
    impact.keywords_added.map((kw) => kw.toLowerCase()),
  );
  const filteredThemes = impact.themes_strengthened.filter(
    (theme) => !keywordsLower.has(theme.toLowerCase().replace(/_/g, " ")),
  );

  const badges: Array<{ text: string; color: string }> = [];

  // Add keyword badges (max 2)
  impact.keywords_added.slice(0, 2).forEach((kw) => {
    badges.push({ text: `+${formatText(kw)}`, color: impactColors.keyword });
  });

  // Add combat stats
  if (impact.power_added > 0) {
    badges.push({
      text: `+${impact.power_added}/${impact.toughness_added}`,
      color: impactColors.positive,
    });
  }

  // Add theme badge (max 1, filtered)
  if (filteredThemes.length > 0) {
    badges.push({
      text: `↑${formatText(filteredThemes[0])}`,
      color: impactColors.theme,
    });
  }

  // Add tribal badge
  if (impact.tribal_boost) {
    badges.push({
      text: `★${impact.tribal_boost}`,
      color: impactColors.tribal,
    });
  }

  if (badges.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {badges.slice(0, 4).map((badge, idx) => (
        <span
          key={idx}
          className="text-xs px-1.5 py-0.5 rounded font-medium"
          style={{
            color: badge.color,
            background: `${badge.color}15`,
            border: `1px solid ${badge.color}30`,
          }}
        >
          {badge.text}
        </span>
      ))}
    </div>
  );
}
