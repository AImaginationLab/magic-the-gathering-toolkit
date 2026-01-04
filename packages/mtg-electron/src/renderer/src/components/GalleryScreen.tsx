/**
 * GalleryScreen - The Art Collector's Gallery
 *
 * A beautiful gallery view for browsing card art across printings.
 * Features a masonry-style grid with artist grouping, smooth transitions,
 * and an immersive full-screen viewer.
 */
import { useState, useEffect, useMemo, useRef } from "react";

import { colors, getRarityColor } from "../theme";

import type { ReactNode, CSSProperties } from "react";
import type { PrintingInfo } from "../../../shared/types/api";

interface GalleryScreenProps {
  cardName: string;
  onBack: () => void;
  onCardClick?: (cardName: string) => void;
}

// Constellation background for ambient effect
function ConstellationBackground(): ReactNode {
  const lines = useMemo(() => {
    const points = Array.from({ length: 15 }, () => ({
      x: 5 + Math.random() * 90,
      y: 5 + Math.random() * 90,
      brightness: 0.2 + Math.random() * 0.5,
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
        if (dist < 30 && connections.length < 15) {
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
        <linearGradient
          id="galleryLineGrad"
          x1="0%"
          y1="0%"
          x2="100%"
          y2="100%"
        >
          <stop offset="0%" stopColor={colors.gold.dim} />
          <stop offset="50%" stopColor={colors.mana.blue.color} />
          <stop offset="100%" stopColor="#ba68c8" />
        </linearGradient>
        <filter id="galleryGlow">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {lines.connections.map((line, i) => (
        <line
          key={`line-${i}`}
          x1={`${line.x1}%`}
          y1={`${line.y1}%`}
          x2={`${line.x2}%`}
          y2={`${line.y2}%`}
          stroke="url(#galleryLineGrad)"
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
          r={1 + point.brightness * 2}
          fill={
            i % 3 === 0
              ? colors.gold.dim
              : i % 3 === 1
                ? colors.mana.blue.color
                : "#ba68c8"
          }
          filter="url(#galleryGlow)"
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.25}s`,
            opacity: point.brightness,
          }}
        />
      ))}
    </svg>
  );
}

interface GalleryCardProps {
  printing: PrintingInfo;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

function GalleryCard({
  printing,
  index,
  isSelected,
  onClick,
}: GalleryCardProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  const cardRef = useRef<HTMLDivElement>(null);

  const rarityColor = printing.rarity
    ? getRarityColor(printing.rarity)
    : colors.text.dim;

  // Mouse tracking for 3D effect
  const handleMouseMove = (e: React.MouseEvent): void => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setMousePos({ x, y });
  };

  // Calculate 3D transform
  const rotateX = isHovered ? (mousePos.y - 0.5) * -10 : 0;
  const rotateY = isHovered ? (mousePos.x - 0.5) * 10 : 0;

  return (
    <div
      ref={cardRef}
      className="relative cursor-pointer group"
      style={{
        perspective: "1000px",
        transformStyle: "preserve-3d",
        animation: `gallery-card-appear 0.5s ease-out forwards`,
        animationDelay: `${index * 0.05}s`,
        opacity: 0,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setMousePos({ x: 0.5, y: 0.5 });
      }}
      onMouseMove={handleMouseMove}
      onClick={onClick}
    >
      {/* Outer glow */}
      <div
        className="absolute -inset-2 rounded-xl transition-opacity duration-300 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at ${mousePos.x * 100}% ${mousePos.y * 100}%, ${rarityColor}40 0%, transparent 60%)`,
          opacity: isHovered ? 0.8 : 0,
          filter: "blur(15px)",
        }}
      />

      {/* Selected ring */}
      {isSelected && (
        <div
          className="absolute -inset-1 rounded-xl pointer-events-none"
          style={{
            border: `2px solid ${colors.gold.standard}`,
            boxShadow: `0 0 20px ${colors.gold.glow}`,
          }}
        />
      )}

      {/* Card container */}
      <div
        className="relative rounded-lg overflow-hidden transition-all duration-300"
        style={{
          background: colors.void.medium,
          boxShadow: isHovered
            ? `0 20px 40px rgba(0,0,0,0.5), 0 0 30px ${rarityColor}30`
            : `0 4px 20px rgba(0,0,0,0.4)`,
          transform: `
            rotateX(${rotateX}deg)
            rotateY(${rotateY}deg)
            ${isHovered ? "translateY(-8px) scale(1.03)" : ""}
          `,
          transformStyle: "preserve-3d",
        }}
      >
        {/* Card image */}
        <div
          style={{
            aspectRatio: "488 / 680",
            background: colors.void.light,
            position: "relative",
          }}
        >
          {printing.image ? (
            <img
              src={printing.image}
              alt={`${printing.set_code || "Unknown"} printing`}
              className="w-full h-full object-cover transition-opacity duration-300"
              style={{ opacity: imageLoaded ? 1 : 0 }}
              loading="lazy"
              onLoad={() => setImageLoaded(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <i
                className="ms ms-planeswalker"
                style={{ fontSize: 48, color: colors.text.muted, opacity: 0.3 }}
              />
            </div>
          )}

          {/* Loading shimmer */}
          {!imageLoaded && printing.image && (
            <div
              className="absolute inset-0"
              style={{
                background: `linear-gradient(90deg, ${colors.void.light} 0%, ${colors.void.lighter} 50%, ${colors.void.light} 100%)`,
                animation: "shimmer 1.5s infinite",
              }}
            />
          )}

          {/* Hover overlay with info */}
          <div
            className="absolute inset-0 flex flex-col justify-end p-3 transition-opacity duration-300"
            style={{
              background: `linear-gradient(180deg, transparent 40%, ${colors.void.deepest}ee 100%)`,
              opacity: isHovered ? 1 : 0,
            }}
          >
            {printing.artist && (
              <div
                className="text-xs font-body truncate"
                style={{ color: colors.text.dim }}
              >
                <span style={{ opacity: 0.6 }}>Art by</span>{" "}
                <span style={{ color: colors.text.standard }}>
                  {printing.artist}
                </span>
              </div>
            )}
          </div>

          {/* Rarity badge */}
          <div
            className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300"
            style={{
              background: `${rarityColor}30`,
              color: rarityColor,
              border: `1px solid ${rarityColor}50`,
              boxShadow: isHovered ? `0 0 12px ${rarityColor}60` : "none",
            }}
          >
            {printing.rarity?.[0]?.toUpperCase() || "?"}
          </div>

          {/* Price badge */}
          {printing.price_usd != null && printing.price_usd > 0 && (
            <div
              className="absolute bottom-2 left-2 px-2 py-0.5 rounded text-xs font-mono font-bold transition-opacity duration-300"
              style={{
                background: `${colors.void.deepest}dd`,
                color: colors.gold.standard,
                border: `1px solid ${colors.gold.dim}40`,
                opacity: isHovered ? 0 : 1,
              }}
            >
              $
              {printing.price_usd < 1
                ? printing.price_usd.toFixed(2)
                : Math.round(printing.price_usd)}
            </div>
          )}
        </div>

        {/* Card info strip */}
        <div
          className="p-3 border-t"
          style={{
            background: colors.void.deep,
            borderColor: colors.border.subtle,
          }}
        >
          <div className="flex items-center justify-between gap-2">
            {/* Set info */}
            <div className="flex items-center gap-2 min-w-0">
              {printing.set_code && (
                <i
                  className={`ss ss-${printing.set_code.toLowerCase()}`}
                  style={{
                    fontSize: 14,
                    color: rarityColor,
                  }}
                />
              )}
              <span
                className="font-mono text-xs truncate"
                style={{ color: colors.text.dim }}
              >
                {printing.set_code?.toUpperCase()}
                {printing.collector_number && ` #${printing.collector_number}`}
              </span>
            </div>

            {/* Release year */}
            {printing.release_date && (
              <span
                className="text-xs shrink-0"
                style={{ color: colors.text.muted }}
              >
                {printing.release_date.substring(0, 4)}
              </span>
            )}
          </div>

          {/* Set name */}
          {printing.release_date && (
            <div
              className="text-xs mt-1 truncate"
              style={{ color: colors.text.muted }}
            >
              Released {printing.release_date}
            </div>
          )}
        </div>

        {/* Shine effect */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-300"
          style={{
            background: `linear-gradient(
              ${110 + (mousePos.x - 0.5) * 30}deg,
              transparent 30%,
              rgba(255,255,255,0.05) 50%,
              transparent 70%
            )`,
            opacity: isHovered ? 1 : 0,
          }}
        />
      </div>
    </div>
  );
}

// Full-screen lightbox viewer
interface LightboxProps {
  printings: PrintingInfo[];
  currentIndex: number;
  cardName: string;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

function Lightbox({
  printings,
  currentIndex,
  cardName,
  onClose,
  onNavigate,
}: LightboxProps): ReactNode {
  const printing = printings[currentIndex];
  if (!printing) return null;

  const rarityColor = printing.rarity
    ? getRarityColor(printing.rarity)
    : colors.text.dim;

  const handlePrev = (e: React.MouseEvent): void => {
    e.stopPropagation();
    const newIndex = currentIndex > 0 ? currentIndex - 1 : printings.length - 1;
    onNavigate(newIndex);
  };

  const handleNext = (e: React.MouseEvent): void => {
    e.stopPropagation();
    const newIndex = currentIndex < printings.length - 1 ? currentIndex + 1 : 0;
    onNavigate(newIndex);
  };

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: globalThis.KeyboardEvent): void {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") {
        const newIndex =
          currentIndex > 0 ? currentIndex - 1 : printings.length - 1;
        onNavigate(newIndex);
      } else if (e.key === "ArrowRight") {
        const newIndex =
          currentIndex < printings.length - 1 ? currentIndex + 1 : 0;
        onNavigate(newIndex);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, printings.length, onClose, onNavigate]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0, 0, 0, 0.95)" }}
      onClick={onClose}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-6 right-6 w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200"
        style={{
          background: colors.void.lighter,
          border: `1px solid ${colors.border.standard}`,
          color: colors.text.dim,
          fontSize: 24,
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
        ×
      </button>

      {/* Navigation arrows */}
      {printings.length > 1 && (
        <>
          <button
            onClick={handlePrev}
            className="absolute left-6 top-1/2 -translate-y-1/2 w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200"
            style={{
              background: `${colors.void.deepest}cc`,
              border: `1px solid ${colors.border.standard}`,
              color: colors.text.bright,
              fontSize: 28,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.gold.standard;
              e.currentTarget.style.color = colors.void.deepest;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = `${colors.void.deepest}cc`;
              e.currentTarget.style.color = colors.text.bright;
            }}
          >
            ‹
          </button>
          <button
            onClick={handleNext}
            className="absolute right-6 top-1/2 -translate-y-1/2 w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200"
            style={{
              background: `${colors.void.deepest}cc`,
              border: `1px solid ${colors.border.standard}`,
              color: colors.text.bright,
              fontSize: 28,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = colors.gold.standard;
              e.currentTarget.style.color = colors.void.deepest;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = `${colors.void.deepest}cc`;
              e.currentTarget.style.color = colors.text.bright;
            }}
          >
            ›
          </button>
        </>
      )}

      {/* Main content */}
      <div
        className="flex flex-col items-center max-w-4xl max-h-[90vh] px-20"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Card image */}
        <div
          className="relative rounded-xl overflow-hidden"
          style={{
            boxShadow: `0 0 60px ${rarityColor}40, 0 30px 60px rgba(0,0,0,0.6)`,
            maxHeight: "70vh",
          }}
        >
          {printing.image ? (
            <img
              src={printing.image}
              alt={`${printing.set_code || "Unknown"} printing`}
              className="max-h-[70vh] w-auto object-contain"
            />
          ) : (
            <div
              className="w-80 flex items-center justify-center"
              style={{
                aspectRatio: "488 / 680",
                background: colors.void.light,
              }}
            >
              <i
                className="ms ms-planeswalker"
                style={{ fontSize: 64, color: colors.text.muted, opacity: 0.3 }}
              />
            </div>
          )}
        </div>

        {/* Card info */}
        <div className="mt-6 text-center" style={{ maxWidth: 400 }}>
          <h2
            className="font-display text-2xl tracking-wide mb-2"
            style={{ color: colors.text.bright }}
          >
            {cardName}
          </h2>

          <div className="flex items-center justify-center gap-3 mb-3">
            {printing.set_code && (
              <span
                className="inline-flex items-center gap-2 px-3 py-1 rounded-lg font-mono text-sm"
                style={{
                  background: `${colors.mana.blue.color}20`,
                  border: `1px solid ${colors.mana.blue.color}40`,
                  color: colors.mana.blue.color,
                }}
              >
                <i className={`ss ss-${printing.set_code.toLowerCase()}`} />
                {printing.set_code.toUpperCase()}
                {printing.collector_number && ` #${printing.collector_number}`}
              </span>
            )}
            {printing.rarity && (
              <span
                className="text-sm capitalize"
                style={{ color: rarityColor }}
              >
                {printing.rarity}
              </span>
            )}
          </div>

          {printing.release_date && (
            <div className="text-sm mb-2" style={{ color: colors.text.dim }}>
              Released {printing.release_date}
            </div>
          )}

          {printing.artist && (
            <div className="text-sm" style={{ color: colors.text.muted }}>
              Art by{" "}
              <span style={{ color: colors.text.standard }}>
                {printing.artist}
              </span>
            </div>
          )}

          {/* Price */}
          {printing.price_usd != null && (
            <div className="mt-3">
              <span
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-display"
                style={{
                  background: `${colors.gold.standard}15`,
                  border: `1px solid ${colors.gold.dim}40`,
                }}
              >
                <span style={{ color: colors.text.muted }}>Price:</span>
                <span style={{ color: colors.gold.bright, fontWeight: 600 }}>
                  ${printing.price_usd.toFixed(2)}
                </span>
                {printing.price_usd_foil != null && (
                  <span style={{ color: colors.text.muted }}>
                    (Foil: ${printing.price_usd_foil.toFixed(2)})
                  </span>
                )}
              </span>
            </div>
          )}
        </div>

        {/* Thumbnail strip */}
        {printings.length > 1 && (
          <div
            className="mt-6 flex items-center gap-2 overflow-x-auto pb-2 max-w-full"
            style={{ scrollbarWidth: "thin" }}
          >
            {printings.map((p, idx) => (
              <button
                key={`${p.set_code}-${p.collector_number}-${idx}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigate(idx);
                }}
                className="shrink-0 rounded overflow-hidden transition-all duration-200"
                style={{
                  width: 48,
                  height: 67,
                  border:
                    idx === currentIndex
                      ? `2px solid ${colors.gold.standard}`
                      : `1px solid ${colors.border.subtle}`,
                  boxShadow:
                    idx === currentIndex
                      ? `0 0 10px ${colors.gold.glow}`
                      : "none",
                  opacity: idx === currentIndex ? 1 : 0.6,
                }}
              >
                {p.image ? (
                  <img
                    src={p.image}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div
                    className="w-full h-full flex items-center justify-center"
                    style={{ background: colors.void.light }}
                  >
                    <i
                      className={`ss ss-${p.set_code?.toLowerCase() || "default"}`}
                      style={{ fontSize: 12, color: colors.text.muted }}
                    />
                  </div>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Counter */}
        <div
          className="mt-4 text-xs font-mono"
          style={{ color: colors.text.muted }}
        >
          {currentIndex + 1} of {printings.length} printings
        </div>
      </div>
    </div>
  );
}

export function GalleryScreen({
  cardName,
  onBack,
}: GalleryScreenProps): ReactNode {
  const [printings, setPrintings] = useState<PrintingInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<"date" | "price" | "set">("date");
  const [filterArtist, setFilterArtist] = useState<string | null>(null);

  // Load printings
  useEffect(() => {
    async function loadPrintings(): Promise<void> {
      setIsLoading(true);
      setError(null);

      // Handle double-faced cards
      const searchName = cardName.includes("//")
        ? cardName.split("//")[0].trim()
        : cardName;

      try {
        const result =
          await window.electronAPI.api.cards.getPrintings(searchName);
        setPrintings(result.printings ?? []);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load printings",
        );
      } finally {
        setIsLoading(false);
      }
    }

    loadPrintings();
  }, [cardName]);

  // Get unique artists for filtering
  const artists = useMemo(() => {
    const artistSet = new Set<string>();
    printings.forEach((p) => {
      if (p.artist) artistSet.add(p.artist);
    });
    return Array.from(artistSet).sort();
  }, [printings]);

  // Sort and filter printings
  const displayedPrintings = useMemo(() => {
    let filtered = filterArtist
      ? printings.filter((p) => p.artist === filterArtist)
      : printings;

    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "price":
          return (b.price_usd ?? 0) - (a.price_usd ?? 0);
        case "set":
          return (a.set_code ?? "").localeCompare(b.set_code ?? "");
        case "date":
        default:
          return (b.release_date ?? "").localeCompare(a.release_date ?? "");
      }
    });
  }, [printings, sortBy, filterArtist]);

  // Calculate stats
  const stats = useMemo(() => {
    const priced = printings.filter(
      (p) => p.price_usd != null && p.price_usd > 0,
    );
    const totalValue = priced.reduce((sum, p) => sum + (p.price_usd ?? 0), 0);
    const avgPrice = priced.length > 0 ? totalValue / priced.length : 0;
    const maxPrice = Math.max(...priced.map((p) => p.price_usd ?? 0), 0);

    return {
      total: printings.length,
      artists: artists.length,
      avgPrice,
      maxPrice,
      totalValue,
    };
  }, [printings, artists.length]);

  const handleCardClick = (index: number): void => {
    setSelectedIndex(index);
  };

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 100% 80% at 0% 0%, ${colors.mana.blue.color}08 0%, transparent 50%),
      radial-gradient(ellipse 80% 60% at 100% 100%, #ba68c820 0%, transparent 50%),
      radial-gradient(ellipse 60% 40% at 50% 50%, ${colors.gold.glow}10 0%, transparent 60%),
      ${colors.void.deepest}
    `,
  };

  return (
    <div className="h-full flex flex-col relative" style={containerStyle}>
      <ConstellationBackground />

      {/* Header */}
      <div
        className="relative z-10 p-6 border-b"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center gap-4 mb-4">
          {/* Back button */}
          <button
            onClick={onBack}
            className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200"
            style={{
              background: colors.void.lighter,
              border: `1px solid ${colors.border.standard}`,
              color: colors.text.dim,
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
            ←
          </button>

          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <i
                className="ms ms-artist-brush"
                style={{ color: "#ba68c8", fontSize: 24, opacity: 0.8 }}
              />
              <h1
                className="font-display text-2xl tracking-widest"
                style={{
                  background: `linear-gradient(135deg, ${colors.mana.blue.color} 0%, #ba68c8 50%, ${colors.gold.standard} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                ART GALLERY
              </h1>
            </div>
            <p className="text-sm font-body" style={{ color: colors.text.dim }}>
              {cardName} — {stats.total} printing{stats.total !== 1 ? "s" : ""}{" "}
              by {stats.artists} artist{stats.artists !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-6">
            {stats.avgPrice > 0 && (
              <div className="text-center">
                <div
                  className="font-display text-lg"
                  style={{ color: colors.gold.standard }}
                >
                  ${stats.avgPrice.toFixed(2)}
                </div>
                <div
                  className="text-xs uppercase tracking-wider"
                  style={{ color: colors.text.muted }}
                >
                  Avg Price
                </div>
              </div>
            )}
            {stats.maxPrice > 0 && (
              <div className="text-center">
                <div
                  className="font-display text-lg"
                  style={{ color: colors.rarity.mythic.color }}
                >
                  ${stats.maxPrice.toFixed(0)}
                </div>
                <div
                  className="text-xs uppercase tracking-wider"
                  style={{ color: colors.text.muted }}
                >
                  Highest
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          {/* Sort */}
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: colors.text.muted }}>
              Sort:
            </span>
            <div
              className="flex rounded-lg overflow-hidden"
              style={{ border: `1px solid ${colors.border.standard}` }}
            >
              {(["date", "price", "set"] as const).map((option) => (
                <button
                  key={option}
                  onClick={() => setSortBy(option)}
                  className="px-3 py-1.5 text-xs font-display uppercase tracking-wide transition-colors"
                  style={{
                    background:
                      sortBy === option
                        ? colors.gold.standard
                        : colors.void.light,
                    color:
                      sortBy === option ? colors.void.deepest : colors.text.dim,
                  }}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          {/* Artist filter */}
          {artists.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: colors.text.muted }}>
                Artist:
              </span>
              <select
                value={filterArtist ?? ""}
                onChange={(e) => setFilterArtist(e.target.value || null)}
                className="h-8 px-3 rounded-lg text-xs"
                style={{
                  background: colors.void.light,
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.standard,
                  outline: "none",
                }}
              >
                <option value="">All Artists ({artists.length})</option>
                {artists.map((artist) => (
                  <option key={artist} value={artist}>
                    {artist}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Filtered count */}
          {filterArtist && (
            <span className="text-xs" style={{ color: colors.text.muted }}>
              Showing {displayedPrintings.length} of {printings.length}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div
                className="w-10 h-10 mx-auto mb-4 rounded-full border-2 border-t-transparent"
                style={{
                  borderColor: "#ba68c8",
                  borderTopColor: "transparent",
                  animation: "spin 1s linear infinite",
                }}
              />
              <p
                className="font-display tracking-wider text-sm"
                style={{ color: colors.text.muted }}
              >
                Loading gallery...
              </p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div
              className="p-6 rounded-xl max-w-md text-center"
              style={{
                background: `${colors.status.error}15`,
                border: `1px solid ${colors.status.error}30`,
              }}
            >
              <i
                className="ms ms-ability-menace text-2xl mb-3"
                style={{ color: colors.status.error }}
              />
              <p style={{ color: colors.status.error }}>{error}</p>
            </div>
          </div>
        ) : displayedPrintings.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <i
                className="ms ms-artist-brush text-5xl mb-4"
                style={{ color: colors.text.muted, opacity: 0.3 }}
              />
              <p
                className="font-display text-lg"
                style={{ color: colors.text.muted }}
              >
                No printings found
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-5">
            {displayedPrintings.map((printing, index) => (
              <GalleryCard
                key={`${printing.set_code}-${printing.collector_number}-${index}`}
                printing={printing}
                index={index}
                isSelected={selectedIndex === index}
                onClick={() => handleCardClick(index)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {selectedIndex !== null && (
        <Lightbox
          printings={displayedPrintings}
          currentIndex={selectedIndex}
          cardName={cardName}
          onClose={() => setSelectedIndex(null)}
          onNavigate={setSelectedIndex}
        />
      )}

      {/* Global animations */}
      <style>{`
        @keyframes constellation-pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        @keyframes star-twinkle {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.3); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes gallery-card-appear {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
}

export default GalleryScreen;
