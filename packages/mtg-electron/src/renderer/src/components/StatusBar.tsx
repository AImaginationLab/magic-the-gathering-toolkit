import { colors } from "../theme";

import type { ReactNode } from "react";

export type ApiStatus = "ready" | "starting" | "offline" | "error";

interface StatusBarProps {
  cardCount: number;
  setCount: number;
  collectionCount: number;
  collectionValue: number;
  apiStatus: ApiStatus;
}

function getStatusColor(status: ApiStatus): string {
  switch (status) {
    case "ready":
      return colors.status.success;
    case "starting":
      return colors.status.warning;
    case "offline":
    case "error":
      return colors.status.error;
  }
}

function getStatusLabel(status: ApiStatus): string {
  switch (status) {
    case "ready":
      return "API Ready";
    case "starting":
      return "Starting...";
    case "offline":
      return "Offline";
    case "error":
      return "Error";
  }
}

export function StatusBar({
  cardCount,
  setCount,
  collectionCount,
  collectionValue,
  apiStatus,
}: StatusBarProps): ReactNode {
  const formatNumber = (n: number): string => n.toLocaleString();
  const formatPrice = (n: number): string =>
    `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const statusColor = getStatusColor(apiStatus);
  const statusLabel = getStatusLabel(apiStatus);

  return (
    <footer
      className="h-8 flex items-center px-4 text-xs font-mono"
      style={{
        background: colors.void.deep,
        borderTop: `1px solid ${colors.border.subtle}`,
        color: colors.text.muted,
      }}
    >
      {/* Stats section */}
      <div className="flex items-center gap-4 flex-1">
        <span>
          <span style={{ color: colors.gold.standard }}>
            {formatNumber(cardCount)}
          </span>{" "}
          cards
        </span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>
          <span style={{ color: colors.gold.standard }}>
            {formatNumber(setCount)}
          </span>{" "}
          sets
        </span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>
          <span style={{ color: colors.mana.green.color }}>
            {formatNumber(collectionCount)}
          </span>{" "}
          owned
        </span>
        {collectionValue > 0 && (
          <>
            <span style={{ opacity: 0.3 }}>|</span>
            <span>
              <span style={{ color: colors.rarity.mythic.color }}>
                {formatPrice(collectionValue)}
              </span>{" "}
              value
            </span>
          </>
        )}
      </div>

      {/* API status indicator - only show when not ready */}
      {apiStatus !== "ready" && (
        <div className="flex items-center gap-2">
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{
              backgroundColor: statusColor,
            }}
          />
          <span style={{ color: statusColor }}>{statusLabel}</span>
        </div>
      )}
    </footer>
  );
}

export default StatusBar;
