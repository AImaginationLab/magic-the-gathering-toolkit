/**
 * DeckArchetypeCard - Redesigned deck suggestion card
 * Cleaner layout inspired by TUI version with better readability
 */

import { useState } from "react";
import { colors } from "../../theme";
import type { ReactNode } from "react";
import type { components } from "../../../../shared/types/api-generated";

type DeckSuggestion = components["schemas"]["DeckSuggestion"];

interface DeckArchetypeCardProps {
  deck: DeckSuggestion;
  onViewCard: (cardName: string) => void;
  onAddToDeck?: (deck: DeckSuggestion) => void;
}

const MANA_COLORS: Record<string, { bg: string; text: string; name: string }> =
  {
    W: { bg: "#f8f6d8", text: "#1a1a1a", name: "White" },
    U: { bg: "#0e68ab", text: "#ffffff", name: "Blue" },
    B: { bg: "#3a3a3a", text: "#ffffff", name: "Black" },
    R: { bg: "#d3202a", text: "#ffffff", name: "Red" },
    G: { bg: "#00733e", text: "#ffffff", name: "Green" },
  };

// Calculate completion color
function getCompletionColor(pct: number): string {
  if (pct >= 0.7) return "#4caf50"; // green
  if (pct >= 0.5) return "#ff9800"; // orange
  if (pct >= 0.3) return "#ffc107"; // yellow
  return colors.text.muted;
}

// Get quality grade
function getQualityGrade(score: number): { grade: string; color: string } {
  if (score >= 0.9) return { grade: "A+", color: "#4caf50" };
  if (score >= 0.8) return { grade: "A", color: "#4caf50" };
  if (score >= 0.7) return { grade: "B+", color: "#00bcd4" };
  if (score >= 0.6) return { grade: "B", color: "#00bcd4" };
  if (score >= 0.5) return { grade: "C+", color: "#ffc107" };
  if (score >= 0.4) return { grade: "C", color: "#ffc107" };
  if (score >= 0.3) return { grade: "D", color: "#ff9800" };
  return { grade: "F", color: "#f44336" };
}

