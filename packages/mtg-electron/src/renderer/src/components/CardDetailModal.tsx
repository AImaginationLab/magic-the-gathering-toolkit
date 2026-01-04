import { useState, useEffect, useCallback } from "react";

import { colors, getRarityColor } from "../theme";
import { ManaCost, CardText } from "./ManaSymbols";
import { DeckSelectorDropdown } from "./DeckSelectorDropdown";

import type { ReactNode, MouseEvent } from "react";
import type {
  CardDetail,
  RulingEntry,
  PrintingInfo,
} from "../../../shared/types/api";
import type { components } from "../../../shared/types/api-generated";

// Combo types from generated schema
type Combo = components["schemas"]["Combo"];
type ComboType = Combo["combo_type"];

interface CardDetailModalProps {
  cardName: string;
  setCode?: string | null;
  collectorNumber?: string | null;
  onClose: () => void;
  onOpenGallery?: (cardName: string) => void;
}

const FORMATS_TO_SHOW = [
  "standard",
  "modern",
  "legacy",
  "vintage",
  "commander",
  "pioneer",
  "pauper",
  "historic",
  "brawl",
];

function LegalityBadge({
  format,
  legality,
}: {
  format: string;
  legality: string;
}): ReactNode {
  const legalityLower = legality.toLowerCase();
  const isLegal = legalityLower === "legal";
  const isBanned = legalityLower === "banned";
  const isRestricted = legalityLower === "restricted";

  let bg: string = colors.void.lighter;
  let borderColor: string = colors.border.subtle;
  let textColor: string = colors.text.muted;

  if (isLegal) {
    bg = "rgba(76, 175, 80, 0.2)";
    borderColor = colors.status.success;
    textColor = colors.status.success;
  } else if (isBanned) {
    bg = "rgba(211, 47, 47, 0.2)";
    borderColor = colors.status.error;
    textColor = colors.status.error;
  } else if (isRestricted) {
    bg = "rgba(255, 152, 0, 0.2)";
    borderColor = colors.status.warning;
    textColor = colors.status.warning;
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        padding: "4px 8px",
        borderRadius: 4,
        background: bg,
        border: `1px solid ${borderColor}`,
      }}
    >
      <span style={{ color: textColor, fontSize: 11, fontWeight: 600 }}>
        {isLegal ? "✓" : isBanned ? "✗" : isRestricted ? "!" : "—"}
      </span>
      <span
        style={{
          color: colors.text.dim,
          fontSize: 11,
          textTransform: "capitalize",
        }}
      >
        {format}
      </span>
    </div>
  );
}

