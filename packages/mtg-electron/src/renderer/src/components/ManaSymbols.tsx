import type { ReactNode } from "react";

import { colors, getManaColor } from "../theme";

/**
 * Parse mana cost string like "{2}{U}{B}" into individual symbols.
 */
export function parseManaSymbols(manaCost: string | null): string[] {
  if (!manaCost) return [];
  const matches = manaCost.match(/\{([^}]+)\}/g);
  if (!matches) return [];
  return matches.map((m) => m.slice(1, -1));
}

interface ManaSymbolProps {
  symbol: string;
  size?: "small" | "medium" | "large";
}

/**
 * Render a single mana symbol as a styled badge.
 * Supports: basic mana (W,U,B,R,G,C), colorless numbers, X, hybrid (W/U),
 * phyrexian (W/P), snow (S), and tap (T).
 */
export function ManaSymbol({
  symbol,
  size = "medium",
}: ManaSymbolProps): ReactNode {
  const upperSymbol = symbol.toUpperCase();

  // Size configurations
  const sizeConfig = {
    small: { width: 16, height: 16, fontSize: 10 },
    medium: { width: 20, height: 20, fontSize: 12 },
    large: { width: 26, height: 26, fontSize: 14 },
  };

  const { width, height, fontSize } = sizeConfig[size];

  // Get background color for the symbol
  const getSymbolStyle = (): { bg: string; text: string } => {
    // Basic mana colors
    if (upperSymbol === "W") return { bg: "#fffcd6", text: "#1a1a1a" };
    if (upperSymbol === "U") return { bg: "#aae0fa", text: "#1a1a1a" };
    if (upperSymbol === "B") return { bg: "#4a4247", text: "#ffffff" };
    if (upperSymbol === "R") return { bg: "#f9aa8f", text: "#1a1a1a" };
    if (upperSymbol === "G") return { bg: "#9bd3ae", text: "#1a1a1a" };
    if (upperSymbol === "C") return { bg: "#cbc2bf", text: "#1a1a1a" };

    // Snow mana
    if (upperSymbol === "S") return { bg: "#b8e0f0", text: "#1a1a1a" };

    // X and other generic costs
    if (upperSymbol === "X") return { bg: "#888888", text: "#ffffff" };

    // Tap symbol
    if (upperSymbol === "T") return { bg: "#888888", text: "#ffffff" };

    // Numeric costs (colorless)
    if (/^\d+$/.test(upperSymbol)) return { bg: "#888888", text: "#ffffff" };

    // Hybrid mana (e.g., W/U, 2/W)
    if (upperSymbol.includes("/")) {
      const [a, b] = upperSymbol.split("/");

      // Phyrexian mana (e.g., W/P, U/P)
      if (b === "P") {
        const baseColor = getManaColor(a);
        return { bg: baseColor, text: "#1a1a1a" };
      }

      // Two-color hybrid - use gradient
      return {
        bg: `linear-gradient(135deg, ${getManaColor(a)} 50%, ${getManaColor(b)} 50%)`,
        text: "#1a1a1a",
      };
    }

    // Default fallback
    return { bg: "#888888", text: "#ffffff" };
  };

  const { bg, text } = getSymbolStyle();

  // Display text for the symbol
  const getDisplayText = (): string => {
    if (/^\d+$/.test(upperSymbol)) return upperSymbol;
    if (upperSymbol === "X") return "X";
    if (upperSymbol === "T") return "T";
    if (upperSymbol === "S") return "S";

    // Hybrid mana
    if (upperSymbol.includes("/")) {
      const [a, b] = upperSymbol.split("/");
      if (b === "P") return a; // Phyrexian - show base color letter
      return ""; // Two-color hybrid - show split colors
    }

    // Single letter mana
    return upperSymbol;
  };

  const displayText = getDisplayText();
  const isPhyrexian = upperSymbol.includes("/P");

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width,
        height,
        borderRadius: "50%",
        background: bg,
        color: text,
        fontSize,
        fontWeight: 700,
        fontFamily: "system-ui, sans-serif",
        boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
        border: "1px solid rgba(0,0,0,0.2)",
        position: "relative",
      }}
      title={symbol}
    >
      {displayText}
      {isPhyrexian && (
        <span
          style={{
            position: "absolute",
            fontSize: fontSize * 0.6,
            bottom: -2,
            right: -2,
            color: colors.status.error,
          }}
        >
          P
        </span>
      )}
    </span>
  );
}

interface ManaCostProps {
  cost: string | null;
  size?: "small" | "medium" | "large";
}

/**
 * Render a full mana cost string as a series of mana symbols.
 */
export function ManaCost({ cost, size = "medium" }: ManaCostProps): ReactNode {
  const symbols = parseManaSymbols(cost);

  if (symbols.length === 0) return null;

  return (
    <span style={{ display: "inline-flex", gap: 2, alignItems: "center" }}>
      {symbols.map((symbol, index) => (
        <ManaSymbol key={index} symbol={symbol} size={size} />
      ))}
    </span>
  );
}

interface CardTextProps {
  text: string;
  size?: "small" | "medium" | "large";
}

/**
 * Render card text with inline mana symbols.
 * Parses {X}, {W}, {U}, {B}, {R}, {G}, {C}, {T}, {1}, {2}, etc. and renders them as symbols.
 */
export function CardText({ text, size = "small" }: CardTextProps): ReactNode {
  // Split text by mana symbols, keeping the delimiters
  const parts = text.split(/(\{[^}]+\})/g);

  return (
    <span style={{ display: "inline" }}>
      {parts.map((part, index) => {
        // Check if this part is a mana symbol
        const match = part.match(/^\{([^}]+)\}$/);
        if (match) {
          return <ManaSymbol key={index} symbol={match[1]} size={size} />;
        }
        // Regular text - preserve line breaks
        return (
          <span key={index} style={{ whiteSpace: "pre-wrap" }}>
            {part}
          </span>
        );
      })}
    </span>
  );
}

export default ManaCost;
