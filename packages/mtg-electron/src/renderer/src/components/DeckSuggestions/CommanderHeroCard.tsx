/**
 * CommanderHeroCard - Commander display with hero art background
 * Features completion ring, color identity, and archetype badge
 */

import { useState } from "react";
import { colors, synergyColors } from "../../theme";
import { CompletionRing } from "./CompletionRing";
import type { ReactNode } from "react";

interface CommanderHeroCardProps {
  name: string;
  colors: string[];
  archetype: string | null;
  completionPct: number;
  reasons: string[];
  imageUrl?: string | null;
  featured?: boolean;
  onClick?: () => void;
}

const MANA_COLORS: Record<string, { color: string; name: string }> = {
  W: { color: colors.mana.white.color, name: "White" },
  U: { color: colors.mana.blue.color, name: "Blue" },
  B: { color: colors.mana.black.color, name: "Black" },
  R: { color: colors.mana.red.color, name: "Red" },
  G: { color: colors.mana.green.color, name: "Green" },
};

export function CommanderHeroCard({
  name,
  colors: commanderColors,
  archetype,
  completionPct,
  reasons,
  imageUrl,
  featured = false,
  onClick,
}: CommanderHeroCardProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const [imageError] = useState(false);

  return (
    <div
      className="relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300"
      style={{
        background: colors.void.light,
        border: `1px solid ${isHovered ? colors.gold.dim : colors.border.subtle}`,
        boxShadow: isHovered
          ? `0 8px 32px rgba(0,0,0,0.5), 0 0 20px ${colors.gold.glow}`
          : "0 4px 16px rgba(0,0,0,0.3)",
        transform: isHovered ? "translateY(-4px)" : "none",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* Background art (blurred) */}
      {imageUrl && !imageError && (
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url(${imageUrl})`,
            backgroundSize: "cover",
            backgroundPosition: "center top",
            filter: "blur(8px) brightness(0.6)",
          }}
        />
      )}

      {/* Gradient overlay */}
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(180deg, transparent 0%, ${colors.void.deep}ee 60%, ${colors.void.deep} 100%)`,
        }}
      />

      {/* Content */}
      <div className="relative p-5">
        <div className="flex items-start gap-4">
          {/* Left: Completion ring */}
          <CompletionRing
            percent={completionPct}
            size={featured ? "large" : "medium"}
            animated
          />

          {/* Right: Info */}
          <div className="flex-1 min-w-0">
            {/* Commander name */}
            <h3
              className="font-display text-lg truncate"
              style={{ color: colors.text.bright }}
            >
              {name}
            </h3>

            {/* Color identity */}
            <div className="flex items-center gap-1.5 mt-2">
              {commanderColors.length === 0 ? (
                <span className="text-xs" style={{ color: colors.text.muted }}>
                  Colorless
                </span>
              ) : (
                commanderColors.map((c) => {
                  const manaInfo = MANA_COLORS[c];
                  if (!manaInfo) return null;
                  return (
                    <i
                      key={c}
                      className={`ms ms-${c.toLowerCase()} ms-cost`}
                      style={{ color: manaInfo.color, fontSize: 16 }}
                      title={manaInfo.name}
                    />
                  );
                })
              )}
            </div>

            {/* Archetype badge */}
            {archetype && (
              <span
                className="inline-block mt-2 px-2.5 py-0.5 rounded text-xs font-display"
                style={{
                  background: `${synergyColors.strategy.color}20`,
                  border: `1px solid ${synergyColors.strategy.color}40`,
                  color: synergyColors.strategy.color,
                }}
              >
                {archetype}
              </span>
            )}
          </div>
        </div>

        {/* Reasons (show on hover or if featured) */}
        {(isHovered || featured) && reasons.length > 0 && (
          <div
            className="mt-4 pt-4 space-y-1.5"
            style={{
              borderTop: `1px solid ${colors.border.subtle}`,
              animation: "reveal-up 0.3s ease-out",
            }}
          >
            <span
              className="text-xs font-display"
              style={{ color: colors.text.muted }}
            >
              SYNERGIES
            </span>
            {reasons.slice(0, 4).map((reason, idx) => (
              <p
                key={idx}
                className="text-xs flex items-start gap-2"
                style={{ color: colors.text.dim }}
              >
                <span style={{ color: colors.gold.dim }}>-</span>
                <span className="line-clamp-1">{reason}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default CommanderHeroCard;
