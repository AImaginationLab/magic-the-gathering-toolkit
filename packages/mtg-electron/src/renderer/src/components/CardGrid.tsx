import { useState, memo, useCallback } from "react";
import { Grid } from "react-window";
import { AutoSizer } from "react-virtualized-auto-sizer";

import { colors, getRarityColor } from "../theme";

import type { ReactNode, CSSProperties, ReactElement } from "react";

export interface CardData {
  uuid: string;
  name: string;
  manaCost?: string | null;
  type: string;
  rarity: string;
  setCode: string;
  text?: string | null;
  imageUrl?: string | null;
  owned?: boolean | null;
}

// Card dimensions for grid layout
const CARD_WIDTH = 200;
const CARD_HEIGHT = 340;
const CARD_GAP = 16;

interface CardItemProps {
  card: CardData;
  onClick?: (card: CardData) => void;
}

// Parse mana cost string like "{2}{U}{U}" into symbols
function parseManaSymbols(manaCost: string | null | undefined): string[] {
  if (!manaCost) return [];
  const matches = manaCost.match(/\{([^}]+)\}/g);
  if (!matches) return [];
  return matches.map((m) => m.slice(1, -1).toLowerCase());
}

function ManaSymbol({ symbol }: { symbol: string }): ReactNode {
  // Handle special cases
  const symbolMap: Record<string, string> = {
    w: "w",
    u: "u",
    b: "b",
    r: "r",
    g: "g",
    c: "c",
    x: "x",
    t: "tap",
    s: "s", // snow
  };

  // Check if it's a number
  if (/^\d+$/.test(symbol)) {
    return <i className={`ms ms-${symbol} ms-cost`} />;
  }

  // Check if it's a hybrid (e.g., "w/u")
  if (symbol.includes("/")) {
    const [a, b] = symbol.split("/");
    return <i className={`ms ms-${a}${b} ms-cost ms-split`} />;
  }

  const mapped = symbolMap[symbol] || symbol;
  return <i className={`ms ms-${mapped} ms-cost`} />;
}