export function DeckArchetypeCard({
  deck,
  onViewCard,
  onAddToDeck,
}: DeckArchetypeCardProps): ReactNode {
  const [isExpanded, setIsExpanded] = useState(false);

  const completionPct = Math.min(100, Math.round(deck.completion_pct * 100));
  const completionColor = getCompletionColor(deck.completion_pct);
  const ownedCount = deck.key_cards_owned?.length ?? 0;
  const missingCount = deck.key_cards_missing?.length ?? 0;
  const qualityInfo = getQualityGrade(deck.quality_score ?? 0);
  const comboCount =
    (deck.complete_combos?.length ?? 0) + (deck.near_combos?.length ?? 0);

  return (
    <div
      className="rounded-lg overflow-hidden transition-all"
      style={{
        background: colors.void.light,
        border: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Header Row - Always Visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-5 text-left transition-colors"
        style={{
          borderBottom: isExpanded
            ? `1px solid ${colors.border.subtle}`
            : "none",
        }}
        onMouseEnter={(e) =>
          (e.currentTarget.style.background = colors.void.medium)
        }
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        {/* Line 1: Name, Colors, Completion, Owned/Needed */}
        <div className="flex items-center gap-4 mb-2">
          {/* Expand indicator */}
          <span style={{ color: colors.text.muted, fontSize: 14 }}>
            {isExpanded ? "▼" : "▶"}
          </span>

          {/* Deck name */}
          <h4
            className="font-display text-lg"
            style={{ color: colors.gold.standard }}
          >
            {deck.name}
          </h4>

          {/* Color pips */}
          <div className="flex items-center gap-1">
            {(deck.colors || []).map((c) => {
              const info = MANA_COLORS[c];
              if (!info) return null;
              return (
                <span
                  key={c}
                  className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                  style={{ background: info.bg, color: info.text }}
                  title={info.name}
                >
                  {c}
                </span>
              );
            })}
          </div>

          {/* Completion percentage */}
          <span
            className="font-mono text-base font-semibold"
            style={{ color: completionColor }}
          >
            {completionPct}%
          </span>

          {/* Quality grade */}
          {(deck.quality_score ?? 0) > 0 && (
            <span
              className="px-2 py-0.5 rounded text-sm font-bold"
              style={{
                background: `${qualityInfo.color}20`,
                color: qualityInfo.color,
              }}
            >
              {qualityInfo.grade}
            </span>
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Owned/Needed counts */}
          <span className="text-base" style={{ color: "#4caf50" }}>
            ✓ {ownedCount}
          </span>
          {missingCount > 0 && (
            <span className="text-base" style={{ color: "#ffc107" }}>
              ⚠ {missingCount}
            </span>
          )}
        </div>

        {/* Line 2: Badges (Format, Archetype, Commander, Combos, Cost) */}
        <div className="flex items-center gap-3 ml-6 flex-wrap">
          {/* Format badge */}
          <span
            className="px-2 py-1 rounded text-sm"
            style={{
              background: colors.void.lighter,
              color: colors.text.dim,
              textTransform: "capitalize",
            }}
          >
            {deck.format}
          </span>

          {/* Archetype badge */}
          {deck.archetype && (
            <span
              className="px-2 py-1 rounded text-sm"
              style={{
                background: "#9c27b020",
                color: "#ce93d8",
              }}
            >
              {deck.archetype}
            </span>
          )}

          {/* Commander */}
          {deck.commander && deck.commander !== deck.name && (
            <span className="text-sm" style={{ color: "#4caf50" }}>
              ★ {deck.commander}
            </span>
          )}

          {/* Combos */}
          {comboCount > 0 && (
            <span className="text-sm" style={{ color: "#ff7043" }}>
              ⚡ {comboCount} combo{comboCount > 1 ? "s" : ""}
            </span>
          )}

          {/* Estimated cost */}
          {deck.estimated_cost > 0 && (
            <span
              className="text-sm font-mono"
              style={{ color: colors.text.muted }}
            >
              ${deck.estimated_cost.toFixed(0)}
            </span>
          )}
        </div>

        {/* Line 3: Hint to expand (only when collapsed) */}
        {!isExpanded && (
          <div className="ml-6 mt-2">
            <span className="text-sm" style={{ color: colors.text.muted }}>
              Click to expand...
            </span>
          </div>
        )}
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-5 space-y-5">
          {/* Why This Deck */}
          {deck.reasons && deck.reasons.length > 0 && (
            <div>
              <h5
                className="text-sm font-display tracking-wide mb-2"
                style={{ color: colors.gold.dim }}
              >
                WHY THIS DECK
              </h5>
              <ul className="space-y-1">
                {deck.reasons.map((reason, idx) => (
                  <li
                    key={idx}
                    className="text-sm flex items-start gap-2"
                    style={{ color: colors.text.dim }}
                  >
                    <span style={{ color: colors.gold.dim }}>•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key Cards Owned */}
          {ownedCount > 0 && (
            <div>
              <h5
                className="text-sm font-display tracking-wide mb-3"
                style={{ color: "#4caf50" }}
              >
                KEY CARDS YOU OWN ({ownedCount})
              </h5>
              <div className="flex flex-wrap gap-2">
                {deck.key_cards_owned?.slice(0, 10).map((card) => (
                  <button
                    key={card}
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewCard(card);
                    }}
                    className="px-3 py-1.5 rounded text-sm transition-all"
                    style={{
                      background: colors.void.medium,
                      border: `1px solid ${colors.border.standard}`,
                      color: colors.text.dim,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = colors.gold.standard;
                      e.currentTarget.style.color = colors.text.bright;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor =
                        colors.border.standard;
                      e.currentTarget.style.color = colors.text.dim;
                    }}
                  >
                    {card}
                  </button>
                ))}
                {ownedCount > 10 && (
                  <span
                    className="px-3 py-1.5 text-sm"
                    style={{ color: colors.text.muted }}
                  >
                    +{ownedCount - 10} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Key Cards Needed */}
          {missingCount > 0 && (
            <div>
              <h5
                className="text-sm font-display tracking-wide mb-3"
                style={{ color: "#ffc107" }}
              >
                KEY CARDS NEEDED ({missingCount})
              </h5>
              <div className="flex flex-wrap gap-2">
                {deck.key_cards_missing?.slice(0, 8).map((card) => (
                  <button
                    key={card}
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewCard(card);
                    }}
                    className="px-3 py-1.5 rounded text-sm transition-all"
                    style={{
                      background: "transparent",
                      border: `1px dashed ${colors.border.standard}`,
                      color: colors.text.muted,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "#ffc107";
                      e.currentTarget.style.color = colors.text.dim;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor =
                        colors.border.standard;
                      e.currentTarget.style.color = colors.text.muted;
                    }}
                  >
                    {card}
                  </button>
                ))}
                {missingCount > 8 && (
                  <span
                    className="px-3 py-1.5 text-sm"
                    style={{ color: colors.text.muted }}
                  >
                    +{missingCount - 8} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Combos Section */}
          {(deck.complete_combos?.length ?? 0) > 0 && (
            <div>
              <h5
                className="text-sm font-display tracking-wide mb-3"
                style={{ color: "#ff7043" }}
              >
                COMPLETE COMBOS ({deck.complete_combos?.length})
              </h5>
              <div className="space-y-2">
                {deck.complete_combos?.slice(0, 3).map((combo) => (
                  <ComboRow
                    key={combo.id}
                    combo={combo}
                    onViewCard={onViewCard}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Near Combos */}
          {(deck.near_combos?.length ?? 0) > 0 && (
            <div>
              <h5
                className="text-sm font-display tracking-wide mb-3"
                style={{ color: "#00bcd4" }}
              >
                NEAR COMBOS ({deck.near_combos?.length})
              </h5>
              <div className="space-y-2">
                {deck.near_combos?.slice(0, 2).map((combo) => (
                  <ComboRow
                    key={combo.id}
                    combo={combo}
                    onViewCard={onViewCard}
                    isNear
                  />
                ))}
              </div>
            </div>
          )}

          {/* Add to Decks button */}
          {onAddToDeck && (
            <div
              className="pt-4 border-t"
              style={{ borderColor: colors.border.subtle }}
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddToDeck(deck);
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2"
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
                <span>+</span>
                <span>Add to My Decks</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Combo row component - expandable to show details
function ComboRow({
  combo,
  onViewCard,
  isNear = false,
}: {
  combo: { id: string; cards: string[]; missing_cards?: string[] };
  onViewCard: (cardName: string) => void;
  isNear?: boolean;
}): ReactNode {
  const [isExpanded, setIsExpanded] = useState(false);
  const accentColor = isNear ? "#00bcd4" : "#ff7043";

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: colors.void.medium,
        border: `1px solid ${accentColor}30`,
      }}
    >
      {/* Header - clickable to expand */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsExpanded(!isExpanded);
        }}
        className="w-full p-3 text-left transition-all flex items-center gap-2"
        onMouseEnter={(e) => {
          e.currentTarget.style.background = colors.void.lighter;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
      >
        <span style={{ color: colors.text.muted, fontSize: 12 }}>
          {isExpanded ? "▼" : "▶"}
        </span>
        <div className="flex flex-wrap gap-2 flex-1">
          {combo.cards.slice(0, 3).map((card) => (
            <span
              key={card}
              className="px-2 py-1 rounded text-sm"
              style={{
                background: colors.void.lighter,
                color: combo.missing_cards?.includes(card)
                  ? colors.text.muted
                  : colors.text.dim,
                textDecoration: combo.missing_cards?.includes(card)
                  ? "line-through"
                  : "none",
              }}
            >
              {card}
            </span>
          ))}
          {combo.cards.length > 3 && (
            <span className="text-xs py-1" style={{ color: colors.text.muted }}>
              +{combo.cards.length - 3} more
            </span>
          )}
        </div>
        {isNear && combo.missing_cards && combo.missing_cards.length > 0 && (
          <span
            className="text-xs px-2 py-1 rounded"
            style={{ background: `${accentColor}20`, color: accentColor }}
          >
            {combo.missing_cards.length} missing
          </span>
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div
          className="px-3 pb-3 pt-1 border-t"
          style={{ borderColor: `${accentColor}20` }}
        >
          {/* All cards - clickable */}
          <div className="mb-3">
            <span
              className="text-xs font-display"
              style={{ color: colors.text.muted }}
            >
              CARDS IN COMBO
            </span>
            <div className="flex flex-wrap gap-2 mt-2">
              {combo.cards.map((card) => (
                <button
                  key={card}
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewCard(card);
                  }}
                  className="px-2 py-1 rounded text-sm transition-all"
                  style={{
                    background: colors.void.lighter,
                    border: `1px solid ${colors.border.subtle}`,
                    color: combo.missing_cards?.includes(card)
                      ? colors.text.muted
                      : colors.text.dim,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = colors.gold.standard;
                    e.currentTarget.style.color = colors.gold.standard;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = colors.border.subtle;
                    e.currentTarget.style.color = combo.missing_cards?.includes(
                      card,
                    )
                      ? colors.text.muted
                      : colors.text.dim;
                  }}
                >
                  {card}
                </button>
              ))}
            </div>
          </div>

          {/* Missing cards */}
          {combo.missing_cards && combo.missing_cards.length > 0 && (
            <div>
              <span
                className="text-xs font-display"
                style={{ color: "#ffc107" }}
              >
                MISSING
              </span>
              <div className="flex flex-wrap gap-2 mt-2">
                {combo.missing_cards.map((card) => (
                  <button
                    key={card}
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewCard(card);
                    }}
                    className="px-2 py-1 rounded text-sm transition-all"
                    style={{
                      background: "transparent",
                      border: `1px dashed #ffc10740`,
                      color: "#ffc107",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "#ffc107";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "#ffc10740";
                    }}
                  >
                    {card}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DeckArchetypeCard;