function RulingsSection({ rulings }: { rulings: RulingEntry[] }): ReactNode {
  const [isExpanded, setIsExpanded] = useState(false);

  if (rulings.length === 0) return null;

  const displayedRulings = isExpanded ? rulings : rulings.slice(0, 3);

  return (
    <div style={{ marginTop: 16 }}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: 0,
          marginBottom: 8,
        }}
      >
        <span
          style={{ color: colors.gold.standard, fontSize: 14, fontWeight: 600 }}
        >
          Rulings ({rulings.length})
        </span>
        <span style={{ color: colors.text.muted, fontSize: 12 }}>
          {isExpanded ? "▲ collapse" : "▼ expand"}
        </span>
      </button>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {displayedRulings.map((ruling, idx) => (
          <div
            key={idx}
            style={{
              padding: "8px 12px",
              background: colors.void.medium,
              borderRadius: 4,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            <div
              style={{
                color: colors.text.muted,
                fontSize: 11,
                marginBottom: 4,
              }}
            >
              {ruling.date}
            </div>
            <div
              style={{ color: colors.text.dim, fontSize: 13, lineHeight: 1.5 }}
            >
              {ruling.text}
            </div>
          </div>
        ))}

        {!isExpanded && rulings.length > 3 && (
          <button
            onClick={() => setIsExpanded(true)}
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.subtle}`,
              borderRadius: 4,
              padding: "6px 12px",
              cursor: "pointer",
              color: colors.text.dim,
              fontSize: 12,
            }}
          >
            Show {rulings.length - 3} more rulings...
          </button>
        )}
      </div>
    </div>
  );
}

// Combo type display configuration - using plain color strings
const COMBO_TYPE_CONFIG: Record<
  ComboType,
  { icon: string; label: string; color: string }
> = {
  infinite: { icon: "∞", label: "Infinite", color: "#ff7043" },
  value: { icon: "★", label: "Value", color: "#81c784" },
  lock: { icon: "🔒", label: "Lock", color: "#64b5f6" },
  win: { icon: "🏆", label: "Win", color: "#ffd700" },
};

interface CombosSectionProps {
  combos: Combo[];
  cardName: string;
  isLoading: boolean;
}

function CombosSection({
  combos,
  cardName,
  isLoading,
}: CombosSectionProps): ReactNode {
  const [isExpanded, setIsExpanded] = useState(false);

  if (isLoading) {
    return (
      <div style={{ marginTop: 16 }}>
        <span
          style={{
            color: colors.text.muted,
            fontSize: 13,
            fontStyle: "italic",
          }}
        >
          Loading combos...
        </span>
      </div>
    );
  }

  if (combos.length === 0) return null;

  const displayedCombos = isExpanded ? combos : combos.slice(0, 2);

  return (
    <div style={{ marginTop: 16 }}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: 0,
          marginBottom: 8,
        }}
      >
        <span style={{ color: "#ff7043", fontSize: 14, fontWeight: 600 }}>
          Known Combos ({combos.length})
        </span>
        <span style={{ color: colors.text.muted, fontSize: 12 }}>
          {isExpanded ? "▲ collapse" : "▼ expand"}
        </span>
      </button>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {displayedCombos.map((combo) => {
          const config = COMBO_TYPE_CONFIG[combo.combo_type];
          const otherCards = combo.cards
            .filter((c) => c.name.toLowerCase() !== cardName.toLowerCase())
            .map((c) => c.name);

          return (
            <div
              key={combo.id}
              style={{
                padding: "10px 12px",
                background: colors.void.medium,
                borderRadius: 6,
                border: `1px solid ${colors.border.subtle}`,
                borderLeft: `3px solid ${config.color}`,
              }}
            >
              {/* Combo type badge */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 6,
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "2px 8px",
                    background: `${config.color}20`,
                    border: `1px solid ${config.color}40`,
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    color: config.color,
                  }}
                >
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                </span>
                {combo.colors && combo.colors.length > 0 && (
                  <span
                    style={{
                      fontSize: 11,
                      color: colors.text.muted,
                      fontFamily: "monospace",
                    }}
                  >
                    {combo.colors.join("")}
                  </span>
                )}
              </div>

              {/* Combo description */}
              <div
                style={{
                  color: colors.text.dim,
                  fontSize: 13,
                  lineHeight: 1.5,
                  marginBottom: 8,
                }}
              >
                {combo.description}
              </div>

              {/* Other cards in combo */}
              {otherCards.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 6,
                    paddingTop: 6,
                    borderTop: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      color: colors.text.muted,
                      marginRight: 4,
                    }}
                  >
                    Combos with:
                  </span>
                  {otherCards.map((name) => (
                    <span
                      key={name}
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        background: colors.void.lighter,
                        border: `1px solid ${colors.border.standard}`,
                        borderRadius: 4,
                        fontSize: 11,
                        color: colors.text.standard,
                      }}
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {!isExpanded && combos.length > 2 && (
          <button
            onClick={() => setIsExpanded(true)}
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.subtle}`,
              borderRadius: 4,
              padding: "6px 12px",
              cursor: "pointer",
              color: colors.text.dim,
              fontSize: 12,
            }}
          >
            Show {combos.length - 2} more combos...
          </button>
        )}
      </div>
    </div>
  );
}

