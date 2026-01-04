/**
 * Combo Detection Panel
 * Detects and displays combos from a deck's card list.
 * Shows complete combos with animated styling and potential combos with missing cards highlighted.
 */

import { useState, useEffect, useCallback } from "react";
import { colors, synergyColors } from "../theme";
import { CardDetailModal } from "./CardDetailModal";

import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

// Use generated types from OpenAPI schema
type DetectCombosResult = components["schemas"]["DetectCombosResult"];
type Combo = components["schemas"]["Combo"];
type ComboCard = components["schemas"]["ComboCard"];
type ComboType = Combo["combo_type"];

// Combo type display configuration
const COMBO_TYPE_CONFIG: Record<
  ComboType,
  { label: string; icon: string; color: string }
> = {
  infinite: {
    label: "Infinite",
    icon: "ms ms-infinity",
    color: "#ff5722",
  },
  value: {
    label: "Value",
    icon: "ms ms-ability-draw",
    color: "#4caf50",
  },
  lock: {
    label: "Lock",
    icon: "ms ms-ability-hexproof",
    color: "#9c27b0",
  },
  win: {
    label: "Win",
    icon: "ms ms-saga",
    color: "#ffc107",
  },
};

// Get mana color icons for combo colors
function getColorIcons(comboColors: string[] | undefined): string[] {
  if (!comboColors || comboColors.length === 0) return [];
  return comboColors.map((c) => `ms ms-${c.toLowerCase()}`);
}

interface ComboDetectionPanelProps {
  cardNames: string[];
  onCardSelect?: (cardName: string) => void;
}

