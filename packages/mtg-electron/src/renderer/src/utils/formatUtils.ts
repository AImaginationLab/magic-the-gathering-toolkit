/**
 * Shared utilities for MTG format styling (colors, glows, icons).
 * Single source of truth for format-related UI configuration.
 */
import { colors } from "../theme";

export interface FormatConfig {
  color: string;
  glow: string;
  icon: string;
}

/**
 * Configuration for all supported MTG formats.
 * Add new formats here to have them automatically available across the app.
 */
export const FORMAT_CONFIG: Record<string, FormatConfig> = {
  commander: {
    color: "#ff6b35",
    glow: "rgba(255, 107, 53, 0.6)",
    icon: "ms-commander",
  },
  standard: {
    color: "#f0f0f0",
    glow: "rgba(240, 240, 240, 0.4)",
    icon: "ms-ability-hexproof",
  },
  modern: {
    color: "#4a9eff",
    glow: "rgba(74, 158, 255, 0.6)",
    icon: "ms-ability-flash",
  },
  legacy: {
    color: "#ffd700",
    glow: "rgba(255, 215, 0, 0.6)",
    icon: "ms-saga",
  },
  vintage: {
    color: "#ff4500",
    glow: "rgba(255, 69, 0, 0.6)",
    icon: "ms-power",
  },
  pioneer: {
    color: "#32cd32",
    glow: "rgba(50, 205, 50, 0.6)",
    icon: "ms-ability-trample",
  },
  pauper: {
    color: "#a0a0a0",
    glow: "rgba(160, 160, 160, 0.4)",
    icon: "ms-common",
  },
  historic: {
    color: "#9370db",
    glow: "rgba(147, 112, 219, 0.6)",
    icon: "ms-historic",
  },
  brawl: {
    color: "#ff69b4",
    glow: "rgba(255, 105, 180, 0.6)",
    icon: "ms-ability-vigilance",
  },
};

/**
 * Get the accent color for a format.
 */
export function getFormatColor(format: string | null): string {
  if (!format) return colors.text.muted;
  const config = FORMAT_CONFIG[format.toLowerCase()];
  return config?.color ?? colors.text.dim;
}

/**
 * Get the glow/shadow color for a format (for hover effects, highlights).
 */
export function getFormatGlow(format: string | null): string {
  if (!format) return "transparent";
  const config = FORMAT_CONFIG[format.toLowerCase()];
  return config?.glow ?? "transparent";
}

/**
 * Get the mana-font icon class for a format.
 */
export function getFormatIcon(format: string | null): string {
  if (!format) return "ms-ability-menace";
  const config = FORMAT_CONFIG[format.toLowerCase()];
  return config?.icon ?? "ms-ability-menace";
}

/**
 * List of all supported format names (for dropdowns, filters, etc.)
 */
export const SUPPORTED_FORMATS = Object.keys(FORMAT_CONFIG);