function ExternalLink({
  href,
  children,
}: {
  href: string | null;
  children: ReactNode;
}): ReactNode {
  if (!href) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => {
        e.preventDefault();
        window.electronAPI.openExternal(href);
      }}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "6px 12px",
        background: colors.void.lighter,
        border: `1px solid ${colors.border.standard}`,
        borderRadius: 4,
        color: colors.text.dim,
        fontSize: 12,
        textDecoration: "none",
        cursor: "pointer",
        transition: "all 0.15s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = colors.gold.standard;
        e.currentTarget.style.color = colors.gold.standard;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = colors.border.standard;
        e.currentTarget.style.color = colors.text.dim;
      }}
    >
      {children}
    </a>
  );
}

export function CardDetailModal({
  cardName,
  setCode,
  collectorNumber,
  onClose,
  onOpenGallery,
}: CardDetailModalProps): ReactNode {
  const [card, setCard] = useState<CardDetail | null>(null);
  const [rulings, setRulings] = useState<RulingEntry[]>([]);
  const [combos, setCombos] = useState<Combo[]>([]);
  const [printings, setPrintings] = useState<PrintingInfo[]>([]);
  const [currentPrintingIndex, setCurrentPrintingIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [combosLoading, setCombosLoading] = useState(true);
  const [printingsLoading, setPrintingsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);

  // Add to Deck state
  const [showDeckSelector, setShowDeckSelector] = useState(false);
  const [lastDeckId, setLastDeckId] = useState<number | null>(null);
  const [addToDeckStatus, setAddToDeckStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Get current printing
  const currentPrinting = printings[currentPrintingIndex] ?? null;

  // Merged card data - use full card details when available, fall back to printing data
  // This allows instant display from cached printings while full details load
  const displayData = {
    name: card?.name ?? cardName,
    flavor_name: card?.flavor_name ?? null,
    mana_cost: card?.mana_cost ?? currentPrinting?.mana_cost ?? null,
    type: card?.type ?? currentPrinting?.type_line ?? null,
    text: card?.text ?? currentPrinting?.oracle_text ?? null,
    flavor: card?.flavor ?? currentPrinting?.flavor_text ?? null,
    rarity: card?.rarity ?? currentPrinting?.rarity ?? null,
    power: card?.power ?? currentPrinting?.power ?? null,
    toughness: card?.toughness ?? currentPrinting?.toughness ?? null,
    loyalty: card?.loyalty ?? null,
    defense: card?.defense ?? null,
    keywords: card?.keywords ?? [],
    legalities: card?.legalities ?? {},
    // Price and set info - prefer card, fall back to printing
    prices: card?.prices ?? {
      usd: currentPrinting?.price_usd ?? null,
      usd_foil: currentPrinting?.price_usd_foil ?? null,
      eur: currentPrinting?.price_eur ?? null,
      eur_foil: null,
    },
    set_code: card?.set_code ?? currentPrinting?.set_code ?? null,
    number: card?.number ?? currentPrinting?.collector_number ?? null,
    artist: card?.artist ?? currentPrinting?.artist ?? null,
  };

  // Navigation functions
  const goToPreviousPrinting = useCallback(() => {
    setCurrentPrintingIndex((prev) =>
      prev > 0 ? prev - 1 : printings.length - 1,
    );
    setImageError(false);
  }, [printings.length]);

  const goToNextPrinting = useCallback(() => {
    setCurrentPrintingIndex((prev) =>
      prev < printings.length - 1 ? prev + 1 : 0,
    );
    setImageError(false);
  }, [printings.length]);

  // Load last selected deck ID from store
  useEffect(() => {
    window.electronAPI.store
      .get<number | null>("lastSelectedDeckId")
      .then(setLastDeckId)
      .catch(() => setLastDeckId(null));
  }, []);

  // Handler for adding card to deck
  const handleAddToDeck = useCallback(
    async (deckId: number, deckName: string): Promise<void> => {
      try {
        await window.electronAPI.decks.addCard(deckId, {
          card_name: displayData.name,
          quantity: 1,
          set_code: currentPrinting?.set_code ?? undefined,
          collector_number: currentPrinting?.collector_number ?? undefined,
        });
        // Persist selection
        await window.electronAPI.store.set("lastSelectedDeckId", deckId);
        setLastDeckId(deckId);
        setShowDeckSelector(false);
        setAddToDeckStatus({
          type: "success",
          message: `Added to ${deckName}`,
        });
        // Clear status after 3 seconds
        setTimeout(() => setAddToDeckStatus(null), 3000);
      } catch (err) {
        setAddToDeckStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Failed to add to deck",
        });
      }
    },
    [displayData.name, currentPrinting],
  );

  // Handler for adding card to collection
  const handleAddToCollection = useCallback(async (): Promise<void> => {
    try {
      // Build import text with set code if available
      const setCode = currentPrinting?.set_code;
      const importText = setCode
        ? `1 ${displayData.name} (${setCode.toUpperCase()})`
        : `1 ${displayData.name}`;

      const result = await window.electronAPI.collection.import(
        importText,
        "add",
      );

      if (result.errors && result.errors.length > 0) {
        setAddToDeckStatus({
          type: "error",
          message: result.errors[0],
        });
      } else {
        setAddToDeckStatus({
          type: "success",
          message: "Added to collection",
        });
      }
      setTimeout(() => setAddToDeckStatus(null), 3000);
    } catch (err) {
      setAddToDeckStatus({
        type: "error",
        message:
          err instanceof Error ? err.message : "Failed to add to collection",
      });
    }
  }, [displayData.name, currentPrinting]);

  // Load card data - printings first (cached!), then details in background
  useEffect(() => {
    async function loadCardData(): Promise<void> {
      setIsLoading(true);
      setCombosLoading(true);
      setPrintingsLoading(true);
      setError(null);
      setCurrentPrintingIndex(0);

      // Handle double-faced cards - use front face name
      const searchName = cardName.includes("//")
        ? cardName.split("//")[0].trim()
        : cardName;

      console.log("[CardDetailModal] Loading card:", searchName);

      // Load printings FIRST - this is cached and should be instant
      // We can show the modal immediately with printing data
      let hasPrintings = false;
      try {
        const printingsResult =
          await window.electronAPI.api.cards.getPrintings(searchName);
        const loadedPrintings = printingsResult.printings ?? [];
        setPrintings(loadedPrintings);
        setPrintingsLoading(false);
        hasPrintings = loadedPrintings.length > 0;

        // If setCode/collectorNumber provided, find and select that printing
        if (setCode && collectorNumber && loadedPrintings.length > 0) {
          const matchIndex = loadedPrintings.findIndex(
            (p) =>
              p.set_code?.toUpperCase() === setCode.toUpperCase() &&
              p.collector_number === collectorNumber,
          );
          if (matchIndex >= 0) {
            setCurrentPrintingIndex(matchIndex);
          }
        }

        // If we have printings, we can show the modal now
        // The printing data includes mana_cost, type_line, oracle_text, etc.
        if (loadedPrintings.length > 0) {
          setIsLoading(false);
        }
      } catch {
        // Continue to load card details if printings fail
        setPrintings([]);
        setPrintingsLoading(false);
      }

      // Load full card details and rulings in background
      // This adds keywords, legalities, color_identity, etc.
      try {
        const [cardResult, rulingsResult] = await Promise.all([
          window.electronAPI.api.cards.getByName(searchName),
          window.electronAPI.api.cards.getRulings(searchName),
        ]);

        setCard(cardResult);
        setRulings(rulingsResult.rulings);
      } catch (err) {
        console.error("[CardDetailModal] Error loading card details:", err);
        // Only show error if we don't have printings to display
        if (!hasPrintings) {
          const message = err instanceof Error ? err.message : "Unknown error";
          setError(`Failed to load card: ${message}`);
        }
      } finally {
        setIsLoading(false);
      }

      // Load combos separately (non-blocking)
      try {
        const combosResult =
          await window.electronAPI.api.combos.forCard(cardName);
        setCombos(combosResult.combos ?? []);
      } catch {
        // Silently fail on combo fetch - it's supplementary info
        setCombos([]);
      } finally {
        setCombosLoading(false);
      }
    }

    loadCardData();
  }, [cardName, setCode, collectorNumber]);

  // Handle keyboard navigation (Escape to close, Arrow keys for printings)
  useEffect(() => {
    function handleKeyDown(e: globalThis.KeyboardEvent): void {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft" && printings.length > 1) {
        e.preventDefault();
        goToPreviousPrinting();
      } else if (e.key === "ArrowRight" && printings.length > 1) {
        e.preventDefault();
        goToNextPrinting();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, printings.length, goToPreviousPrinting, goToNextPrinting]);

  // Handle click outside to close
  const handleBackdropClick = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  // Build external links
  const getScryfallLink = (): string | null => {
    const encodedName = encodeURIComponent(displayData.name);
    return `https://scryfall.com/search?q=${encodedName}`;
  };

  const getEdhrecLink = (): string | null => {
    return card?.related_links?.edhrec ?? null;
  };

  const getTcgPlayerLink = (): string | null => {
    return card?.purchase_links?.tcgplayer ?? null;
  };

  // Format price display
  const formatPrice = (price: number | null | undefined): string => {
    if (price == null) return "--";
    return `$${price.toFixed(2)}`;
  };

  // Get the best image URL - prefer current printing if available
  const getImageUrl = (): string | null => {
    // Use current printing's image if available
    if (currentPrinting?.image) {
      return currentPrinting.image;
    }
    // Fall back to card's default image
    if (!card?.images) return null;
    return card.images.large ?? card.images.normal ?? card.images.small ?? null;
  };

  // Get current printing's rarity color, or fall back to card's rarity
  const displayRarity = currentPrinting?.rarity ?? card?.rarity ?? null;
  const rarityColor = displayRarity
    ? getRarityColor(displayRarity)
    : colors.text.dim;

  return (
    <div
      onClick={handleBackdropClick}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        style={{
          background: colors.void.deep,
          border: `1px solid ${colors.border.standard}`,
          borderRadius: 8,
          maxWidth: 900,
          maxHeight: "90vh",
          width: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header with close button */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            padding: "12px 16px",
            borderBottom: `1px solid ${colors.border.subtle}`,
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: colors.text.muted,
              fontSize: 24,
              lineHeight: 1,
              padding: 4,
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.color = colors.text.bright)
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.color = colors.text.muted)
            }
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
          {isLoading && printings.length === 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 48,
                color: colors.text.muted,
              }}
            >
              <span>Loading card details...</span>
            </div>
          )}

          {error && printings.length === 0 && (
            <div
              style={{
                padding: 16,
                background: `${colors.status.error}20`,
                border: `1px solid ${colors.status.error}40`,
                borderRadius: 4,
                color: colors.status.error,
              }}
            >
              {error}
            </div>
          )}

          {(card || printings.length > 0) && (
            <div style={{ display: "flex", gap: 24 }}>
              {/* Left column - Card image with printing navigation */}
              <div style={{ flexShrink: 0, width: 280 }}>
                {/* Image container with nav arrows */}
                <div style={{ position: "relative" }}>
                  {getImageUrl() && !imageError ? (
                    <img
                      src={getImageUrl()!}
                      alt={displayData.name}
                      style={{
                        width: "100%",
                        borderRadius: 8,
                        boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
                      }}
                      onError={() => setImageError(true)}
                    />
                  ) : (
                    <div
                      style={{
                        width: "100%",
                        aspectRatio: "488/680",
                        background: colors.void.light,
                        borderRadius: 8,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: colors.text.muted,
                      }}
                    >
                      No image available
                    </div>
                  )}

                  {/* Navigation arrows - only show if multiple printings */}
                  {printings.length > 1 && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          goToPreviousPrinting();
                        }}
                        style={{
                          position: "absolute",
                          left: 8,
                          top: "50%",
                          transform: "translateY(-50%)",
                          width: 36,
                          height: 36,
                          borderRadius: "50%",
                          background: `${colors.void.deepest}cc`,
                          border: `1px solid ${colors.border.standard}`,
                          color: colors.text.bright,
                          fontSize: 18,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background =
                            colors.gold.standard;
                          e.currentTarget.style.color = colors.void.deepest;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = `${colors.void.deepest}cc`;
                          e.currentTarget.style.color = colors.text.bright;
                        }}
                        title="Previous printing (←)"
                      >
                        ‹
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          goToNextPrinting();
                        }}
                        style={{
                          position: "absolute",
                          right: 8,
                          top: "50%",
                          transform: "translateY(-50%)",
                          width: 36,
                          height: 36,
                          borderRadius: "50%",
                          background: `${colors.void.deepest}cc`,
                          border: `1px solid ${colors.border.standard}`,
                          color: colors.text.bright,
                          fontSize: 18,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background =
                            colors.gold.standard;
                          e.currentTarget.style.color = colors.void.deepest;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = `${colors.void.deepest}cc`;
                          e.currentTarget.style.color = colors.text.bright;
                        }}
                        title="Next printing (→)"
                      >
                        ›
                      </button>
                    </>
                  )}
                </div>

                {/* Printing info bar */}
                {printings.length > 0 && (
                  <div
                    style={{
                      marginTop: 12,
                      padding: "10px 12px",
                      background: colors.void.medium,
                      borderRadius: 6,
                      border: `1px solid ${colors.border.subtle}`,
                    }}
                  >
                    {/* Printing counter */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ color: colors.text.muted, fontSize: 11 }}>
                        Printing {currentPrintingIndex + 1} of{" "}
                        {printings.length}
                      </span>
                      {printingsLoading && (
                        <span
                          style={{ color: colors.text.muted, fontSize: 11 }}
                        >
                          Loading...
                        </span>
                      )}
                    </div>

                    {/* Set and collector number */}
                    {currentPrinting && (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          {currentPrinting.set_code && (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                                padding: "2px 8px",
                                background: `${colors.mana.blue.color}20`,
                                borderRadius: 4,
                                fontSize: 12,
                                fontFamily: "monospace",
                                color: colors.mana.blue.color,
                              }}
                            >
                              <i
                                className={`ss ss-${currentPrinting.set_code.toLowerCase()}`}
                                style={{ fontSize: 12 }}
                              />
                              {currentPrinting.set_code.toUpperCase()}
                              {currentPrinting.collector_number && (
                                <span style={{ color: colors.text.dim }}>
                                  #{currentPrinting.collector_number}
                                </span>
                              )}
                            </span>
                          )}
                          {currentPrinting.rarity && (
                            <span
                              style={{
                                fontSize: 11,
                                color: getRarityColor(currentPrinting.rarity),
                                textTransform: "capitalize",
                              }}
                            >
                              {currentPrinting.rarity}
                            </span>
                          )}
                        </div>

                        {/* Artist */}
                        {currentPrinting.artist && (
                          <div style={{ fontSize: 12, color: colors.text.dim }}>
                            Art by{" "}
                            <span style={{ color: colors.text.standard }}>
                              {currentPrinting.artist}
                            </span>
                          </div>
                        )}

                        {/* Price */}
                        {currentPrinting.price_usd != null && (
                          <div style={{ fontSize: 12 }}>
                            <span style={{ color: colors.text.muted }}>
                              Price:{" "}
                            </span>
                            <span
                              style={{
                                color: colors.gold.standard,
                                fontWeight: 600,
                              }}
                            >
                              ${currentPrinting.price_usd.toFixed(2)}
                            </span>
                            {currentPrinting.price_usd_foil != null && (
                              <span
                                style={{
                                  color: colors.text.muted,
                                  marginLeft: 8,
                                }}
                              >
                                (Foil: $
                                {currentPrinting.price_usd_foil.toFixed(2)})
                              </span>
                            )}
                          </div>
                        )}

                        {/* View in Gallery link */}
                        {onOpenGallery && (
                          <button
                            onClick={() => onOpenGallery(displayData.name)}
                            style={{
                              marginTop: 4,
                              padding: "6px 10px",
                              background: "transparent",
                              border: `1px solid ${colors.border.standard}`,
                              borderRadius: 4,
                              color: colors.text.dim,
                              fontSize: 11,
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              transition: "all 0.15s ease",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderColor =
                                colors.gold.standard;
                              e.currentTarget.style.color =
                                colors.gold.standard;
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderColor =
                                colors.border.standard;
                              e.currentTarget.style.color = colors.text.dim;
                            }}
                          >
                            <span>🖼</span>
                            <span>View in Gallery</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right column - Card details */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Name and mana cost */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 16,
                    marginBottom: 8,
                  }}
                >
                  <h2
                    style={{
                      margin: 0,
                      color: colors.text.bright,
                      fontSize: 24,
                      fontWeight: 600,
                    }}
                  >
                    {displayData.flavor_name ?? displayData.name}
                    {displayData.flavor_name && (
                      <span
                        style={{
                          display: "block",
                          fontSize: 14,
                          color: colors.text.muted,
                          fontWeight: 400,
                          marginTop: 4,
                        }}
                      >
                        ({displayData.name})
                      </span>
                    )}
                  </h2>
                  <ManaCost cost={displayData.mana_cost} size="large" />
                </div>

                {/* Type line */}
                <div
                  style={{
                    color: colors.text.dim,
                    fontSize: 14,
                    marginBottom: 16,
                    paddingBottom: 16,
                    borderBottom: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  {displayData.type}
                  <span
                    style={{
                      marginLeft: 8,
                      color: rarityColor,
                      textTransform: "capitalize",
                    }}
                  >
                    ({displayData.rarity})
                  </span>
                </div>

                {/* Oracle text */}
                {displayData.text && (
                  <div
                    style={{
                      color: colors.text.standard,
                      fontSize: 14,
                      lineHeight: 1.8,
                      marginBottom: 16,
                    }}
                  >
                    <CardText text={displayData.text} size="small" />
                  </div>
                )}

                {/* Flavor text */}
                {displayData.flavor && (
                  <div
                    style={{
                      color: colors.text.muted,
                      fontSize: 13,
                      fontStyle: "italic",
                      marginBottom: 16,
                      paddingLeft: 12,
                      borderLeft: `2px solid ${colors.border.subtle}`,
                    }}
                  >
                    {displayData.flavor}
                  </div>
                )}

                {/* Power/Toughness or Loyalty */}
                {(displayData.power ||
                  displayData.loyalty ||
                  displayData.defense) && (
                  <div
                    style={{
                      marginBottom: 16,
                      paddingBottom: 16,
                      borderBottom: `1px solid ${colors.border.subtle}`,
                    }}
                  >
                    {displayData.power && displayData.toughness && (
                      <span style={{ color: colors.text.dim, fontSize: 14 }}>
                        Power/Toughness:{" "}
                        <span
                          style={{
                            color: colors.gold.standard,
                            fontWeight: 600,
                          }}
                        >
                          {displayData.power}/{displayData.toughness}
                        </span>
                      </span>
                    )}
                    {displayData.loyalty && (
                      <span style={{ color: colors.text.dim, fontSize: 14 }}>
                        Loyalty:{" "}
                        <span
                          style={{
                            color: colors.gold.standard,
                            fontWeight: 600,
                          }}
                        >
                          {displayData.loyalty}
                        </span>
                      </span>
                    )}
                    {displayData.defense && (
                      <span
                        style={{
                          color: colors.text.dim,
                          fontSize: 14,
                          marginLeft: 16,
                        }}
                      >
                        Defense:{" "}
                        <span
                          style={{
                            color: colors.gold.standard,
                            fontWeight: 600,
                          }}
                        >
                          {displayData.defense}
                        </span>
                      </span>
                    )}
                  </div>
                )}

                {/* Prices */}
                {(displayData.prices.usd !== null ||
                  displayData.prices.eur !== null) && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 16,
                      marginBottom: 16,
                      paddingBottom: 16,
                      borderBottom: `1px solid ${colors.border.subtle}`,
                    }}
                  >
                    <div>
                      <span style={{ color: colors.text.muted, fontSize: 12 }}>
                        USD:{" "}
                      </span>
                      <span
                        style={{
                          color: colors.gold.standard,
                          fontSize: 14,
                          fontWeight: 600,
                        }}
                      >
                        {formatPrice(displayData.prices.usd)}
                      </span>
                      {displayData.prices.usd_foil && (
                        <span
                          style={{
                            color: colors.text.muted,
                            fontSize: 12,
                            marginLeft: 4,
                          }}
                        >
                          (Foil: {formatPrice(displayData.prices.usd_foil)})
                        </span>
                      )}
                    </div>
                    <div>
                      <span style={{ color: colors.text.muted, fontSize: 12 }}>
                        EUR:{" "}
                      </span>
                      <span style={{ color: colors.text.dim, fontSize: 14 }}>
                        {displayData.prices.eur != null
                          ? `€${displayData.prices.eur.toFixed(2)}`
                          : "--"}
                      </span>
                      {displayData.prices.eur_foil && (
                        <span
                          style={{
                            color: colors.text.muted,
                            fontSize: 12,
                            marginLeft: 4,
                          }}
                        >
                          (Foil: €{displayData.prices.eur_foil.toFixed(2)})
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Set and artist info */}
                <div
                  style={{
                    display: "flex",
                    gap: 16,
                    marginBottom: 16,
                    fontSize: 13,
                    color: colors.text.dim,
                  }}
                >
                  {displayData.set_code && (
                    <span>
                      Set:{" "}
                      <span
                        style={{
                          color: colors.text.standard,
                          fontFamily: "monospace",
                        }}
                      >
                        {displayData.set_code.toUpperCase()}
                      </span>
                      {displayData.number && ` #${displayData.number}`}
                    </span>
                  )}
                  {displayData.artist && (
                    <span>
                      Artist:{" "}
                      <span style={{ color: colors.text.standard }}>
                        {displayData.artist}
                      </span>
                    </span>
                  )}
                </div>

                {/* Legalities */}
                {Object.keys(displayData.legalities).length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div
                      style={{
                        color: colors.gold.standard,
                        fontSize: 14,
                        fontWeight: 600,
                        marginBottom: 8,
                      }}
                    >
                      Format Legalities
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {FORMATS_TO_SHOW.map((format) => {
                        const legality = displayData.legalities?.[format];
                        if (!legality) return null;
                        return (
                          <LegalityBadge
                            key={format}
                            format={format}
                            legality={legality}
                          />
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Rulings */}
                <RulingsSection rulings={rulings} />

                {/* Combos */}
                <CombosSection
                  combos={combos}
                  cardName={cardName}
                  isLoading={combosLoading}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer with actions */}
        {(card || printings.length > 0) && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px 24px",
              borderTop: `1px solid ${colors.border.subtle}`,
              background: colors.void.medium,
            }}
          >
            {/* Action buttons */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {/* Add to Deck button */}
              <button
                onClick={() => setShowDeckSelector(true)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 16px",
                  background: colors.gold.standard,
                  border: "none",
                  borderRadius: 4,
                  color: colors.void.deepest,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = colors.gold.bright)
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = colors.gold.standard)
                }
              >
                + Add to Deck
              </button>

              {/* Add to Collection button */}
              <button
                onClick={handleAddToCollection}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
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
                  e.currentTarget.style.borderColor = colors.gold.standard;
                  e.currentTarget.style.color = colors.gold.standard;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = colors.border.standard;
                  e.currentTarget.style.color = colors.text.dim;
                }}
              >
                + Add to Collection
              </button>

              {/* Status message */}
              {addToDeckStatus && (
                <span
                  style={{
                    fontSize: 13,
                    color:
                      addToDeckStatus.type === "success"
                        ? colors.status.success
                        : colors.status.error,
                  }}
                >
                  {addToDeckStatus.message}
                </span>
              )}
            </div>

            {/* External links */}
            <div style={{ display: "flex", gap: 8 }}>
              <ExternalLink href={getScryfallLink()}>Scryfall</ExternalLink>
              <ExternalLink href={getEdhrecLink()}>EDHREC</ExternalLink>
              <ExternalLink href={getTcgPlayerLink()}>TCGPlayer</ExternalLink>
            </div>
          </div>
        )}
      </div>

      {/* Deck selector dropdown */}
      {showDeckSelector && (
        <DeckSelectorDropdown
          onSelect={handleAddToDeck}
          onCancel={() => setShowDeckSelector(false)}
          defaultDeckId={lastDeckId}
        />
      )}
    </div>
  );
}

export default CardDetailModal;
