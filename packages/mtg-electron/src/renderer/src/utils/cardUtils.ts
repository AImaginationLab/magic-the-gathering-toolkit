/**
 * Shared utility functions for card formatting, pricing, and categorization.
 * Extracted from CollectionScreen and DeckBuilderScreen to reduce duplication.
 */

import { colors } from "../theme";

/**
 * Get display color based on card rarity.
 */
export function getNameColorForRarity(
  rarity: string | null | undefined,
): string {
  if (!rarity) return colors.text.standard;
  switch (rarity.toLowerCase()) {
    case "mythic":
      return colors.rarity.mythic.color;
    case "rare":
      return colors.rarity.rare.color;
    case "uncommon":
      return colors.rarity.uncommon.color;
    default:
      return colors.text.standard;
  }
}

/**
 * Format price for display with appropriate precision.
 */
export function formatPrice(price: number | null | undefined): string {
  if (price == null || price === 0) return "";
  if (price < 1) return `$${price.toFixed(2)}`;
  if (price < 10) return `$${price.toFixed(2)}`;
  return `$${price.toFixed(0)}`;
}

/**
 * Get color based on price tier (mythic/rare/gold/standard/muted).
 */
export function getPriceColor(price: number | null | undefined): string {
  if (price == null) return colors.text.muted;
  if (price >= 50) return colors.rarity.mythic.color;
  if (price >= 20) return colors.rarity.rare.color;
  if (price >= 5) return colors.gold.standard;
  if (price >= 1) return colors.text.standard;
  return colors.text.muted;
}

/**
 * Categorize a card by its type for deck organization.
 */
export function getCardCategory(
  typeLine: string | null | undefined,
  isCommander: boolean = false,
): string {
  if (isCommander) return "Commander";
  if (!typeLine) return "Other";
  const t = typeLine.toLowerCase();
  if (t.includes("creature")) return "Creature";
  if (t.includes("planeswalker")) return "Planeswalker";
  if (t.includes("instant")) return "Instant";
  if (t.includes("sorcery")) return "Sorcery";
  if (t.includes("artifact")) return "Artifact";
  if (t.includes("enchantment")) return "Enchantment";
  if (t.includes("land")) return "Land";
  return "Other";
}

/**
 * Extract subtype from full type line (e.g., "Creature - Human Wizard" -> "Human Wizard").
 */
export function getSubtype(typeLine: string | null | undefined): string | null {
  if (!typeLine) return null;
  const dashIndex = typeLine.indexOf("—");
  if (dashIndex === -1) return null;
  return typeLine.substring(dashIndex + 1).trim();
}