export function ComboDetectionPanel({
  cardNames,
  onCardSelect,
}: ComboDetectionPanelProps): ReactNode {
  const [result, setResult] = useState<DetectCombosResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);
  const [expandedComboId, setExpandedComboId] = useState<string | null>(null);

  // Detect combos when card names change
  useEffect(() => {
    if (cardNames.length === 0) {
      setResult(null);
      return;
    }

    const detectCombos = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const detected = await window.electronAPI.api.combos.detect(cardNames);
        setResult(detected);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(`Failed to detect combos: ${message}`);
        setResult(null);
      } finally {
        setIsLoading(false);
      }
    };

    detectCombos();
  }, [cardNames]);

  // Handle card click
  const handleCardClick = useCallback(
    (cardName: string) => {
      if (onCardSelect) {
        onCardSelect(cardName);
      } else {
        setSelectedCardName(cardName);
      }
    },
    [onCardSelect],
  );

  // Toggle combo expansion
  const toggleCombo = useCallback((comboId: string) => {
    setExpandedComboId((prev) => (prev === comboId ? null : comboId));
  }, []);

  // Calculate totals
  const completeCount = result?.combos?.length ?? 0;
  const potentialCount = result?.potential_combos?.length ?? 0;
  const totalCount = completeCount + potentialCount;

  return (
    <div
      className="h-full flex flex-col rounded-xl overflow-hidden"
      style={{
        background: colors.void.deep,
        border: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Header */}
      <header
        className="p-4 flex items-center gap-3"
        style={{
          borderBottom: `1px solid ${colors.border.subtle}`,
          background: `linear-gradient(180deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
        }}
      >
        {/* Combo icon with glow */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{
            background: `${synergyColors.combo.color}20`,
            border: `1px solid ${synergyColors.combo.color}40`,
            boxShadow: `0 0 20px ${synergyColors.combo.glow}`,
          }}
        >
          <i
            className="ms ms-instant"
            style={{ color: synergyColors.combo.color, fontSize: 18 }}
          />
        </div>

        <div className="flex-1">
          <h2
            className="font-display text-sm tracking-wider"
            style={{ color: synergyColors.combo.color }}
          >
            COMBO DETECTION
          </h2>
          <p className="text-xs" style={{ color: colors.text.muted }}>
            {isLoading
              ? "Analyzing deck..."
              : totalCount > 0
                ? `${completeCount} complete, ${potentialCount} potential`
                : "No combos detected"}
          </p>
        </div>

        {/* Stats badge */}
        {totalCount > 0 && (
          <div
            className="px-3 py-1 rounded-full text-xs font-display"
            style={{
              background: `${synergyColors.combo.color}20`,
              border: `1px solid ${synergyColors.combo.color}40`,
              color: synergyColors.combo.color,
            }}
          >
            {totalCount} {totalCount === 1 ? "combo" : "combos"}
          </div>
        )}
      </header>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : totalCount === 0 ? (
          <EmptyState cardCount={cardNames.length} />
        ) : (
          <div className="space-y-4">
            {/* Complete combos section */}
            {completeCount > 0 && (
              <section>
                <SectionHeader
                  title="COMPLETE COMBOS"
                  count={completeCount}
                  isComplete={true}
                />
                <div className="space-y-3 mt-3">
                  {result?.combos?.map((combo) => (
                    <ComboTile
                      key={combo.id}
                      combo={combo}
                      isComplete={true}
                      isExpanded={expandedComboId === combo.id}
                      onToggle={() => toggleCombo(combo.id)}
                      onCardClick={handleCardClick}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Potential combos section */}
            {potentialCount > 0 && (
              <section className={completeCount > 0 ? "mt-6" : ""}>
                <SectionHeader
                  title="POTENTIAL COMBOS"
                  count={potentialCount}
                  isComplete={false}
                />
                <div className="space-y-3 mt-3">
                  {result?.potential_combos?.map((combo) => (
                    <ComboTile
                      key={combo.id}
                      combo={combo}
                      isComplete={false}
                      missingCards={result?.missing_cards?.[combo.id]}
                      isExpanded={expandedComboId === combo.id}
                      onToggle={() => toggleCombo(combo.id)}
                      onCardClick={handleCardClick}
                    />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>

      {/* Card detail modal */}
      {selectedCardName && (
        <CardDetailModal
          cardName={selectedCardName}
          onClose={() => setSelectedCardName(null)}
        />
      )}
    </div>
  );
}

// Section header component
function SectionHeader({
  title,
  count,
  isComplete,
}: {
  title: string;
  count: number;
  isComplete: boolean;
}): ReactNode {
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-2 h-2 rounded-full"
        style={{
          background: isComplete
            ? synergyColors.combo.color
            : colors.text.muted,
          boxShadow: isComplete
            ? `0 0 8px ${synergyColors.combo.glow}`
            : "none",
        }}
      />
      <span
        className="text-xs font-display tracking-wider"
        style={{
          color: isComplete ? synergyColors.combo.color : colors.text.muted,
        }}
      >
        {title}
      </span>
      <span
        className="px-1.5 py-0.5 rounded text-xs"
        style={{
          background: colors.void.lighter,
          color: colors.text.dim,
        }}
      >
        {count}
      </span>
    </div>
  );
}

// Combo tile component
function ComboTile({
  combo,
  isComplete,
  missingCards,
  isExpanded,
  onToggle,
  onCardClick,
}: {
  combo: Combo;
  isComplete: boolean;
  missingCards?: string[];
  isExpanded: boolean;
  onToggle: () => void;
  onCardClick: (name: string) => void;
}): ReactNode {
  const typeConfig = COMBO_TYPE_CONFIG[combo.combo_type];
  const colorIcons = getColorIcons(combo.colors);

  return (
    <div
      className="rounded-lg overflow-hidden transition-all duration-300"
      style={{
        background: isComplete
          ? `linear-gradient(135deg, ${colors.void.light} 0%, ${colors.void.medium} 100%)`
          : colors.void.medium,
        border: `1px solid ${isComplete ? `${synergyColors.combo.color}40` : colors.border.subtle}`,
        boxShadow: isComplete
          ? `0 0 20px ${synergyColors.combo.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`
          : "none",
        animation: isComplete ? "combo-pulse 3s ease-in-out infinite" : "none",
      }}
    >
      {/* Combo header (clickable) */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-3 text-left transition-colors"
        style={{
          background: isExpanded ? "rgba(255,255,255,0.02)" : "transparent",
        }}
      >
        {/* Type badge */}
        <div
          className="w-8 h-8 rounded-md flex items-center justify-center shrink-0"
          style={{
            background: `${typeConfig.color}20`,
            border: `1px solid ${typeConfig.color}40`,
          }}
        >
          <i
            className={typeConfig.icon}
            style={{ color: typeConfig.color, fontSize: 14 }}
          />
        </div>

        {/* Combo info */}
        <div className="flex-1 min-w-0">
          {/* Card names preview */}
          <div className="flex items-center gap-1 flex-wrap">
            {combo.cards.slice(0, 3).map((card, idx) => (
              <span key={card.name}>
                <span
                  className="text-sm"
                  style={{
                    color: missingCards?.includes(card.name)
                      ? colors.text.muted
                      : colors.text.standard,
                    textDecoration: missingCards?.includes(card.name)
                      ? "line-through"
                      : "none",
                  }}
                >
                  {card.name}
                </span>
                {idx < Math.min(combo.cards.length, 3) - 1 && (
                  <span style={{ color: colors.text.muted }}> + </span>
                )}
              </span>
            ))}
            {combo.cards.length > 3 && (
              <span className="text-xs" style={{ color: colors.text.muted }}>
                +{combo.cards.length - 3} more
              </span>
            )}
          </div>

          {/* Type and colors */}
          <div className="flex items-center gap-2 mt-1">
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                background: `${typeConfig.color}20`,
                color: typeConfig.color,
              }}
            >
              {typeConfig.label}
            </span>
            {colorIcons.length > 0 && (
              <div className="flex items-center gap-0.5">
                {colorIcons.map((icon, idx) => (
                  <i
                    key={idx}
                    className={icon}
                    style={{ fontSize: 12, color: colors.text.dim }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Missing indicator */}
        {missingCards && missingCards.length > 0 && (
          <div
            className="px-2 py-1 rounded text-xs"
            style={{
              background: `${colors.status.warning}20`,
              border: `1px solid ${colors.status.warning}40`,
              color: colors.status.warning,
            }}
          >
            {missingCards.length} missing
          </div>
        )}

        {/* Expand/collapse indicator */}
        <div
          style={{
            color: colors.text.muted,
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div
          className="p-4 pt-0"
          style={{
            borderTop: `1px solid ${colors.border.subtle}`,
            animation: "reveal-up 0.3s ease-out",
          }}
        >
          {/* Description */}
          <p
            className="text-sm mb-4 pt-4"
            style={{ color: colors.text.dim, lineHeight: 1.6 }}
          >
            {combo.description}
          </p>

          {/* Card list with roles */}
          <div className="space-y-2">
            {combo.cards.map((card) => (
              <ComboCardRow
                key={card.name}
                card={card}
                isMissing={missingCards?.includes(card.name) ?? false}
                onClick={() => onCardClick(card.name)}
              />
            ))}
          </div>

          {/* Missing cards callout */}
          {missingCards && missingCards.length > 0 && (
            <div
              className="mt-4 p-3 rounded-lg"
              style={{
                background: `${colors.status.warning}10`,
                border: `1px solid ${colors.status.warning}30`,
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <i
                  className="ms ms-ability-menace"
                  style={{ color: colors.status.warning, fontSize: 14 }}
                />
                <span
                  className="text-xs font-display"
                  style={{ color: colors.status.warning }}
                >
                  MISSING CARDS
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {missingCards.map((name) => (
                  <button
                    key={name}
                    onClick={() => onCardClick(name)}
                    className="px-2 py-1 rounded text-xs transition-colors"
                    style={{
                      background: colors.void.lighter,
                      border: `1px solid ${colors.border.subtle}`,
                      color: colors.text.dim,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = colors.gold.dim;
                      e.currentTarget.style.color = colors.gold.standard;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = colors.border.subtle;
                      e.currentTarget.style.color = colors.text.dim;
                    }}
                  >
                    {name}
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

// Combo card row component
function ComboCardRow({
  card,
  isMissing,
  onClick,
}: {
  card: ComboCard;
  isMissing: boolean;
  onClick: () => void;
}): ReactNode {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-2 rounded-lg transition-all"
      style={{
        background: colors.void.light,
        border: `1px solid ${isMissing ? `${colors.status.warning}40` : colors.border.subtle}`,
        opacity: isMissing ? 0.7 : 1,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = colors.gold.dim;
        e.currentTarget.style.background = colors.void.lighter;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = isMissing
          ? `${colors.status.warning}40`
          : colors.border.subtle;
        e.currentTarget.style.background = colors.void.light;
      }}
    >
      {/* Status indicator */}
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{
          background: isMissing ? colors.status.warning : colors.status.success,
        }}
      />

      {/* Card name */}
      <span
        className="flex-1 text-left text-sm"
        style={{
          color: isMissing ? colors.text.muted : colors.text.standard,
          textDecoration: isMissing ? "line-through" : "none",
        }}
      >
        {card.name}
      </span>

      {/* Role */}
      <span
        className="text-xs px-2 py-0.5 rounded"
        style={{
          background: colors.void.medium,
          color: colors.text.muted,
        }}
      >
        {card.role}
      </span>

      {/* View indicator */}
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        style={{ color: colors.text.muted }}
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
    </button>
  );
}

// Loading state
function LoadingState(): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center py-12">
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center mb-4"
        style={{
          background: `${synergyColors.combo.color}20`,
          border: `1px solid ${synergyColors.combo.color}40`,
          boxShadow: `0 0 20px ${synergyColors.combo.glow}`,
          animation: "pulse-glow 1.5s ease-in-out infinite",
        }}
      >
        <i
          className="ms ms-instant"
          style={{ color: synergyColors.combo.color, fontSize: 24 }}
        />
      </div>
      <p className="text-sm font-display" style={{ color: colors.text.muted }}>
        DETECTING COMBOS...
      </p>
    </div>
  );
}

// Error state
function ErrorState({ message }: { message: string }): ReactNode {
  return (
    <div
      className="p-4 rounded-lg"
      style={{
        background: `${colors.status.error}10`,
        border: `1px solid ${colors.status.error}30`,
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <i
          className="ms ms-ability-menace"
          style={{ color: colors.status.error, fontSize: 14 }}
        />
        <span
          className="text-xs font-display"
          style={{ color: colors.status.error }}
        >
          ERROR
        </span>
      </div>
      <p className="text-sm" style={{ color: colors.text.dim }}>
        {message}
      </p>
    </div>
  );
}

// Empty state
function EmptyState({ cardCount }: { cardCount: number }): ReactNode {
  return (
    <div className="flex-1 flex flex-col items-center justify-center py-12 text-center">
      <div
        className="w-16 h-16 rounded-xl flex items-center justify-center mb-4"
        style={{
          background: colors.void.medium,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        <i
          className="ms ms-instant"
          style={{ fontSize: 28, color: colors.text.muted, opacity: 0.5 }}
        />
      </div>
      <h3
        className="font-display text-sm mb-2"
        style={{ color: colors.text.dim }}
      >
        NO COMBOS DETECTED
      </h3>
      <p className="text-xs max-w-xs" style={{ color: colors.text.muted }}>
        {cardCount === 0
          ? "Add cards to your deck to detect potential combos."
          : "No known combos found with the current card selection. Try adding more cards."}
      </p>
    </div>
  );
}

export default ComboDetectionPanel;
