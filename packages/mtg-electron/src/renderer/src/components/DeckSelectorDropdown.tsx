import { useState, useEffect } from "react";
import { colors } from "../theme";
import type { ReactNode } from "react";
import type { components } from "../../../shared/types/api-generated";

type DeckSummaryResponse = components["schemas"]["DeckSummaryResponse"];

// Card info for bulk quantity selection
export interface BulkCardSelection {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
  availableQuantity: number; // Total available in collection
  selectedQuantity: number; // How many to add (default: all)
  enabled: boolean; // Whether this printing is enabled for adding
}

interface DeckSelectorDropdownProps {
  onSelect: (
    deckId: number,
    deckName: string,
    quantities?: Map<string, number>,
  ) => void;
  onCancel: () => void;
  defaultDeckId?: number | null;
  cardCount?: number;
  // For bulk mode with quantity selection
  bulkCards?: BulkCardSelection[];
}

// Generate unique key for a card
function getCardKey(
  cardName: string,
  setCode: string | null,
  collectorNumber: string | null,
): string {
  if (setCode && collectorNumber) {
    return `${cardName}|${setCode.toUpperCase()}|${collectorNumber}`;
  }
  return cardName;
}

export function DeckSelectorDropdown({
  onSelect,
  onCancel,
  defaultDeckId,
  cardCount = 1,
  bulkCards,
}: DeckSelectorDropdownProps): ReactNode {
  // Local state for quantity editing
  const [editableCards, setEditableCards] = useState<BulkCardSelection[]>(
    bulkCards ?? [],
  );
  const [decks, setDecks] = useState<DeckSummaryResponse[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(
    defaultDeckId ?? null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDecks(): Promise<void> {
      setIsLoading(true);
      setError(null);
      try {
        const deckList = await window.electronAPI.decks.list();
        setDecks(deckList);
        // If no default and we have decks, select the first one
        if (!defaultDeckId && deckList.length > 0) {
          setSelectedDeckId(deckList[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load decks");
      } finally {
        setIsLoading(false);
      }
    }
    loadDecks();
  }, [defaultDeckId]);

  // Sync local state when bulkCards changes
  useEffect(() => {
    if (bulkCards) {
      setEditableCards(bulkCards);
    }
  }, [bulkCards]);

  const handleQuantityChange = (cardKey: string, newQuantity: number): void => {
    setEditableCards((prev) =>
      prev.map((card) => {
        const key = getCardKey(
          card.cardName,
          card.setCode,
          card.collectorNumber,
        );
        if (key === cardKey) {
          const clamped = Math.max(
            1,
            Math.min(newQuantity, card.availableQuantity),
          );
          return { ...card, selectedQuantity: clamped };
        }
        return card;
      }),
    );
  };

  const handleToggleEnabled = (cardKey: string): void => {
    setEditableCards((prev) =>
      prev.map((card) => {
        const key = getCardKey(
          card.cardName,
          card.setCode,
          card.collectorNumber,
        );
        if (key === cardKey) {
          return { ...card, enabled: !card.enabled };
        }
        return card;
      }),
    );
  };

  const handleConfirm = (): void => {
    if (selectedDeckId !== null) {
      const deck = decks.find((d) => d.id === selectedDeckId);
      // Build quantities map if in bulk mode - only include enabled cards
      if (editableCards.length > 0) {
        const quantities = new Map<string, number>();
        for (const card of editableCards) {
          if (card.enabled) {
            const key = getCardKey(
              card.cardName,
              card.setCode,
              card.collectorNumber,
            );
            quantities.set(key, card.selectedQuantity);
          }
        }
        onSelect(selectedDeckId, deck?.name ?? "Unknown Deck", quantities);
      } else {
        onSelect(selectedDeckId, deck?.name ?? "Unknown Deck");
      }
    }
  };

  // Only count enabled cards for the total
  const enabledCards = editableCards.filter((c) => c.enabled);
  const totalCardsToAdd = enabledCards.reduce(
    (sum, c) => sum + c.selectedQuantity,
    0,
  );

  const selectedDeck = decks.find((d) => d.id === selectedDeckId);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        style={{
          background: colors.void.deep,
          border: `1px solid ${colors.border.standard}`,
          borderRadius: 8,
          padding: 24,
          minWidth: 320,
          maxWidth: 400,
        }}
      >
        <h3
          style={{
            margin: "0 0 16px 0",
            color: colors.text.bright,
            fontSize: 18,
            fontWeight: 600,
          }}
        >
          Add to Deck
        </h3>

        {isLoading && (
          <div style={{ color: colors.text.muted, padding: "16px 0" }}>
            Loading decks...
          </div>
        )}

        {error && (
          <div
            style={{
              color: colors.status.error,
              padding: "12px",
              background: `${colors.status.error}20`,
              borderRadius: 4,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        {!isLoading && !error && decks.length === 0 && (
          <div style={{ color: colors.text.muted, padding: "16px 0" }}>
            No decks found. Create a deck first.
          </div>
        )}

        {!isLoading && decks.length > 0 && (
          <>
            <select
              value={selectedDeckId ?? ""}
              onChange={(e) => setSelectedDeckId(Number(e.target.value))}
              style={{
                width: "100%",
                padding: "10px 12px",
                background: colors.void.medium,
                border: `1px solid ${colors.border.standard}`,
                borderRadius: 4,
                color: colors.text.bright,
                fontSize: 14,
                marginBottom: 12,
                cursor: "pointer",
              }}
            >
              {decks.map((deck) => (
                <option key={deck.id} value={deck.id}>
                  {deck.name} ({deck.card_count} cards)
                  {deck.format ? ` - ${deck.format}` : ""}
                </option>
              ))}
            </select>

            {selectedDeck && (
              <div
                style={{
                  padding: "8px 12px",
                  background: colors.void.lighter,
                  borderRadius: 4,
                  marginBottom: 16,
                  fontSize: 13,
                }}
              >
                <div style={{ color: colors.text.dim }}>
                  <span style={{ color: colors.text.muted }}>Format: </span>
                  {selectedDeck.format ?? "None"}
                </div>
                {selectedDeck.commander && (
                  <div style={{ color: colors.text.dim, marginTop: 4 }}>
                    <span style={{ color: colors.text.muted }}>
                      Commander:{" "}
                    </span>
                    {selectedDeck.commander}
                  </div>
                )}
                <div style={{ color: colors.text.dim, marginTop: 4 }}>
                  <span style={{ color: colors.text.muted }}>Cards: </span>
                  {selectedDeck.card_count} main
                  {selectedDeck.sideboard_count > 0 &&
                    ` + ${selectedDeck.sideboard_count} sideboard`}
                </div>
              </div>
            )}

            {/* Card selection with checkboxes and quantity controls */}
            {editableCards.length > 0 && (
              <div
                style={{
                  maxHeight: 250,
                  overflowY: "auto",
                  marginBottom: 16,
                  padding: "8px 0",
                  borderTop: `1px solid ${colors.border.subtle}`,
                  borderBottom: `1px solid ${colors.border.subtle}`,
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: colors.text.muted,
                    marginBottom: 8,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Select cards & quantities:
                </div>
                {editableCards.map((card) => {
                  const key = getCardKey(
                    card.cardName,
                    card.setCode,
                    card.collectorNumber,
                  );
                  return (
                    <div
                      key={key}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 0",
                        borderBottom: `1px solid ${colors.border.subtle}20`,
                        opacity: card.enabled ? 1 : 0.5,
                      }}
                    >
                      {/* Checkbox to enable/disable this printing */}
                      <input
                        type="checkbox"
                        checked={card.enabled}
                        onChange={() => handleToggleEnabled(key)}
                        style={{
                          width: 16,
                          height: 16,
                          cursor: "pointer",
                          accentColor: colors.gold.standard,
                        }}
                      />
                      <div
                        style={{
                          flex: 1,
                          fontSize: 13,
                          color: card.enabled
                            ? colors.text.standard
                            : colors.text.muted,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {card.cardName}
                        {card.setCode && (
                          <span
                            style={{ color: colors.text.dim, marginLeft: 6 }}
                          >
                            {card.setCode.toUpperCase()}
                            {card.collectorNumber &&
                              ` #${card.collectorNumber}`}
                          </span>
                        )}
                      </div>
                      {/* Quantity controls - only show if qty > 1 */}
                      {card.availableQuantity > 1 ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <button
                            onClick={() =>
                              handleQuantityChange(
                                key,
                                card.selectedQuantity - 1,
                              )
                            }
                            disabled={
                              !card.enabled || card.selectedQuantity <= 1
                            }
                            style={{
                              width: 22,
                              height: 22,
                              border: `1px solid ${colors.border.standard}`,
                              borderRadius: 4,
                              background: colors.void.medium,
                              color:
                                !card.enabled || card.selectedQuantity <= 1
                                  ? colors.text.muted
                                  : colors.text.standard,
                              cursor:
                                !card.enabled || card.selectedQuantity <= 1
                                  ? "not-allowed"
                                  : "pointer",
                              fontSize: 12,
                              fontWeight: 600,
                            }}
                          >
                            −
                          </button>
                          <input
                            type="number"
                            min={1}
                            max={card.availableQuantity}
                            value={card.selectedQuantity}
                            disabled={!card.enabled}
                            onChange={(e) =>
                              handleQuantityChange(
                                key,
                                parseInt(e.target.value) || 1,
                              )
                            }
                            style={{
                              width: 40,
                              padding: "2px 4px",
                              textAlign: "center",
                              background: colors.void.medium,
                              border: `1px solid ${colors.border.standard}`,
                              borderRadius: 4,
                              color: card.enabled
                                ? colors.text.bright
                                : colors.text.muted,
                              fontSize: 12,
                            }}
                          />
                          <button
                            onClick={() =>
                              handleQuantityChange(
                                key,
                                card.selectedQuantity + 1,
                              )
                            }
                            disabled={
                              !card.enabled ||
                              card.selectedQuantity >= card.availableQuantity
                            }
                            style={{
                              width: 22,
                              height: 22,
                              border: `1px solid ${colors.border.standard}`,
                              borderRadius: 4,
                              background: colors.void.medium,
                              color:
                                !card.enabled ||
                                card.selectedQuantity >= card.availableQuantity
                                  ? colors.text.muted
                                  : colors.text.standard,
                              cursor:
                                !card.enabled ||
                                card.selectedQuantity >= card.availableQuantity
                                  ? "not-allowed"
                                  : "pointer",
                              fontSize: 12,
                              fontWeight: 600,
                            }}
                          >
                            +
                          </button>
                          <span
                            style={{
                              fontSize: 10,
                              color: colors.text.dim,
                              minWidth: 28,
                            }}
                          >
                            /{card.availableQuantity}
                          </span>
                        </div>
                      ) : (
                        <span
                          style={{
                            fontSize: 12,
                            color: colors.text.dim,
                            minWidth: 28,
                          }}
                        >
                          1x
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            <div
              style={{
                fontSize: 13,
                color: colors.text.muted,
                marginBottom: 16,
              }}
            >
              Adding {editableCards.length > 0 ? totalCardsToAdd : cardCount}{" "}
              card
              {(editableCards.length > 0 ? totalCardsToAdd : cardCount) !== 1
                ? "s"
                : ""}{" "}
              to this deck
            </div>
          </>
        )}

        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "flex-end",
          }}
        >
          <button
            onClick={onCancel}
            style={{
              padding: "8px 16px",
              background: "transparent",
              border: `1px solid ${colors.border.standard}`,
              borderRadius: 4,
              color: colors.text.dim,
              fontSize: 14,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = colors.text.dim;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = colors.border.standard;
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={selectedDeckId === null || decks.length === 0}
            style={{
              padding: "8px 16px",
              background:
                selectedDeckId === null || decks.length === 0
                  ? colors.void.lighter
                  : colors.gold.standard,
              border: "none",
              borderRadius: 4,
              color:
                selectedDeckId === null || decks.length === 0
                  ? colors.text.muted
                  : colors.void.deepest,
              fontSize: 14,
              fontWeight: 600,
              cursor:
                selectedDeckId === null || decks.length === 0
                  ? "not-allowed"
                  : "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (selectedDeckId !== null && decks.length > 0) {
                e.currentTarget.style.background = colors.gold.bright;
              }
            }}
            onMouseLeave={(e) => {
              if (selectedDeckId !== null && decks.length > 0) {
                e.currentTarget.style.background = colors.gold.standard;
              }
            }}
          >
            Add to Deck
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeckSelectorDropdown;