// Memoized card item for virtualization performance
const CardItem = memo(function CardItem({
  card,
  onClick,
}: CardItemProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const [imageError, setImageError] = useState(false);
  const manaSymbols = parseManaSymbols(card.manaCost);
  const rarityColor = getRarityColor(card.rarity);

  return (
    <div
      className="relative rounded overflow-hidden cursor-pointer transition-all duration-200"
      style={{
        background: colors.void.medium,
        border: `1px solid ${isHovered ? rarityColor : colors.border.standard}`,
        transform: isHovered ? "translateY(-2px)" : "none",
        boxShadow: isHovered ? `0 4px 12px rgba(0,0,0,0.4)` : "none",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClick?.(card)}
    >
      {/* Card image */}
      <div
        className="relative w-full overflow-hidden"
        style={{ aspectRatio: "488/680" }}
      >
        {card.imageUrl && !imageError ? (
          <img
            src={card.imageUrl}
            alt={card.name}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => setImageError(true)}
          />
        ) : (
          <div
            className="w-full h-full flex flex-col items-center justify-center p-3"
            style={{ background: colors.void.light }}
          >
            {/* Fallback card display */}
            <div className="text-center">
              {/* Mana cost */}
              {manaSymbols.length > 0 && (
                <div className="flex items-center justify-center gap-0.5 mb-2">
                  {manaSymbols.map((s, i) => (
                    <ManaSymbol key={i} symbol={s} />
                  ))}
                </div>
              )}

              {/* Name */}
              <div
                className="font-display text-sm mb-2 leading-tight"
                style={{ color: colors.text.bright }}
              >
                {card.name}
              </div>

              {/* Type */}
              <div className="text-xs mb-2" style={{ color: colors.text.dim }}>
                {card.type}
              </div>

              {/* Card text preview */}
              {card.text && (
                <div
                  className="text-xs leading-snug line-clamp-4"
                  style={{ color: colors.text.muted }}
                >
                  {card.text}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Rarity indicator */}
        <div
          className="absolute top-2 right-2 w-3 h-3 rounded-full"
          style={{
            backgroundColor: rarityColor,
            boxShadow: `0 0 6px ${rarityColor}`,
          }}
          title={card.rarity}
        />

        {/* Owned indicator */}
        {card.owned && (
          <div
            className="absolute top-2 left-2 flex items-center justify-center"
            style={{
              color: colors.status.success,
              fontSize: "14px",
              textShadow: "0 1px 3px rgba(0,0,0,0.8)",
            }}
            title="In your collection"
          >
            <i className="ms ms-ability-treasure" />
          </div>
        )}
      </div>

      {/* Card info bar */}
      <div
        className="p-2"
        style={{ borderTop: `1px solid ${colors.border.subtle}` }}
      >
        <div
          className="text-sm font-display truncate"
          style={{ color: colors.text.standard }}
        >
          {card.name}
        </div>
        <div className="flex items-center justify-between mt-1">
          <span
            className="text-xs font-mono uppercase"
            style={{ color: colors.text.muted }}
          >
            {card.setCode}
          </span>
          {manaSymbols.length > 0 && (
            <div className="flex items-center gap-0.5">
              {manaSymbols.slice(0, 5).map((s, i) => (
                <span key={i} style={{ fontSize: "12px" }}>
                  <ManaSymbol symbol={s} />
                </span>
              ))}
              {manaSymbols.length > 5 && (
                <span className="text-xs" style={{ color: colors.text.muted }}>
                  +{manaSymbols.length - 5}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

// Props passed to cell component via cellProps
interface GridCellProps {
  cards: CardData[];
  columnCount: number;
  onCardClick?: (card: CardData) => void;
}

// Cell renderer for the virtualized grid (react-window v2 API)
function GridCell({
  columnIndex,
  rowIndex,
  style,
  cards,
  columnCount,
  onCardClick,
}: {
  ariaAttributes: { "aria-colindex": number; role: "gridcell" };
  columnIndex: number;
  rowIndex: number;
  style: CSSProperties;
} & GridCellProps): ReactElement {
  const index = rowIndex * columnCount + columnIndex;

  if (index >= cards.length) {
    // Return empty div for cells beyond data range
    return <div style={style} />;
  }

  const card = cards[index];

  return (
    <div style={{ ...style, padding: CARD_GAP / 2 }}>
      <CardItem card={card} onClick={onCardClick} />
    </div>
  );
}

// Wrapper component for AutoSizer's Child prop
function VirtualizedGridContent({
  height,
  width,
  cards,
  onCardClick,
}: {
  height: number | undefined;
  width: number | undefined;
  cards: CardData[];
  onCardClick: (card: CardData) => void;
}): ReactElement {
  // Handle initial render when dimensions are undefined
  if (!height || !width) {
    return <div />;
  }

  // Calculate grid dimensions
  const columnCount = Math.max(1, Math.floor(width / (CARD_WIDTH + CARD_GAP)));
  const rowCount = Math.ceil(cards.length / columnCount);
  const columnWidth = width / columnCount;

  const cellProps: GridCellProps = {
    cards,
    columnCount,
    onCardClick,
  };

  return (
    <Grid
      cellComponent={GridCell}
      cellProps={cellProps}
      columnCount={columnCount}
      columnWidth={columnWidth}
      rowCount={rowCount}
      rowHeight={CARD_HEIGHT + CARD_GAP}
      overscanCount={2}
      style={{ height, width }}
    />
  );
}

interface CardGridProps {
  cards: CardData[];
  onCardClick?: (card: CardData) => void;
  isLoading?: boolean;
  emptyMessage?: string;
}

// Threshold for using virtualization (cards below this render normally)
const VIRTUALIZATION_THRESHOLD = 50;

export function CardGrid({
  cards,
  onCardClick,
  isLoading = false,
  emptyMessage = "No cards found",
}: CardGridProps): ReactNode {
  // Memoize the click handler to prevent unnecessary re-renders
  const handleCardClick = useCallback(
    (card: CardData) => {
      onCardClick?.(card);
    },
    [onCardClick],
  );

  // Create bound Child component for AutoSizer (must be before conditional returns - Rules of Hooks)
  const BoundGridContent = useCallback(
    ({
      height,
      width,
    }: {
      height: number | undefined;
      width: number | undefined;
    }) => (
      <VirtualizedGridContent
        height={height}
        width={width}
        cards={cards}
        onCardClick={handleCardClick}
      />
    ),
    [cards, handleCardClick],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div
          className="flex items-center gap-3"
          style={{ color: colors.text.muted }}
        >
          <i className="ms ms-c ms-cost" style={{ fontSize: "24px" }} />
          <span className="font-body">Searching the multiverse...</span>
        </div>
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="font-body" style={{ color: colors.text.muted }}>
          {emptyMessage}
        </span>
      </div>
    );
  }

  // For small card counts, use simple grid (faster initial render)
  if (cards.length <= VIRTUALIZATION_THRESHOLD) {
    return (
      <div
        className="grid gap-4"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
        }}
      >
        {cards.map((card) => (
          <CardItem key={card.uuid} card={card} onClick={handleCardClick} />
        ))}
      </div>
    );
  }

  // For large card counts, use virtualized grid
  return (
    <div className="h-full w-full" style={{ minHeight: 400 }}>
      <AutoSizer Child={BoundGridContent} />
    </div>
  );
}

export default CardGrid;
