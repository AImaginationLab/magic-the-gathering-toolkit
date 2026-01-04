/**
 * MTG Spellbook Theme
 * Colors inspired by official MTG card frames and the mana-font project
 */

export const colors = {
  // Void - Deep backgrounds
  void: {
    deepest: "#08080c",
    deep: "#0c0c14",
    medium: "#14141f",
    light: "#1c1c2a",
    lighter: "#282838",
  },

  // Gold accent - Inspired by rare card frames
  gold: {
    bright: "#f0d060",
    standard: "#c9a227",
    dim: "#a08020",
    muted: "#786030",
    glow: "rgba(201, 162, 39, 0.4)",
  },

  // Mana colors - Based on official MTG mana symbols
  mana: {
    white: { color: "#fffcd6", glow: "rgba(255, 252, 214, 0.4)" },
    blue: { color: "#aae0fa", glow: "rgba(170, 224, 250, 0.4)" },
    black: { color: "#bab1ab", glow: "rgba(186, 177, 171, 0.4)" },
    red: { color: "#f9aa8f", glow: "rgba(249, 170, 143, 0.4)" },
    green: { color: "#9bd3ae", glow: "rgba(155, 211, 174, 0.4)" },
    colorless: { color: "#cbc2bf", glow: "rgba(203, 194, 191, 0.4)" },
  },

  // Rarity colors
  rarity: {
    mythic: { color: "#E67300", glow: "rgba(230, 115, 0, 0.5)" }, // Warm orange
    rare: { color: "#D4AF37", glow: "rgba(212, 175, 55, 0.4)" }, // Muted gold
    uncommon: { color: "#B8B8B8", glow: "rgba(184, 184, 184, 0.3)" }, // Silver
    common: { color: "#909090", glow: "rgba(144, 144, 144, 0.2)" }, // Gray
  },

  // Text hierarchy
  text: {
    bright: "#f0f0f0",
    standard: "#d0d0d0",
    dim: "#909090",
    muted: "#606060",
  },

  // Borders
  border: {
    subtle: "rgba(201, 162, 39, 0.1)",
    standard: "rgba(201, 162, 39, 0.2)",
    active: "rgba(201, 162, 39, 0.4)",
    bright: "rgba(201, 162, 39, 0.6)",
  },

  // Status
  status: {
    success: "#4CAF50", // Material green
    error: "#E54545", // Soft red
    warning: "#E5A020", // Warm amber
    info: "#4A9FD8", // Sky blue
  },

  // Positive/negative stat changes
  stats: {
    positive: "#4CAF50", // Material green - buffs
    negative: "#E54545", // Soft red - nerfs
    neutral: "#40C4D0", // Soft cyan
  },

  // Quality tier colors
  quality: {
    legendary: "#E67300", // Warm orange
    epic: "#9040C0", // Muted purple
    rare: "#4080D0", // Muted blue
    uncommon: "#50B050", // Muted green
  },
} as const;

// Synergy category colors
export const synergyColors = {
  keyword: { color: "#64b5f6", glow: "rgba(100, 181, 246, 0.4)" }, // Sky blue
  tribal: { color: "#81c784", glow: "rgba(129, 199, 132, 0.4)" }, // Soft green
  ability: { color: "#ba68c8", glow: "rgba(186, 104, 200, 0.4)" }, // Purple
  mana: { color: "#ffb74d", glow: "rgba(255, 183, 77, 0.4)" }, // Amber
  combo: { color: "#ff7043", glow: "rgba(255, 112, 67, 0.5)" }, // Deep orange
  strategy: { color: "#4dd0e1", glow: "rgba(77, 208, 225, 0.4)" }, // Cyan
} as const;

// Connection strength colors for synergy visualization
export const connectionColors = {
  weak: "rgba(201, 162, 39, 0.2)",
  moderate: "rgba(201, 162, 39, 0.4)",
  strong: "rgba(201, 162, 39, 0.7)",
  perfect: "rgba(240, 208, 96, 0.9)",
} as const;

// Gradients
export const gradients = {
  goldShimmer: `linear-gradient(135deg, ${colors.gold.bright} 0%, ${colors.gold.standard} 50%, ${colors.gold.dim} 100%)`,
  voidDepth: `linear-gradient(180deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
  synergyGlow: `radial-gradient(ellipse at center, rgba(201, 162, 39, 0.15) 0%, transparent 70%)`,
  comboHighlight: `linear-gradient(135deg, rgba(255, 112, 67, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%)`,
  deckSuggestion: `linear-gradient(180deg, rgba(100, 181, 246, 0.05) 0%, transparent 50%)`,
  mythicShimmer: `linear-gradient(90deg, transparent, rgba(230, 92, 0, 0.3), transparent)`,
} as const;

// Animation keyframe names (actual keyframes in index.css)
export const animations = {
  pulseGlow: "pulse-glow 2s ease-in-out infinite",
  flowLine: "flow-line 3s linear infinite",
  revealUp: "reveal-up 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
  shimmer: "shimmer 2s linear infinite",
  connectionPulse: "connection-pulse 1.5s ease-in-out infinite",
} as const;

// Shadows
export const shadows = {
  goldGlow: `0 0 8px ${colors.gold.glow}, 0 0 16px rgba(201, 162, 39, 0.2)`,
  goldGlowIntense: `0 0 12px ${colors.gold.glow}, 0 0 24px rgba(201, 162, 39, 0.3)`,
  voidShadow: "0 4px 16px rgba(0, 0, 0, 0.5)",
} as const;

export function getRarityColor(rarity: string): string {
  const r = rarity.toLowerCase();
  if (r in colors.rarity) {
    return colors.rarity[r as keyof typeof colors.rarity].color;
  }
  return colors.text.dim;
}

export function getManaColor(mana: string): string {
  const manaMap: Record<string, keyof typeof colors.mana> = {
    W: "white",
    U: "blue",
    B: "black",
    R: "red",
    G: "green",
    C: "colorless",
  };
  const key = manaMap[mana.toUpperCase()];
  return key ? colors.mana[key].color : colors.mana.colorless.color;
}
