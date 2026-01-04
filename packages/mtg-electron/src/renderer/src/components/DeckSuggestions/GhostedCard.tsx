/**
 * GhostedCard - Missing card placeholder with silhouette styling
 * Shows cards the user needs to complete a deck
 */

import { colors } from "../../theme";
import type { ReactNode } from "react";

interface GhostedCardProps {
  name: string;
  price?: number | null;
  reason?: string;
  onClick?: () => void;
}

export function GhostedCard({ name, price, reason, onClick }: GhostedCardProps): ReactNode {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center p-2 rounded-lg transition-all group"
      style={{
        background: `${colors.void.lighter}50`,
        border: `2px dashed ${colors.border.standard}`,
        minWidth: 80,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = colors.status.warning;
        e.currentTarget.style.background = `${colors.status.warning}10`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = colors.border.standard;
        e.currentTarget.style.background = `${colors.void.lighter}50`;
      }}
    >
      {/* Card silhouette */}
      <div
        className="w-12 h-16 rounded flex items-center justify-center mb-1.5"
        style={{
          background: colors.void.medium,
          border: `1px dashed ${colors.border.subtle}`,
        }}
      >
        <svg
          width="24"
          height="32"
          viewBox="0 0 24 32"
          fill="none"
          style={{ opacity: 0.3 }}
        >
          {/* Simple card outline */}
          <rect
            x="2"
            y="2"
            width="20"
            height="28"
            rx="2"
            stroke={colors.text.muted}
            strokeWidth="1.5"
            strokeDasharray="3 2"
          />
          {/* Question mark */}
          <text
            x="12"
            y="20"
            textAnchor="middle"
            fill={colors.text.muted}
            fontSize="14"
            fontWeight="bold"
          >
            ?
          </text>
        </svg>
      </div>

      {/* Card name */}
      <span
        className="text-xs text-center line-clamp-2 group-hover:text-current transition-colors"
        style={{ color: colors.text.muted, maxWidth: 80 }}
        title={name}
      >
        {name}
      </span>

      {/* Price */}
      {price !== undefined && price !== null && (
        <span
          className="text-xs font-mono mt-0.5"
          style={{ color: colors.status.warning }}
        >
          ${price.toFixed(2)}
        </span>
      )}

      {/* Reason tooltip on hover */}
      {reason && (
        <span
          className="text-xs mt-1 opacity-0 group-hover:opacity-100 transition-opacity text-center"
          style={{ color: colors.text.dim, maxWidth: 80 }}
        >
          {reason}
        </span>
      )}
    </button>
  );
}

export default GhostedCard;
