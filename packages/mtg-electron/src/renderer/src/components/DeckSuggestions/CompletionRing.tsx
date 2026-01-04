/**
 * CompletionRing - Radial progress indicator for deck completion
 * Displays a circular progress ring with percentage and status label
 */

import { colors } from "../../theme";
import type { ReactNode } from "react";

interface CompletionRingProps {
  percent: number;
  size?: "small" | "medium" | "large";
  showLabel?: boolean;
  animated?: boolean;
}

const SIZES = {
  small: { outer: 48, stroke: 4, fontSize: 11, labelSize: 8 },
  medium: { outer: 72, stroke: 6, fontSize: 16, labelSize: 10 },
  large: { outer: 96, stroke: 8, fontSize: 20, labelSize: 12 },
};

function getCompletionColor(percent: number): string {
  if (percent >= 80) return colors.status.success;
  if (percent >= 50) return colors.status.warning;
  if (percent >= 20) return "#ff7043"; // Deep orange
  return colors.status.error;
}

function getStatusLabel(percent: number): string {
  if (percent >= 80) return "READY";
  if (percent >= 50) return "CLOSE";
  if (percent >= 20) return "STARTED";
  return "EARLY";
}

export function CompletionRing({
  percent,
  size = "medium",
  showLabel = true,
  animated = true,
}: CompletionRingProps): ReactNode {
  const config = SIZES[size];
  const radius = (config.outer - config.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const color = getCompletionColor(percent);
  const label = getStatusLabel(percent);

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: config.outer, height: config.outer }}
    >
      <svg
        width={config.outer}
        height={config.outer}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={config.outer / 2}
          cy={config.outer / 2}
          r={radius}
          fill="none"
          stroke={colors.void.lighter}
          strokeWidth={config.stroke}
        />
        {/* Progress circle */}
        <circle
          cx={config.outer / 2}
          cy={config.outer / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={config.stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{
            transition: animated ? "stroke-dashoffset 0.8s ease-out" : "none",
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-bold"
          style={{ fontSize: config.fontSize, color: colors.text.bright }}
        >
          {Math.round(percent)}%
        </span>
        {showLabel && (
          <span
            className="font-display tracking-wider"
            style={{ fontSize: config.labelSize, color }}
          >
            {label}
          </span>
        )}
      </div>

      {/* Pulse animation for high completion */}
      {percent >= 80 && animated && (
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: `2px solid ${color}`,
            animation: "pulse-glow 2s ease-in-out infinite",
            opacity: 0.5,
          }}
        />
      )}
    </div>
  );
}

export default CompletionRing;
