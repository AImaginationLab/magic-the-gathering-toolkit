/**
 * ArtistsScreen - Arcane Gallery
 *
 * Browse MTG card artists with the Arcane Library aesthetic.
 * Features constellation background, glowing selections, and
 * 3D card previews.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from "react";

import { colors } from "../theme";
import { ManaCost } from "./ManaSymbols";
import { CardDetailModal } from "./CardDetailModal";

import type { ReactNode, CSSProperties } from "react";
import type { components } from "../../../shared/types/api-generated";

type ArtistSummary = components["schemas"]["ArtistSummary"];
type CardSummary = components["schemas"]["CardSummary"];

// ═══════════════════════════════════════════════════════════════
// AMBIENT EFFECTS
// ═══════════════════════════════════════════════════════════════

function ConstellationBackground(): ReactNode {
  const lines = useMemo(() => {
    const points = Array.from({ length: 8 }, () => ({
      x: 10 + Math.random() * 80,
      y: 10 + Math.random() * 80,
    }));

    const connections: Array<{
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      delay: number;
    }> = [];

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = Math.hypot(
          points[i].x - points[j].x,
          points[i].y - points[j].y,
        );
        if (dist < 40 && connections.length < 10) {
          connections.push({
            x1: points[i].x,
            y1: points[i].y,
            x2: points[j].x,
            y2: points[j].y,
            delay: Math.random() * 5,
          });
        }
      }
    }

    return { points, connections };
  }, []);

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.06 }}
    >
      <defs>
        <linearGradient id="artistLineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={colors.gold.dim} />
          <stop offset="100%" stopColor={colors.mana.white.color} />
        </linearGradient>
      </defs>

      {lines.connections.map((line, i) => (
        <line
          key={`line-${i}`}
          x1={`${line.x1}%`}
          y1={`${line.y1}%`}
          x2={`${line.x2}%`}
          y2={`${line.y2}%`}
          stroke="url(#artistLineGrad)"
          strokeWidth="0.5"
          style={{
            animation: `constellation-pulse 4s ease-in-out infinite`,
            animationDelay: `${line.delay}s`,
          }}
        />
      ))}

      {lines.points.map((point, i) => (
        <circle
          key={`point-${i}`}
          cx={`${point.x}%`}
          cy={`${point.y}%`}
          r="1.5"
          fill={colors.gold.dim}
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.4}s`,
          }}
        />
      ))}
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════
// ARTIST LIST ITEM
// ═══════════════════════════════════════════════════════════════

interface ArtistListItemProps {
  artist: ArtistSummary;
  isSelected: boolean;
  onClick: () => void;
}

function ArtistListItem({
  artist,
  isSelected,
  onClick,
}: ArtistListItemProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  const yearRange =
    artist.first_card_year && artist.most_recent_year
      ? artist.first_card_year === artist.most_recent_year
        ? `${artist.first_card_year}`
        : `${artist.first_card_year}-${artist.most_recent_year}`
      : null;

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative px-4 py-3 cursor-pointer transition-all duration-300"
      style={{
        background: isSelected
          ? `linear-gradient(90deg, ${colors.gold.standard}15 0%, transparent 100%)`
          : isHovered
            ? colors.void.light
            : "transparent",
        borderBottom: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Selection accent */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 transition-all duration-300"
        style={{
          background: isSelected ? colors.gold.standard : "transparent",
          boxShadow: isSelected ? `0 0 10px ${colors.gold.glow}` : "none",
        }}
      />

      <div
        className="font-display text-sm tracking-wide truncate transition-colors duration-300"
        style={{
          color: isSelected
            ? colors.gold.bright
            : isHovered
              ? colors.text.bright
              : colors.text.standard,
        }}
      >
        {artist.name}
      </div>

      <div className="flex items-center gap-2 mt-1">
        <span
          className="text-xs px-1.5 py-0.5 rounded"
          style={{
            background: `${colors.gold.standard}20`,
            color: colors.gold.dim,
          }}
        >
          {artist.card_count} cards
        </span>
        <span className="text-xs" style={{ color: colors.text.muted }}>
          {artist.sets_count} sets
        </span>
        {yearRange && (
          <span className="text-xs" style={{ color: colors.text.dim }}>
            {yearRange}
          </span>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// CARD GRID ITEM
// ═══════════════════════════════════════════════════════════════

function getRarityStyle(rarity: string | null): {
  letter: string;
  color: string;
  glow: string;
} {
  const r = (rarity ?? "common").toLowerCase();
  switch (r) {
    case "mythic":
      return {
        letter: "M",
        color: colors.rarity.mythic.color,
        glow: colors.rarity.mythic.glow,
      };
    case "rare":
      return {
        letter: "R",
        color: colors.rarity.rare.color,
        glow: colors.rarity.rare.glow,
      };
    case "uncommon":
      return {
        letter: "U",
        color: colors.rarity.uncommon.color,
        glow: colors.rarity.uncommon.glow,
      };
    default:
      return {
        letter: "C",
        color: colors.rarity.common.color,
        glow: colors.rarity.common.glow,
      };
  }
}

interface ArtistCardGridItemProps {
  card: CardSummary;
  onClick: () => void;
}

function ArtistCardGridItem({
  card,
  onClick,
}: ArtistCardGridItemProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const { letter, color, glow } = getRarityStyle(card.rarity ?? null);

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative group cursor-pointer transition-all duration-300"
      style={{
        transform: isHovered ? "translateY(-4px) scale(1.02)" : "none",
      }}
    >
      {/* Card image */}
      <div
        className="relative rounded-lg overflow-hidden"
        style={{
          aspectRatio: "488 / 680",
          background: colors.void.medium,
          boxShadow: isHovered
            ? `0 12px 40px rgba(0,0,0,0.5), 0 0 20px ${glow}`
            : "0 4px 20px rgba(0,0,0,0.3)",
        }}
      >
        {card.image || card.image_small ? (
          <img
            src={card.image || card.image_small || ""}
            alt={card.name}
            loading="lazy"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <i
              className="ms ms-artist-nib text-4xl"
              style={{ color: colors.text.muted, opacity: 0.3 }}
            />
          </div>
        )}

        {/* Hover overlay */}
        <div
          className="absolute inset-0 transition-opacity duration-300"
          style={{
            background: `linear-gradient(180deg, transparent 50%, ${colors.void.deepest}ee 100%)`,
            opacity: isHovered ? 1 : 0,
          }}
        />

        {/* Rarity badge */}
        <div
          className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300"
          style={{
            background: `${color}30`,
            color,
            border: `1px solid ${color}50`,
            boxShadow: isHovered ? `0 0 10px ${glow}` : "none",
          }}
        >
          {letter}
        </div>
      </div>

      {/* Card info */}
      <div className="mt-2 px-1">
        <p
          className="text-xs font-display truncate transition-colors duration-300"
          style={{
            color: isHovered ? colors.text.bright : colors.text.standard,
          }}
        >
          {card.name}
        </p>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs" style={{ color: colors.text.muted }}>
            {card.set_code?.toUpperCase()}
          </span>
          {card.mana_cost && <ManaCost cost={card.mana_cost} size="small" />}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SEARCH BAR
// ═══════════════════════════════════════════════════════════════

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function SearchBar({
  value,
  onChange,
  placeholder = "Search...",
}: SearchBarProps): ReactNode {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="relative">
      {/* Glow effect */}
      <div
        className="absolute -inset-1 rounded-lg transition-opacity duration-300"
        style={{
          background: `linear-gradient(135deg, ${colors.gold.dim}30 0%, ${colors.mana.white.color}20 100%)`,
          opacity: isFocused ? 1 : 0,
          filter: "blur(8px)",
        }}
      />

      <div
        className="relative flex items-center transition-all duration-300"
        style={{
          background: colors.void.deep,
          border: `1px solid ${isFocused ? colors.gold.dim : colors.border.standard}`,
          borderRadius: 8,
        }}
      >
        <div
          className="pl-3 pr-2 transition-colors duration-300"
          style={{ color: isFocused ? colors.gold.dim : colors.text.muted }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>

        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className="flex-1 h-9 bg-transparent text-sm font-body outline-none"
          style={{ color: colors.text.standard }}
        />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// STATS ORB (mini version)
// ═══════════════════════════════════════════════════════════════

interface StatBadgeProps {
  value: string | number;
  label: string;
  accentColor?: string;
}

function StatBadge({
  value,
  label,
  accentColor = colors.gold.standard,
}: StatBadgeProps): ReactNode {
  return (
    <div className="flex flex-col items-center">
      <span className="font-display text-2xl" style={{ color: accentColor }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </span>
      <span
        className="text-xs uppercase tracking-wider"
        style={{ color: colors.text.muted }}
      >
        {label}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

const PAGE_SIZE = 50;
const DEBOUNCE_MS = 300;

export function ArtistsScreen(): ReactNode {
  const [artists, setArtists] = useState<ArtistSummary[]>([]);
  const [selectedArtist, setSelectedArtist] = useState<ArtistSummary | null>(
    null,
  );
  const [artistCards, setArtistCards] = useState<CardSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isLoadingArtists, setIsLoadingArtists] = useState(true);
  const [isLoadingCards, setIsLoadingCards] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalArtists, setTotalArtists] = useState(0);
  const [artistsOffset, setArtistsOffset] = useState(0);
  const [selectedCardName, setSelectedCardName] = useState<string | null>(null);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search query
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setArtistsOffset(0);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery]);

  // Load artists when debounced query changes
  useEffect(() => {
    async function loadArtists(): Promise<void> {
      setIsLoadingArtists(true);
      setError(null);

      try {
        const result = await window.electronAPI.artists.list({
          query: debouncedQuery || undefined,
          limit: PAGE_SIZE,
          offset: 0,
        });

        if (!result?.artists) {
          throw new Error(
            "Invalid API response - please restart the app to reload the API server",
          );
        }

        setArtists(result.artists);
        setTotalArtists(result.total_count);
        setArtistsOffset(0);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoadingArtists(false);
      }
    }

    loadArtists();
  }, [debouncedQuery]);

  // Load artist cards when selection changes
  const loadArtistCards = useCallback(async (artist: ArtistSummary) => {
    setIsLoadingCards(true);
    setArtistCards([]);

    try {
      const result = await window.electronAPI.artists.getCards(artist.name);
      setArtistCards(result.cards ?? []);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoadingCards(false);
    }
  }, []);

  const handleSelectArtist = (artist: ArtistSummary): void => {
    setSelectedArtist(artist);
    loadArtistCards(artist);
  };

  const handleLoadMoreArtists = async (): Promise<void> => {
    if (isLoadingArtists) return;

    const nextOffset = artistsOffset + PAGE_SIZE;
    setIsLoadingArtists(true);

    try {
      const result = await window.electronAPI.artists.list({
        query: debouncedQuery || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });

      setArtists((prev) => [...prev, ...result.artists]);
      setArtistsOffset(nextOffset);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoadingArtists(false);
    }
  };

  const handleCardClick = (card: CardSummary): void => {
    setSelectedCardName(card.name);
  };

  const handleCloseModal = (): void => {
    setSelectedCardName(null);
  };

  const hasMoreArtists = artists.length < totalArtists;

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 100% 80% at 0% 0%, ${colors.mana.white.color}08 0%, transparent 50%),
      radial-gradient(ellipse 80% 60% at 100% 100%, ${colors.gold.glow}10 0%, transparent 50%),
      ${colors.void.deepest}
    `,
  };

  return (
    <div className="h-full flex flex-col relative" style={containerStyle}>
      {/* Background effect */}
      <ConstellationBackground />

      {/* Header */}
      <div
        className="relative z-10 p-6 border-b"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <i
                className="ms ms-artist-nib text-xl"
                style={{ color: colors.mana.white.color, opacity: 0.8 }}
              />
              <h1
                className="font-display text-2xl tracking-widest"
                style={{
                  background: `linear-gradient(135deg, ${colors.mana.white.color} 0%, ${colors.gold.standard} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                GALLERY
              </h1>
            </div>
            <p className="text-sm font-body" style={{ color: colors.text.dim }}>
              Explore the artists behind the cards
            </p>
          </div>

          <div className="w-64">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search artists..."
            />
          </div>
        </div>
      </div>

      {error && (
        <div
          className="relative z-10 mx-6 mt-4 p-3 rounded-lg text-sm"
          style={{
            background: `${colors.status.error}15`,
            border: `1px solid ${colors.status.error}30`,
            color: colors.status.error,
          }}
        >
          {error}
        </div>
      )}

      {/* Main content - split view */}
      <div className="relative z-10 flex-1 flex min-h-0">
        {/* Left panel - Artist list */}
        <div
          className="w-80 border-r flex flex-col"
          style={{ borderColor: colors.border.subtle }}
        >
          {/* List header */}
          <div
            className="px-4 py-3 flex items-center justify-between"
            style={{
              background: `${colors.void.medium}80`,
              borderBottom: `1px solid ${colors.border.subtle}`,
            }}
          >
            <span
              className="text-xs font-display uppercase tracking-wider"
              style={{ color: colors.text.muted }}
            >
              Artists
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: `${colors.gold.standard}20`,
                color: colors.gold.dim,
              }}
            >
              {totalArtists.toLocaleString()}
            </span>
          </div>

          {/* Artist list */}
          <div className="flex-1 overflow-auto">
            {isLoadingArtists && artists.length === 0 ? (
              <div className="p-8 text-center">
                <div
                  className="w-6 h-6 mx-auto mb-3 rounded-full border-2 border-t-transparent"
                  style={{
                    borderColor: colors.gold.dim,
                    borderTopColor: "transparent",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <span style={{ color: colors.text.muted }}>
                  Loading artists...
                </span>
              </div>
            ) : artists.length === 0 ? (
              <div className="p-8 text-center">
                <i
                  className="ms ms-artist-nib text-3xl mb-3"
                  style={{ color: colors.text.muted, opacity: 0.3 }}
                />
                <p style={{ color: colors.text.muted }}>No artists found</p>
              </div>
            ) : (
              <>
                {artists.map((artist) => (
                  <ArtistListItem
                    key={artist.name}
                    artist={artist}
                    isSelected={selectedArtist?.name === artist.name}
                    onClick={() => handleSelectArtist(artist)}
                  />
                ))}
                {hasMoreArtists && (
                  <button
                    onClick={handleLoadMoreArtists}
                    disabled={isLoadingArtists}
                    className="w-full py-3 text-sm font-body transition-all duration-300"
                    style={{
                      background: colors.void.light,
                      color: isLoadingArtists
                        ? colors.text.muted
                        : colors.gold.standard,
                      borderTop: `1px solid ${colors.border.subtle}`,
                    }}
                    onMouseEnter={(e) => {
                      if (!isLoadingArtists) {
                        e.currentTarget.style.background = colors.void.lighter;
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = colors.void.light;
                    }}
                  >
                    {isLoadingArtists
                      ? "Loading..."
                      : `Load more (${(totalArtists - artists.length).toLocaleString()} remaining)`}
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right panel - Artist details */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedArtist ? (
            <div className="flex-1 flex flex-col items-center justify-center">
              <i
                className="ms ms-artist-nib text-6xl mb-4"
                style={{ color: colors.gold.dim, opacity: 0.2 }}
              />
              <p
                className="font-display text-lg tracking-wide"
                style={{ color: colors.text.muted }}
              >
                Select an artist to explore their work
              </p>
            </div>
          ) : (
            <>
              {/* Artist header */}
              <div
                className="p-6 border-b"
                style={{ borderColor: colors.border.subtle }}
              >
                <h2
                  className="font-display text-3xl tracking-wide mb-4"
                  style={{ color: colors.text.bright }}
                >
                  {selectedArtist.name}
                </h2>

                <div className="flex gap-8">
                  <StatBadge
                    value={selectedArtist.card_count}
                    label="Cards"
                    accentColor={colors.gold.standard}
                  />
                  <StatBadge
                    value={selectedArtist.sets_count}
                    label="Sets"
                    accentColor={colors.mana.blue.color}
                  />
                  {selectedArtist.first_card_year &&
                    selectedArtist.most_recent_year && (
                      <StatBadge
                        value={
                          selectedArtist.first_card_year ===
                          selectedArtist.most_recent_year
                            ? `${selectedArtist.first_card_year}`
                            : `${selectedArtist.first_card_year}-${selectedArtist.most_recent_year}`
                        }
                        label="Active"
                        accentColor={colors.mana.green.color}
                      />
                    )}
                </div>
              </div>

              {/* Cards grid */}
              <div className="flex-1 overflow-auto p-6">
                {/* Section header */}
                <div className="flex items-center gap-3 mb-4">
                  <span
                    className="w-8 h-px"
                    style={{ background: colors.border.standard }}
                  />
                  <span
                    className="text-xs font-display uppercase tracking-widest"
                    style={{ color: colors.text.muted }}
                  >
                    Artwork ({artistCards.length})
                  </span>
                  <span
                    className="flex-1 h-px"
                    style={{ background: colors.border.standard }}
                  />
                </div>

                {isLoadingCards ? (
                  <div className="flex items-center justify-center py-12">
                    <div
                      className="w-8 h-8 rounded-full border-2 border-t-transparent"
                      style={{
                        borderColor: colors.gold.dim,
                        borderTopColor: "transparent",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                  </div>
                ) : artistCards.length === 0 ? (
                  <div className="text-center py-12">
                    <p style={{ color: colors.text.muted }}>No cards found</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                    {artistCards.map((card) => (
                      <ArtistCardGridItem
                        key={card.uuid ?? card.name}
                        card={card}
                        onClick={() => handleCardClick(card)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Card detail modal */}
      {selectedCardName && (
        <CardDetailModal
          cardName={selectedCardName}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}

export default ArtistsScreen;
