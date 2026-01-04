import { colors } from "../theme";
import type { ReactNode } from "react";

interface BulkActionsBarProps {
  selectedCount: number;
  onAddToDeck: () => void;
  onDelete: () => void;
  onClearSelection: () => void;
}

export function BulkActionsBar({
  selectedCount,
  onAddToDeck,
  onDelete,
  onClearSelection,
}: BulkActionsBarProps): ReactNode {
  if (selectedCount === 0) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50 flex items-center gap-4 px-6 py-3 rounded-lg"
      style={{
        background: colors.void.deep,
        border: `1px solid ${colors.gold.dim}`,
        boxShadow: `0 4px 20px rgba(0, 0, 0, 0.5), 0 0 20px ${colors.gold.glow}30`,
      }}
    >
      <span
        className="font-medium text-sm"
        style={{ color: colors.gold.standard }}
      >
        {selectedCount} card{selectedCount !== 1 ? "s" : ""} selected
      </span>

      <div className="w-px h-6" style={{ background: colors.border.subtle }} />

      <button
        onClick={onAddToDeck}
        className="flex items-center gap-2 px-4 py-2 rounded text-sm font-semibold transition-all"
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
        + Add to Deck
      </button>

      <button
        onClick={onDelete}
        className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-all"
        style={{
          background: "transparent",
          border: `1px solid ${colors.status.error}60`,
          color: colors.status.error,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = `${colors.status.error}20`;
          e.currentTarget.style.borderColor = colors.status.error;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.borderColor = `${colors.status.error}60`;
        }}
      >
        Delete
      </button>

      <button
        onClick={onClearSelection}
        className="px-3 py-2 rounded text-sm transition-all"
        style={{
          background: "transparent",
          color: colors.text.muted,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = colors.text.standard;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = colors.text.muted;
        }}
      >
        Clear
      </button>
    </div>
  );
}

export default BulkActionsBar;
