/**
 * CardSuggestionsPanel - Redesigned card suggestions with editorial layout
 *
 * Features:
 * - Category tabs (Synergy, Staple, Upgrade, Budget) with counts
 * - Data-dense row layout with hover preview
 * - Detected themes as filter pills
 * - Score-based visual hierarchy
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { colors, synergyColors } from "../../theme";
import { ManaCost } from "../ManaSymbols";

import type { ReactNode } from "react";
import type { components } from "../../../../shared/types/api-generated";

type SuggestCardsResult = components["schemas"]["SuggestCardsResult"];
type SuggestedCard = components["schemas"]["SuggestedCard"];
type Category = SuggestedCard["category"];

// Category configuration with icons and colors
const CATEGORY_CONFIG: Record<
  Category,
  {
    label: string;
    icon: string;
    color: string;
    glow: string;
    description: string;
  }
> = {
  synergy: {
    label: "Synergy",
    icon: "ms-instant",
    color: synergyColors.keyword.color,
    glow: synergyColors.keyword.glow,
    description: "Cards that synergize with your deck's themes",
  },
  staple: {
    label: "Staple",
    icon: "ms-artifact",
    color: colors.gold.standard,
    glow: colors.gold.glow,
    description: "Format staples that fit your colors",
  },
  upgrade: {
    label: "Upgrade",
    icon: "ms-planeswalker",
    color: synergyColors.combo.color,
    glow: synergyColors.combo.glow,
    description: "Direct upgrades to cards in your deck",
  },
  budget: {
    label: "Budget",
    icon: "ms-land",
    color: synergyColors.tribal.color,
    glow: synergyColors.tribal.glow,
    description: "Affordable alternatives and value picks",
  },
};

interface CardSuggestionsPanelProps {
  result: SuggestCardsResult;
  onViewCard: (cardName: string) => void;
}

export function CardSuggestionsPanel({
  result,
  onViewCard,
}: CardSuggestionsPanelProps): ReactNode {
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(
    null,
  );
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [hoveredCard, setHoveredCard] = useState<SuggestedCard | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [cardImages, setCardImages] = useState<Record<string, string>>({});
  const [mousePosition, setMousePosition] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const suggestions = result.suggestions || [];
  const detectedThemes = result.detected_themes || [];

  // Group by category
  const grouped = suggestions.reduce(
    (acc, card) => {
      if (!acc[card.category]) acc[card.category] = [];
      acc[card.category].push(card);
      return acc;
    },
    {} as Record<Category, SuggestedCard[]>,
  );

  // Filter cards based on selection
  const filteredCards = suggestions.filter((card) => {
    if (selectedCategory && card.category !== selectedCategory) return false;
    if (
      selectedTheme &&
      !card.reason.toLowerCase().includes(selectedTheme.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  // Sort by category priority, then by owned status
  const sortedCards = [...filteredCards].sort((a, b) => {
    const categoryOrder: Category[] = [
      "synergy",
      "staple",
      "upgrade",
      "budget",
    ];
    const catDiff =
      categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category);
    if (catDiff !== 0) return catDiff;
    // Owned cards first within category
    if (a.owned && !b.owned) return -1;
    if (!a.owned && b.owned) return 1;
    return 0;
  });

  // Prefetch card images
  useEffect(() => {
    if (suggestions.length === 0) return;

    const fetchImages = async (): Promise<void> => {
      const images: Record<string, string> = {};
      // Fetch first 20 images to avoid too many requests
      const cardsToFetch = suggestions.slice(0, 20);

      await Promise.all(
        cardsToFetch.map(async (card) => {
          try {
            const details = await window.electronAPI.api.cards.getByName(
              card.name,
            );
            if (details?.images?.small) {
              images[card.name] = details.images.small;
            }
          } catch {
            // Ignore errors
          }
        }),
      );
      setCardImages(images);
    };

    fetchImages();
  }, [suggestions]);

  // Fetch preview image on hover
  useEffect(() => {
    if (!hoveredCard) {
      setPreviewImageUrl(null);
      return;
    }

    // Try cached small image first, convert to normal
    const smallImage = cardImages[hoveredCard.name];
    if (smallImage) {
      const normalUrl = smallImage.replace("/small/", "/normal/");
      setPreviewImageUrl(normalUrl);
    }

    // Fetch full resolution
    const fetchImage = async (): Promise<void> => {
      try {
        const details = await window.electronAPI.api.cards.getByName(
          hoveredCard.name,
        );
        if (details?.images?.normal) {
          setPreviewImageUrl(details.images.normal);
        } else if (details?.images?.large) {
          setPreviewImageUrl(details.images.large);
        }
      } catch {
        // Keep existing image
      }
    };

    fetchImage();
  }, [hoveredCard, cardImages]);

  // Hover handlers with mouse position tracking
  const handleCardHover = useCallback(
    (card: SuggestedCard | null, position?: { x: number; y: number }) => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
        hoverTimeoutRef.current = null;
      }
      if (card && position) {
        setHoveredCard(card);
        setMousePosition(position);
      } else {
        hoverTimeoutRef.current = setTimeout(() => {
          setHoveredCard(null);
          setMousePosition(null);
        }, 100);
      }
    },
    [],
  );

  // Category counts
  const categoryCounts: Record<Category, number> = {
    synergy: grouped.synergy?.length || 0,
    staple: grouped.staple?.length || 0,
    upgrade: grouped.upgrade?.length || 0,
    budget: grouped.budget?.length || 0,
  };

  const totalCount = suggestions.length;
  const categories: Category[] = ["synergy", "staple", "upgrade", "budget"];

  return (
    <div className="space-y-4">
      {/* Detected themes pills */}
      {detectedThemes.length > 0 && (
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className="text-xs uppercase tracking-wider"
            style={{ color: colors.text.muted }}
          >
            Detected Themes
          </span>
          <div className="flex flex-wrap gap-2">
            {detectedThemes.map((theme) => {
              const isSelected = selectedTheme === theme;
              return (
                <button
                  key={theme}
                  onClick={() => setSelectedTheme(isSelected ? null : theme)}
                  className="px-3 py-1.5 rounded-full text-xs font-medium transition-all"
                  style={{
                    background: isSelected
                      ? `${synergyColors.strategy.color}30`
                      : colors.void.light,
                    border: `1px solid ${isSelected ? synergyColors.strategy.color : colors.border.subtle}`,
                    color: isSelected
                      ? synergyColors.strategy.color
                      : colors.text.dim,
                    boxShadow: isSelected
                      ? `0 0 12px ${synergyColors.strategy.glow}`
                      : "none",
                  }}
                >
                  {theme.toUpperCase()}
                </button>
              );
            })}
          </div>
          {selectedTheme && (
            <button
              onClick={() => setSelectedTheme(null)}
              className="text-xs transition-colors"
              style={{ color: colors.text.muted }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = colors.text.standard)
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = colors.text.muted)
              }
            >
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* Category tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <button
          onClick={() => setSelectedCategory(null)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
          style={{
            background: !selectedCategory
              ? colors.void.lighter
              : colors.void.light,
            border: `1px solid ${!selectedCategory ? colors.gold.dim : colors.border.subtle}`,
            color: !selectedCategory ? colors.gold.standard : colors.text.dim,
          }}
        >
          <i className="ms ms-saga" style={{ fontSize: 14 }} />
          <span>All</span>
          <span
            className="px-1.5 py-0.5 rounded text-xs"
            style={{
              background: !selectedCategory
                ? colors.gold.standard
                : colors.void.medium,
              color: !selectedCategory
                ? colors.void.deepest
                : colors.text.muted,
            }}
          >
            {totalCount}
          </span>
        </button>

        {categories.map((cat) => {
          const config = CATEGORY_CONFIG[cat];
          const count = categoryCounts[cat];
          const isSelected = selectedCategory === cat;

          if (count === 0) return null;

          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(isSelected ? null : cat)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
              style={{
                background: isSelected
                  ? `${config.color}20`
                  : colors.void.light,
                border: `1px solid ${isSelected ? config.color : colors.border.subtle}`,
                color: isSelected ? config.color : colors.text.dim,
                boxShadow: isSelected ? `0 0 15px ${config.glow}` : "none",
              }}
            >
              <i className={`ms ${config.icon}`} style={{ fontSize: 14 }} />
              <span>{config.label}</span>
              <span
                className="px-1.5 py-0.5 rounded text-xs"
                style={{
                  background: isSelected ? config.color : colors.void.medium,
                  color: isSelected ? colors.void.deepest : colors.text.muted,
                }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Results container */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          background: colors.void.deep,
          border: `1px solid ${colors.border.subtle}`,
        }}
      >
        {/* Results header */}
        <div
          className="px-4 py-2.5 border-b flex items-center justify-between"
          style={{ borderColor: colors.border.subtle }}
        >
          <span className="text-sm" style={{ color: colors.text.muted }}>
            {filteredCards.length} suggestion
            {filteredCards.length !== 1 ? "s" : ""}
            {selectedCategory &&
              ` in ${CATEGORY_CONFIG[selectedCategory].label}`}
            {selectedTheme && ` matching "${selectedTheme}"`}
          </span>
          {(selectedCategory || selectedTheme) && (
            <button
              onClick={() => {
                setSelectedCategory(null);
                setSelectedTheme(null);
              }}
              className="text-xs px-2 py-1 rounded transition-colors"
              style={{
                color: colors.text.muted,
                background: colors.void.light,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = colors.text.standard;
                e.currentTarget.style.background = colors.void.lighter;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = colors.text.muted;
                e.currentTarget.style.background = colors.void.light;
              }}
            >
              Clear all filters
            </button>
          )}
        </div>

        {/* Card rows */}
        <div className="max-h-[520px] overflow-auto">
          {sortedCards.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <span className="text-sm" style={{ color: colors.text.muted }}>
                No cards match the current filters
              </span>
            </div>
          ) : (
            sortedCards.map((card, idx) => (
              <SuggestionRow
                key={card.name}
                card={card}
                imageUrl={cardImages[card.name]}
                delay={idx * 0.02}
                onHover={handleCardHover}
                onClick={() => onViewCard(card.name)}
                isHovered={hoveredCard?.name === card.name}
              />
            ))
          )}
        </div>
      </div>

      {/* Floating card preview */}
      {hoveredCard && previewImageUrl && mousePosition && (
        <CardPreviewPanel
          card={hoveredCard}
          imageUrl={previewImageUrl}
          mousePosition={mousePosition}
        />
      )}
    </div>
  );
}

// Individual suggestion row
function SuggestionRow({
  card,
  imageUrl,
  delay,
  onHover,
  onClick,
  isHovered,
}: {
  card: SuggestedCard;
  imageUrl?: string;
  delay: number;
  onHover: (
    card: SuggestedCard | null,
    position?: { x: number; y: number },
  ) => void;
  onClick: () => void;
  isHovered: boolean;
}): ReactNode {
  const config = CATEGORY_CONFIG[card.category];

  const handleMouseEnter = (e: React.MouseEvent): void => {
    onHover(card, { x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent): void => {
    if (isHovered) {
      onHover(card, { x: e.clientX, y: e.clientY });
    }
  };

  return (
    <div
      className="flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-all"
      style={{
        borderBottom: `1px solid ${colors.border.subtle}`,
        background: isHovered ? colors.void.light : "transparent",
        animation: `reveal-up 0.25s ease-out ${delay}s both`,
      }}
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => onHover(null)}
    >
      {/* Thumbnail */}
      {imageUrl ? (
        <img
          src={imageUrl}
          alt=""
          className="w-9 h-12 rounded object-cover flex-shrink-0"
          loading="lazy"
          style={{ border: `1px solid ${colors.border.subtle}` }}
        />
      ) : (
        <div
          className="w-9 h-12 rounded flex items-center justify-center flex-shrink-0"
          style={{
            background: colors.void.medium,
            border: `1px solid ${colors.border.subtle}`,
          }}
        >
          <i
            className={`ms ${config.icon}`}
            style={{ color: colors.text.muted, fontSize: 14 }}
          />
        </div>
      )}

      {/* Card info */}
      <div className="flex-1 min-w-0 flex items-center gap-3">
        {/* Owned indicator */}
        {card.owned && (
          <span
            title="In your collection"
            className="flex-shrink-0"
            style={{ color: colors.status.success, fontSize: 12 }}
          >
            <i className="ms ms-ability-treasure" />
          </span>
        )}

        {/* Name */}
        <span
          className="font-medium truncate transition-colors"
          style={{
            color: isHovered ? colors.text.bright : colors.text.standard,
            fontSize: 13,
          }}
        >
          {card.name}
        </span>

        {/* Mana cost */}
        {card.mana_cost && (
          <span className="flex-shrink-0 opacity-80">
            <ManaCost cost={card.mana_cost} size="small" />
          </span>
        )}
      </div>

      {/* Type line - truncated */}
      <span
        className="hidden md:block flex-shrink-0 truncate text-xs"
        style={{ color: colors.text.muted, maxWidth: 120 }}
      >
        {card.type_line?.replace("Legendary ", "").replace("Creature — ", "") ||
          ""}
      </span>

      {/* Reason badge */}
      <span
        className="flex-shrink-0 text-xs px-2 py-0.5 rounded truncate"
        style={{
          background: `${config.color}18`,
          color: config.color,
          maxWidth: 160,
          fontWeight: 500,
        }}
      >
        {card.reason}
      </span>

      {/* Category indicator dot */}
      <div
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{
          background: config.color,
          boxShadow: `0 0 6px ${config.glow}`,
        }}
        title={config.label}
      />

      {/* Price */}
      {card.price_usd != null && (
        <span
          className="flex-shrink-0 text-xs font-mono"
          style={{
            color: colors.gold.standard,
            minWidth: 50,
            textAlign: "right",
          }}
        >
          ${card.price_usd.toFixed(2)}
        </span>
      )}
    </div>
  );
}

// Floating preview panel - positioned near mouse cursor
function CardPreviewPanel({
  card,
  imageUrl,
  mousePosition,
}: {
  card: SuggestedCard;
  imageUrl: string;
  mousePosition: { x: number; y: number };
}): ReactNode {
  const config = CATEGORY_CONFIG[card.category];

  // Calculate position - offset from mouse, keep within viewport
  const panelWidth = 260;
  const panelHeight = 400; // approximate
  const offset = 20;

  let left = mousePosition.x + offset;
  let top = mousePosition.y - panelHeight / 2;

  // Keep panel within viewport horizontally
  if (left + panelWidth > window.innerWidth - 20) {
    left = mousePosition.x - panelWidth - offset;
  }
  if (left < 20) {
    left = 20;
  }

  // Keep panel within viewport vertically
  if (top < 20) {
    top = 20;
  }
  if (top + panelHeight > window.innerHeight - 20) {
    top = window.innerHeight - panelHeight - 20;
  }

  return createPortal(
    <div
      className="fixed z-50 pointer-events-none"
      style={{
        left,
        top,
        width: panelWidth,
      }}
    >
      <div
        className="p-3 rounded-xl"
        style={{
          background: `linear-gradient(135deg, ${colors.void.medium} 0%, ${colors.void.deep} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 60px ${colors.gold.glow}20`,
          animation: "fade-in 0.15s ease-out",
        }}
      >
        {/* Card image */}
        <img
          src={imageUrl}
          alt={card.name}
          className="w-full rounded-lg"
          style={{ boxShadow: "0 4px 16px rgba(0,0,0,0.4)" }}
        />

        {/* Card info */}
        <div className="mt-3 space-y-2">
          {/* Name and mana */}
          <div className="text-center">
            <div
              className="font-medium text-sm truncate"
              style={{ color: colors.gold.standard }}
            >
              {card.name}
            </div>
            {card.mana_cost && (
              <div className="flex justify-center mt-1">
                <ManaCost cost={card.mana_cost} size="small" />
              </div>
            )}
          </div>

          {/* Type */}
          {card.type_line && (
            <div
              className="text-xs text-center truncate"
              style={{ color: colors.text.muted }}
            >
              {card.type_line}
            </div>
          )}

          {/* Category badge */}
          <div className="flex justify-center">
            <span
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium"
              style={{
                background: `${config.color}20`,
                border: `1px solid ${config.color}40`,
                color: config.color,
              }}
            >
              <i className={`ms ${config.icon}`} style={{ fontSize: 12 }} />
              {config.label}
            </span>
          </div>

          {/* Reason */}
          <div
            className="text-xs text-center leading-relaxed"
            style={{ color: colors.text.dim }}
          >
            {card.reason}
          </div>

          {/* Price and owned status */}
          <div className="flex items-center justify-center gap-3 pt-1">
            {card.owned && (
              <span
                className="flex items-center gap-1 text-xs"
                style={{ color: colors.status.success }}
              >
                <i className="ms ms-ability-treasure" />
                Owned
              </span>
            )}
            {card.price_usd != null && (
              <span
                className="text-xs font-mono"
                style={{ color: colors.gold.standard }}
              >
                ${card.price_usd.toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default CardSuggestionsPanel;
