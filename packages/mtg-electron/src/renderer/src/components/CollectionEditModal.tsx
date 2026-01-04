import { useState, useCallback, useEffect } from "react";
import { colors } from "../theme";

import type { ReactNode } from "react";

interface CollectionCard {
  cardName: string;
  quantity: number;
  foilQuantity: number;
  setCode: string | null;
  setName: string | null;
  collectorNumber: string | null;
  addedAt: string;
  // Enriched data from card database
  colors: string[];
  typeLine: string | null;
  rarity: string | null;
  cmc: number;
  priceUsd: number | null;
  priceUsdFoil: number | null;
  // Gameplay stats
  winRate: number | null;
  tier: string | null;
  draftPick: number | null;
}

interface CollectionEditModalProps {
  card: CollectionCard;
  onClose: () => void;
  onSave: (updated: CollectionCard) => void;
  onDelete: () => void;
}

export function CollectionEditModal({
  card,
  onClose,
  onSave,
  onDelete,
}: CollectionEditModalProps): ReactNode {
  const [quantity, setQuantity] = useState(card.quantity);
  const [foilQuantity, setFoilQuantity] = useState(card.foilQuantity);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when card changes
  useEffect(() => {
    setQuantity(card.quantity);
    setFoilQuantity(card.foilQuantity);
    setShowDeleteConfirm(false);
    setError(null);
  }, [card]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        if (showDeleteConfirm) {
          setShowDeleteConfirm(false);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, showDeleteConfirm]);

  const handleSave = useCallback(async () => {
    // Validate quantities
    if (quantity < 0 || foilQuantity < 0) {
      setError("Quantities cannot be negative");
      return;
    }

    if (quantity === 0 && foilQuantity === 0) {
      // If both are zero, delete instead
      setShowDeleteConfirm(true);
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const result = await window.electronAPI.collection.update({
        cardName: card.cardName,
        setCode: card.setCode,
        collectorNumber: card.collectorNumber,
        quantity,
        foilQuantity,
      });

      if (result.success && result.card) {
        // Merge returned card with original's metadata (gameplay stats not returned by API)
        onSave({
          ...result.card,
          winRate: card.winRate,
          tier: card.tier,
          draftPick: card.draftPick,
        });
      } else {
        setError(result.error ?? "Failed to update card");
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setIsSaving(false);
    }
  }, [card, quantity, foilQuantity, onSave]);

  const handleDelete = useCallback(async () => {
    setIsDeleting(true);
    setError(null);

    try {
      const result = await window.electronAPI.collection.delete({
        cardName: card.cardName,
        setCode: card.setCode,
        collectorNumber: card.collectorNumber,
      });

      if (result.success) {
        onDelete();
      } else {
        setError(result.error ?? "Failed to delete card");
        setShowDeleteConfirm(false);
      }
    } catch (err) {
      setError(String(err));
      setShowDeleteConfirm(false);
    } finally {
      setIsDeleting(false);
    }
  }, [card, onDelete]);

  const handleBackdropClick = useCallback(() => {
    if (!showDeleteConfirm) {
      onClose();
    }
  }, [onClose, showDeleteConfirm]);

  const totalCards = quantity + foilQuantity;
  const hasChanges =
    quantity !== card.quantity || foilQuantity !== card.foilQuantity;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.8)" }}
      onClick={handleBackdropClick}
    >
      <div
        className="w-full max-w-md flex flex-col rounded-lg overflow-hidden"
        style={{
          background: colors.void.deep,
          border: `1px solid ${colors.border.subtle}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: colors.border.subtle }}
        >
          <h2
            className="font-display text-lg"
            style={{ color: colors.text.bright }}
          >
            Edit Card
          </h2>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 transition-colors"
            style={{ color: colors.text.muted }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {/* Card info */}
          <div
            className="mb-5 p-4 rounded"
            style={{
              background: colors.void.light,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            <div
              className="font-display text-base mb-1"
              style={{ color: colors.text.bright }}
            >
              {card.cardName}
            </div>
            {card.setCode && (
              <div
                className="flex items-center gap-2 text-sm"
                style={{ color: colors.text.muted }}
              >
                <i className={`ss ss-${card.setCode.toLowerCase()}`} />
                <span>
                  {card.setCode.toUpperCase()}
                  {card.collectorNumber && ` #${card.collectorNumber}`}
                </span>
              </div>
            )}
          </div>

          {/* Quantity controls */}
          <div className="space-y-4">
            {/* Regular quantity */}
            <div>
              <label
                className="block text-sm mb-2"
                style={{ color: colors.text.muted }}
              >
                Regular Copies
              </label>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setQuantity(Math.max(0, quantity - 1))}
                  className="w-10 h-10 flex items-center justify-center rounded text-xl font-bold transition-colors"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    color: colors.text.standard,
                  }}
                >
                  -
                </button>
                <input
                  type="number"
                  min="0"
                  value={quantity}
                  onChange={(e) =>
                    setQuantity(Math.max(0, parseInt(e.target.value) || 0))
                  }
                  className="w-20 h-10 text-center font-mono text-lg"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    borderRadius: "4px",
                    color: colors.text.bright,
                    outline: "none",
                  }}
                />
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="w-10 h-10 flex items-center justify-center rounded text-xl font-bold transition-colors"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    color: colors.text.standard,
                  }}
                >
                  +
                </button>
              </div>
            </div>

            {/* Foil quantity */}
            <div>
              <label
                className="block text-sm mb-2 flex items-center gap-2"
                style={{ color: colors.text.muted }}
              >
                <i
                  className="ms ms-dfc-spark"
                  style={{ color: colors.rarity.mythic.color }}
                />
                Foil Copies
              </label>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setFoilQuantity(Math.max(0, foilQuantity - 1))}
                  className="w-10 h-10 flex items-center justify-center rounded text-xl font-bold transition-colors"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    color: colors.text.standard,
                  }}
                >
                  -
                </button>
                <input
                  type="number"
                  min="0"
                  value={foilQuantity}
                  onChange={(e) =>
                    setFoilQuantity(Math.max(0, parseInt(e.target.value) || 0))
                  }
                  className="w-20 h-10 text-center font-mono text-lg"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    borderRadius: "4px",
                    color: colors.rarity.mythic.color,
                    outline: "none",
                  }}
                />
                <button
                  onClick={() => setFoilQuantity(foilQuantity + 1)}
                  className="w-10 h-10 flex items-center justify-center rounded text-xl font-bold transition-colors"
                  style={{
                    background: colors.void.light,
                    border: `1px solid ${colors.border.standard}`,
                    color: colors.text.standard,
                  }}
                >
                  +
                </button>
              </div>
            </div>
          </div>

          {/* Total display */}
          <div
            className="mt-5 pt-4 flex items-center justify-between"
            style={{ borderTop: `1px solid ${colors.border.subtle}` }}
          >
            <span className="text-sm" style={{ color: colors.text.muted }}>
              Total Cards
            </span>
            <span
              className="font-display text-xl"
              style={{ color: colors.gold.standard }}
            >
              {totalCards}
            </span>
          </div>

          {/* Error message */}
          {error && (
            <div
              className="mt-4 p-3 rounded text-sm"
              style={{
                background: "rgba(255,85,85,0.1)",
                border: "1px solid rgba(255,85,85,0.3)",
                color: "#ff5555",
              }}
            >
              {error}
            </div>
          )}

          {/* Delete confirmation */}
          {showDeleteConfirm && (
            <div
              className="mt-4 p-4 rounded"
              style={{
                background: "rgba(255,85,85,0.1)",
                border: "1px solid rgba(255,85,85,0.3)",
              }}
            >
              <div className="flex items-center gap-2 mb-3">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="#ff5555">
                  <path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z" />
                </svg>
                <span
                  className="font-display text-sm"
                  style={{ color: "#ff5555" }}
                >
                  Delete this card?
                </span>
              </div>
              <p className="text-xs mb-3" style={{ color: colors.text.muted }}>
                This will permanently remove {card.cardName} from your
                collection.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 px-3 py-2 text-sm font-display"
                  style={{
                    background: "transparent",
                    border: `1px solid ${colors.border.standard}`,
                    borderRadius: "3px",
                    color: colors.text.muted,
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="flex-1 px-3 py-2 text-sm font-display"
                  style={{
                    background: "#d32f2f",
                    borderRadius: "3px",
                    color: "white",
                    opacity: isDeleting ? 0.5 : 1,
                  }}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {!showDeleteConfirm && (
          <div
            className="flex items-center justify-between px-5 py-4 border-t"
            style={{ borderColor: colors.border.subtle }}
          >
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 font-display text-sm flex items-center gap-2"
              style={{
                background: "transparent",
                color: "#d32f2f",
                border: "none",
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                <path
                  fillRule="evenodd"
                  d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"
                />
              </svg>
              Delete
            </button>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 font-display text-sm"
                style={{
                  background: "transparent",
                  color: colors.text.muted,
                  border: `1px solid ${colors.border.standard}`,
                  borderRadius: "3px",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges || isSaving}
                className="px-4 py-2 font-display text-sm tracking-wide"
                style={{
                  background:
                    !hasChanges || isSaving
                      ? colors.text.muted
                      : colors.gold.standard,
                  color: colors.void.deepest,
                  borderRadius: "3px",
                  opacity: !hasChanges || isSaving ? 0.5 : 1,
                }}
              >
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CollectionEditModal;
