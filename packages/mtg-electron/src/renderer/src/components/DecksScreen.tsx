/**
 * DecksScreen - Arcane Grimoire
 *
 * Browse and manage MTG decks with format-specific theming,
 * subtle 3D mouse tracking, and constellation background.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from "react";

import { colors } from "../theme";
import {
  getFormatColor,
  getFormatGlow,
  getFormatIcon,
} from "../utils/formatUtils";

import type { ReactNode, CSSProperties } from "react";

// Types from the API
interface DeckSummary {
  id: number;
  name: string;
  format: string | null;
  card_count: number;
  sideboard_count: number;
  commander: string | null;
  updated_at: string | null;
}

interface DeckCardFromApi {
  card_name: string;
  quantity: number;
  is_sideboard: boolean;
  is_commander: boolean;
  set_code: string | null;
  collector_number: string | null;
}

// Cache for deck featured images - persisted to localStorage
const DECK_IMAGE_CACHE_KEY = "mtg-deck-featured-images";

function loadDeckImageCache(): Map<number, string> {
  try {
    const stored = localStorage.getItem(DECK_IMAGE_CACHE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Record<string, string>;
      return new Map(
        Object.entries(parsed).map(([k, v]) => [parseInt(k, 10), v]),
      );
    }
  } catch {
    // Ignore parse errors
  }
  return new Map();
}

function saveDeckImageCache(cache: Map<number, string>): void {
  try {
    const obj: Record<string, string> = {};
    cache.forEach((v, k) => {
      obj[k.toString()] = v;
    });
    localStorage.setItem(DECK_IMAGE_CACHE_KEY, JSON.stringify(obj));
  } catch {
    // Ignore storage errors
  }
}

const deckImageCache = loadDeckImageCache();
const deckImageFetching = new Set<number>();

interface CreateDeckFormData {
  name: string;
  format: string;
  commander: string;
  description: string;
}

const FORMATS = [
  { value: "", label: "No Format" },
  { value: "commander", label: "Commander" },
  { value: "standard", label: "Standard" },
  { value: "modern", label: "Modern" },
  { value: "legacy", label: "Legacy" },
  { value: "vintage", label: "Vintage" },
  { value: "pioneer", label: "Pioneer" },
  { value: "pauper", label: "Pauper" },
  { value: "historic", label: "Historic" },
  { value: "brawl", label: "Brawl" },
];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return date.toLocaleDateString();
}

function ConstellationBackground(): ReactNode {
  const lines = useMemo(() => {
    const points = Array.from({ length: 20 }, () => ({
      x: 5 + Math.random() * 90,
      y: 5 + Math.random() * 90,
      brightness: 0.3 + Math.random() * 0.7,
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
        if (dist < 25 && connections.length < 25) {
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
      style={{ opacity: 0.08 }}
    >
      <defs>
        <linearGradient id="deckLineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffd700" />
          <stop offset="50%" stopColor="#ff6b35" />
          <stop offset="100%" stopColor="#4a9eff" />
        </linearGradient>
        <filter id="starGlow">
          <feGaussianBlur stdDeviation="1" result="blur" />
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
          stroke="url(#deckLineGrad)"
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
          r={1 + point.brightness * 1.5}
          fill={i % 3 === 0 ? "#ffd700" : i % 3 === 1 ? "#ff6b35" : "#4a9eff"}
          filter="url(#starGlow)"
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.2}s`,
            opacity: point.brightness,
          }}
        />
      ))}
    </svg>
  );
}

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
      {/* Prismatic glow on focus */}
      <div
        className="absolute -inset-1 rounded-xl transition-all duration-500"
        style={{
          background: isFocused
            ? `linear-gradient(135deg, #ffd70040 0%, #ff6b3540 50%, #4a9eff40 100%)`
            : "transparent",
          filter: "blur(10px)",
          opacity: isFocused ? 1 : 0,
        }}
      />

      <div
        className="relative flex items-center transition-all duration-300"
        style={{
          background: `linear-gradient(135deg, ${colors.void.deep} 0%, ${colors.void.medium} 100%)`,
          border: `1px solid ${isFocused ? "#ffd700" : colors.border.standard}`,
          borderRadius: 12,
          boxShadow: isFocused
            ? `0 0 20px rgba(255, 215, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.05)`
            : `inset 0 1px 0 rgba(255,255,255,0.03)`,
        }}
      >
        <div
          className="pl-4 pr-2 transition-colors duration-300"
          style={{ color: isFocused ? "#ffd700" : colors.text.muted }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
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
          className="flex-1 h-12 bg-transparent text-sm font-body outline-none pr-4"
          style={{ color: colors.text.standard }}
        />
      </div>
    </div>
  );
}

interface DeckCardProps {
  deck: DeckSummary;
  onSelect: (deck: DeckSummary) => void;
  onDelete: (deck: DeckSummary) => void;
}

function DeckCard({ deck, onSelect, onDelete }: DeckCardProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [featuredImage, setFeaturedImage] = useState<string | null>(
    deckImageCache.get(deck.id) || null,
  );
  const [imageLoaded, setImageLoaded] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  const cardRef = useRef<HTMLDivElement>(null);

  const formatColor = getFormatColor(deck.format);
  const formatGlow = getFormatGlow(deck.format);
  const formatIcon = getFormatIcon(deck.format);

  // Mouse tracking for 3D effect
  const handleMouseMove = (e: React.MouseEvent): void => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setMousePos({ x, y });
  };

  // Calculate 3D transform - subtle tilt
  const rotateX = isHovered ? (mousePos.y - 0.5) * -8 : 0;
  const rotateY = isHovered ? (mousePos.x - 0.5) * 8 : 0;

  // Fetch featured card image on mount
  useEffect(() => {
    const cached = deckImageCache.get(deck.id);
    if (cached) {
      if (cached !== "none") {
        setFeaturedImage(cached);
      }
      return;
    }

    if (deckImageFetching.has(deck.id)) {
      return;
    }
    deckImageFetching.add(deck.id);

    async function fetchFeaturedImage(): Promise<void> {
      try {
        const deckDetails = await window.electronAPI.decks.get(deck.id);
        if (!deckDetails?.cards?.length) {
          deckImageCache.set(deck.id, "none");
          saveDeckImageCache(deckImageCache);
          return;
        }

        const cards = deckDetails.cards as DeckCardFromApi[];
        let featuredCardImages: {
          large?: string | null;
          png?: string | null;
          normal?: string | null;
          art_crop?: string | null;
        } | null = null;

        if (deck.format?.toLowerCase() === "commander" && deck.commander) {
          const details = await window.electronAPI.api.cards.getByName(
            deck.commander,
          );
          featuredCardImages = details?.images ?? null;
        } else if (cards.length > 0) {
          const cardsToCheck = cards.slice(0, 15);
          let landFallback: {
            large: string | null;
            png: string | null;
            normal: string;
            art_crop: string;
          } | null = null;

          for (const card of cardsToCheck) {
            try {
              const searchName = card.card_name.split(" // ")[0];
              const searchResult = await window.electronAPI.api.cards.search({
                name: searchName,
                page_size: 1,
              });
              const firstCard = searchResult?.cards?.[0];
              if (firstCard?.image) {
                const cardType = (firstCard.type ?? "").toLowerCase();
                const artCropUrl = firstCard.image.replace(
                  "/normal/",
                  "/art_crop/",
                );
                const images = {
                  large: null,
                  png: null,
                  normal: firstCard.image,
                  art_crop: artCropUrl,
                };

                if (cardType.includes("land")) {
                  if (!landFallback) {
                    landFallback = images;
                  }
                  continue;
                }

                featuredCardImages = images;

                if (cardType.includes("creature")) {
                  break;
                }
              }
            } catch {
              // Skip cards that fail to fetch
            }
          }
          if (!featuredCardImages && landFallback) {
            featuredCardImages = landFallback;
          }
        }

        const imageUrl =
          featuredCardImages?.art_crop ?? featuredCardImages?.normal ?? null;

        if (imageUrl) {
          deckImageCache.set(deck.id, imageUrl);
          saveDeckImageCache(deckImageCache);
          setFeaturedImage(imageUrl);
        } else {
          deckImageCache.set(deck.id, "none");
          saveDeckImageCache(deckImageCache);
        }
      } catch {
        // Don't cache failures
      } finally {
        deckImageFetching.delete(deck.id);
      }
    }

    fetchFeaturedImage();
  }, [deck.id, deck.format, deck.commander]);

  const handleDelete = (e: React.MouseEvent): void => {
    e.stopPropagation();
    if (showDeleteConfirm) {
      onDelete(deck);
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
    }
  };

  const handleCancelDelete = (e: React.MouseEvent): void => {
    e.stopPropagation();
    setShowDeleteConfirm(false);
  };

  return (
    <div
      ref={cardRef}
      className="relative cursor-pointer group"
      style={{
        perspective: "1000px",
        transformStyle: "preserve-3d",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setShowDeleteConfirm(false);
        setMousePos({ x: 0.5, y: 0.5 });
      }}
      onMouseMove={handleMouseMove}
      onClick={() => onSelect(deck)}
    >
      {/* Outer glow - subtle, follows mouse */}
      <div
        className="absolute -inset-1 rounded-xl transition-opacity duration-300 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at ${mousePos.x * 100}% ${mousePos.y * 100}%, ${formatGlow} 0%, transparent 60%)`,
          opacity: isHovered ? 0.5 : 0,
          filter: "blur(12px)",
        }}
      />

      {/* Card container with 3D transform */}
      <div
        className="relative rounded-xl overflow-hidden transition-all duration-300"
        style={{
          background: `linear-gradient(145deg, ${colors.void.deep} 0%, ${colors.void.deepest} 100%)`,
          border: `1px solid ${isHovered ? formatColor : colors.border.subtle}`,
          boxShadow: isHovered
            ? `
              0 12px 30px rgba(0,0,0,0.4),
              0 0 20px ${formatGlow},
              inset 0 1px 0 rgba(255,255,255,0.08)
            `
            : `
              0 4px 16px rgba(0,0,0,0.3),
              inset 0 1px 0 rgba(255,255,255,0.05)
            `,
          transform: `
            rotateX(${rotateX}deg)
            rotateY(${rotateY}deg)
          `,
          transformStyle: "preserve-3d",
          minHeight: "200px",
        }}
      >
        {/* Background artwork */}
        {featuredImage && (
          <>
            <img
              src={featuredImage}
              alt=""
              className="absolute top-0 right-0 h-full object-cover transition-all duration-400"
              loading="lazy"
              style={{
                width: "70%",
                opacity: imageLoaded ? (isHovered ? 0.5 : 0.35) : 0,
                maskImage:
                  "linear-gradient(to right, transparent 0%, black 35%)",
                WebkitMaskImage:
                  "linear-gradient(to right, transparent 0%, black 35%)",
                filter: isHovered
                  ? "saturate(1.1) brightness(1.05)"
                  : "saturate(0.8)",
              }}
              onLoad={() => setImageLoaded(true)}
            />
            {/* Gradient overlay */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: `linear-gradient(to right, ${colors.void.deepest} 35%, ${colors.void.deep}80 60%, transparent 100%)`,
              }}
            />
          </>
        )}

        {/* Accent bar */}
        <div
          className="absolute left-0 top-0 bottom-0 w-1 transition-all duration-300"
          style={{
            background: isHovered ? formatColor : `${formatColor}50`,
            boxShadow: isHovered ? `0 0 8px ${formatGlow}` : "none",
          }}
        />

        {/* Content */}
        <div className="relative z-10 p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              {/* Format badge with icon */}
              {deck.format && (
                <span
                  className="inline-flex items-center gap-2 text-xs font-display tracking-wider px-2.5 py-1 rounded-md mb-3"
                  style={{
                    background: `${formatColor}15`,
                    color: formatColor,
                    border: `1px solid ${formatColor}30`,
                  }}
                >
                  <i className={formatIcon} style={{ fontSize: 11 }} />
                  {deck.format.toUpperCase()}
                </span>
              )}

              {/* Deck name */}
              <h3
                className="font-display text-xl tracking-wide"
                style={{
                  lineHeight: 1.2,
                  color: colors.text.bright,
                  textShadow: `0 2px 8px rgba(0,0,0,0.8)`,
                  wordBreak: "break-word",
                }}
              >
                {deck.name}
              </h3>

              {/* Commander */}
              {deck.commander && (
                <div
                  className="mt-2 flex items-center gap-2"
                  style={{ color: colors.gold.standard }}
                >
                  <i className="ms ms-planeswalker" style={{ fontSize: 12 }} />
                  <span className="text-sm truncate">{deck.commander}</span>
                </div>
              )}
            </div>

            {/* Card count orb */}
            <div
              className="shrink-0 rounded-full flex flex-col items-center justify-center transition-all duration-300"
              style={{
                width: 64,
                height: 64,
                background: `radial-gradient(circle at 30% 30%, ${colors.void.lighter} 0%, ${colors.void.medium} 100%)`,
                border: `1px solid ${isHovered ? formatColor : colors.border.subtle}`,
                boxShadow: isHovered
                  ? `0 0 12px ${formatGlow}, 0 4px 12px rgba(0,0,0,0.3)`
                  : `0 4px 12px rgba(0,0,0,0.2)`,
              }}
            >
              <span
                className="font-display text-xl"
                style={{
                  color: isHovered ? formatColor : colors.text.standard,
                }}
              >
                {deck.card_count}
              </span>
              <span
                className="text-[10px] uppercase tracking-wider"
                style={{ color: colors.text.muted }}
              >
                cards
              </span>
            </div>
          </div>

          {/* Footer */}
          <div
            className="flex items-center justify-between mt-4 pt-3 border-t"
            style={{ borderColor: `${colors.border.subtle}50` }}
          >
            <div className="flex items-center gap-3">
              <span className="text-xs" style={{ color: colors.text.muted }}>
                {formatDate(deck.updated_at)}
              </span>
              {deck.sideboard_count > 0 && (
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    background: colors.void.lighter,
                    color: colors.text.dim,
                  }}
                >
                  +{deck.sideboard_count} sideboard
                </span>
              )}
            </div>

            {/* Delete button */}
            <div
              className="transition-opacity duration-200"
              style={{ opacity: isHovered ? 1 : 0 }}
            >
              {showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <button
                    className="text-xs px-3 py-1.5 rounded transition-colors"
                    style={{
                      background: colors.status.error,
                      color: colors.text.bright,
                    }}
                    onClick={handleDelete}
                  >
                    Confirm
                  </button>
                  <button
                    className="text-xs px-3 py-1.5 rounded transition-colors"
                    style={{
                      background: colors.void.lighter,
                      color: colors.text.dim,
                    }}
                    onClick={handleCancelDelete}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  className="text-xs px-3 py-1.5 rounded transition-colors"
                  style={{
                    background: colors.void.lighter,
                    color: colors.text.dim,
                    border: `1px solid ${colors.border.subtle}`,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = colors.status.error;
                    e.currentTarget.style.color = colors.status.error;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = colors.border.subtle;
                    e.currentTarget.style.color = colors.text.dim;
                  }}
                  onClick={handleDelete}
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Subtle shine effect on hover */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-300"
          style={{
            background: `linear-gradient(
              ${120 + (mousePos.x - 0.5) * 20}deg,
              transparent 40%,
              rgba(255,255,255,0.03) 50%,
              transparent 60%
            )`,
            opacity: isHovered ? 1 : 0,
          }}
        />
      </div>
    </div>
  );
}

interface CreateDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: CreateDeckFormData) => void;
  isCreating: boolean;
}

function CreateDeckModal({
  isOpen,
  onClose,
  onCreate,
  isCreating,
}: CreateDeckModalProps): ReactNode {
  const [formData, setFormData] = useState<CreateDeckFormData>({
    name: "",
    format: "commander",
    commander: "",
    description: "",
  });

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (formData.name.trim()) {
      onCreate(formData);
    }
  };

  const handleChange = (
    field: keyof CreateDeckFormData,
    value: string,
  ): void => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  const formatColor = getFormatColor(formData.format || null);

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: "rgba(0, 0, 0, 0.8)" }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md p-6 rounded-xl"
        style={{
          background: `linear-gradient(180deg, ${colors.void.deep} 0%, ${colors.void.deepest} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: `0 25px 50px rgba(0,0,0,0.5)`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{
              background: `${colors.gold.standard}15`,
              border: `1px solid ${colors.gold.standard}30`,
            }}
          >
            <i
              className="ms ms-saga"
              style={{ color: colors.gold.standard, fontSize: 18 }}
            />
          </div>
          <h2
            className="font-display text-xl tracking-wider"
            style={{ color: colors.gold.standard }}
          >
            Create Deck
          </h2>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Deck Name */}
          <div className="mb-4">
            <label
              className="block text-xs font-display uppercase tracking-wider mb-2"
              style={{ color: colors.text.muted }}
            >
              Deck Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="Enter deck name"
              className="w-full h-11 px-4 text-sm rounded-lg"
              style={{
                background: colors.void.medium,
                border: `1px solid ${formData.name ? colors.gold.dim : colors.border.standard}`,
                color: colors.text.standard,
                outline: "none",
              }}
              autoFocus
            />
          </div>

          {/* Format */}
          <div className="mb-4">
            <label
              className="block text-xs font-display uppercase tracking-wider mb-2"
              style={{ color: colors.text.muted }}
            >
              Format
            </label>
            <select
              value={formData.format}
              onChange={(e) => handleChange("format", e.target.value)}
              className="w-full h-11 px-4 text-sm rounded-lg"
              style={{
                background: colors.void.medium,
                border: `1px solid ${formatColor}50`,
                color: formatColor,
                outline: "none",
              }}
            >
              {FORMATS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          {/* Commander */}
          {formData.format === "commander" && (
            <div className="mb-4">
              <label
                className="block text-xs font-display uppercase tracking-wider mb-2"
                style={{ color: colors.text.muted }}
              >
                Commander
              </label>
              <input
                type="text"
                value={formData.commander}
                onChange={(e) => handleChange("commander", e.target.value)}
                placeholder="Search for a commander..."
                className="w-full h-11 px-4 text-sm rounded-lg"
                style={{
                  background: colors.void.medium,
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.standard,
                  outline: "none",
                }}
              />
            </div>
          )}

          {/* Description */}
          <div className="mb-6">
            <label
              className="block text-xs font-display uppercase tracking-wider mb-2"
              style={{ color: colors.text.muted }}
            >
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange("description", e.target.value)}
              placeholder="Optional description..."
              rows={3}
              className="w-full px-4 py-3 text-sm rounded-lg resize-none"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.standard}`,
                color: colors.text.standard,
                outline: "none",
              }}
            />
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-sm font-display tracking-wide rounded-lg transition-colors"
              style={{
                background: colors.void.lighter,
                color: colors.text.dim,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.name.trim() || isCreating}
              className="px-5 py-2.5 text-sm font-display tracking-wide rounded-lg transition-colors"
              style={{
                background:
                  formData.name.trim() && !isCreating
                    ? colors.gold.standard
                    : colors.void.lighter,
                color:
                  formData.name.trim() && !isCreating
                    ? colors.void.deepest
                    : colors.text.muted,
                cursor:
                  formData.name.trim() && !isCreating
                    ? "pointer"
                    : "not-allowed",
              }}
            >
              {isCreating ? "Creating..." : "Create Deck"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface ImportDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (deckId: number) => void;
}

interface ParsedCard {
  name: string;
  quantity: number;
  is_sideboard: boolean;
  is_commander: boolean;
}

interface ImportDeckResult {
  name: string;
  format: string | null;
  commander: string | null;
  cards: ParsedCard[];
  sideboard: ParsedCard[];
  maybeboard: ParsedCard[];
  source_url: string | null;
  errors: string[];
}

type ImportMode = "url" | "paste";

function ImportDeckModal({
  isOpen,
  onClose,
  onImport,
}: ImportDeckModalProps): ReactNode {
  const [mode, setMode] = useState<ImportMode>("url");
  const [url, setUrl] = useState("");
  const [pasteText, setPasteText] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [parseResult, setParseResult] = useState<ImportDeckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deckName, setDeckName] = useState("");

  const handleParse = async (): Promise<void> => {
    const input = mode === "url" ? url.trim() : pasteText.trim();
    if (!input) return;

    setIsParsing(true);
    setError(null);
    setParseResult(null);

    try {
      const result = await window.electronAPI.decks.parseImport(
        mode === "url" ? { url: input } : { text: input },
      );
      if (result.errors.length > 0 && result.cards.length === 0) {
        setError(result.errors.join(", "));
      } else {
        setParseResult(result);
        // For pasted decks without a name, use a default
        setDeckName(result.name || "Pasted Deck");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsParsing(false);
    }
  };

  const handleImport = async (): Promise<void> => {
    if (!parseResult || !deckName.trim()) return;

    setIsImporting(true);
    setError(null);

    try {
      // Create the deck
      const createResult = await window.electronAPI.decks.create({
        name: deckName,
        format: parseResult.format,
        commander: parseResult.commander,
      });

      // Add all cards
      for (const card of parseResult.cards) {
        await window.electronAPI.decks.addCard(createResult.id, {
          card_name: card.name,
          quantity: card.quantity,
          is_sideboard: false,
          is_commander: card.is_commander,
        });
      }

      // Add sideboard cards
      for (const card of parseResult.sideboard) {
        await window.electronAPI.decks.addCard(createResult.id, {
          card_name: card.name,
          quantity: card.quantity,
          is_sideboard: true,
        });
      }

      onImport(createResult.id);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = (): void => {
    setMode("url");
    setUrl("");
    setPasteText("");
    setParseResult(null);
    setError(null);
    setDeckName("");
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent): void => {
    // Only trigger on Enter in URL mode (paste mode uses textarea which needs Enter for newlines)
    if (
      e.key === "Enter" &&
      mode === "url" &&
      !isParsing &&
      url.trim() &&
      !parseResult
    ) {
      handleParse();
    }
  };

  if (!isOpen) return null;

  const totalCards =
    parseResult?.cards.reduce((sum, c) => sum + c.quantity, 0) ?? 0;
  const sideboardCards =
    parseResult?.sideboard.reduce((sum, c) => sum + c.quantity, 0) ?? 0;
  const maybeboardCards =
    parseResult?.maybeboard?.reduce((sum, c) => sum + c.quantity, 0) ?? 0;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: "rgba(0, 0, 0, 0.8)" }}
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-lg p-6 rounded-xl max-h-[80vh] flex flex-col"
        style={{
          background: `linear-gradient(180deg, ${colors.void.deep} 0%, ${colors.void.deepest} 100%)`,
          border: `1px solid ${colors.border.standard}`,
          boxShadow: `0 25px 50px rgba(0,0,0,0.5)`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{
              background: `${colors.mana.blue.color}15`,
              border: `1px solid ${colors.mana.blue.color}30`,
            }}
          >
            <i
              className="ms ms-dfc-modal-face"
              style={{ color: colors.mana.blue.color, fontSize: 18 }}
            />
          </div>
          <h2
            className="font-display text-xl tracking-wider"
            style={{ color: colors.mana.blue.color }}
          >
            Import Deck
          </h2>
        </div>

        {/* Mode Tabs */}
        {!parseResult && (
          <div
            className="flex gap-1 mb-4 p-1 rounded-lg"
            style={{ background: colors.void.medium }}
          >
            <button
              onClick={() => setMode("url")}
              className="flex-1 py-2 px-4 text-sm font-display rounded-md transition-all"
              style={{
                background:
                  mode === "url" ? colors.mana.blue.color : "transparent",
                color: mode === "url" ? colors.void.deepest : colors.text.muted,
              }}
            >
              From URL
            </button>
            <button
              onClick={() => setMode("paste")}
              className="flex-1 py-2 px-4 text-sm font-display rounded-md transition-all"
              style={{
                background:
                  mode === "paste" ? colors.mana.blue.color : "transparent",
                color:
                  mode === "paste" ? colors.void.deepest : colors.text.muted,
              }}
            >
              Paste List
            </button>
          </div>
        )}

        {/* URL Input */}
        {!parseResult && mode === "url" && (
          <div className="mb-4">
            <label
              className="block text-xs font-display uppercase tracking-wider mb-2"
              style={{ color: colors.text.muted }}
            >
              Deck URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Paste deck URL from mtgdecks.net, tappedout.net, moxfield.com..."
                className="flex-1 h-11 px-4 text-sm rounded-lg"
                style={{
                  background: colors.void.medium,
                  border: `1px solid ${url ? colors.mana.blue.color : colors.border.standard}`,
                  color: colors.text.standard,
                  outline: "none",
                }}
                autoFocus
              />
              <button
                onClick={handleParse}
                disabled={!url.trim() || isParsing}
                className="px-4 h-11 rounded-lg transition-colors font-display text-sm tracking-wide"
                style={{
                  background:
                    url.trim() && !isParsing
                      ? colors.mana.blue.color
                      : colors.void.lighter,
                  color:
                    url.trim() && !isParsing
                      ? colors.void.deepest
                      : colors.text.muted,
                  cursor: url.trim() && !isParsing ? "pointer" : "not-allowed",
                }}
              >
                {isParsing ? "..." : "Fetch"}
              </button>
            </div>
            <p className="mt-2 text-xs" style={{ color: colors.text.dim }}>
              Supports: mtgdecks.net, tappedout.net, moxfield.com,
              archidekt.com, mtggoldfish.com
            </p>
          </div>
        )}

        {/* Paste Text Input */}
        {!parseResult && mode === "paste" && (
          <div className="mb-4">
            <label
              className="block text-xs font-display uppercase tracking-wider mb-2"
              style={{ color: colors.text.muted }}
            >
              Deck List
            </label>
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder={`Paste your deck list here...\n\nSupported formats:\n1 Card Name\n4 Lightning Bolt\n2 Aang and Katara (TLE) 69\n\nSideboard\n2 Negate`}
              className="w-full h-48 px-4 py-3 text-sm rounded-lg resize-none font-mono"
              style={{
                background: colors.void.medium,
                border: `1px solid ${pasteText ? colors.mana.blue.color : colors.border.standard}`,
                color: colors.text.standard,
                outline: "none",
              }}
              autoFocus
            />
            <div className="flex justify-between items-center mt-2">
              <p className="text-xs" style={{ color: colors.text.dim }}>
                Formats: "4 Card Name", "4x Card Name", "1 Card (SET) 123"
              </p>
              <button
                onClick={handleParse}
                disabled={!pasteText.trim() || isParsing}
                className="px-4 py-2 rounded-lg transition-colors font-display text-sm tracking-wide"
                style={{
                  background:
                    pasteText.trim() && !isParsing
                      ? colors.mana.blue.color
                      : colors.void.lighter,
                  color:
                    pasteText.trim() && !isParsing
                      ? colors.void.deepest
                      : colors.text.muted,
                  cursor:
                    pasteText.trim() && !isParsing ? "pointer" : "not-allowed",
                }}
              >
                {isParsing ? "Parsing..." : "Parse Deck"}
              </button>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            className="mb-4 p-3 rounded-lg text-sm"
            style={{
              background: `rgba(255, 68, 68, 0.1)`,
              border: `1px solid rgba(255, 68, 68, 0.3)`,
              color: "#ff4444",
            }}
          >
            {error}
          </div>
        )}

        {/* Parse Result Preview */}
        {parseResult && (
          <div className="flex-1 overflow-auto">
            {/* Deck Name Input */}
            <div className="mb-4">
              <label
                className="block text-xs font-display uppercase tracking-wider mb-2"
                style={{ color: colors.text.muted }}
              >
                Deck Name
              </label>
              <input
                type="text"
                value={deckName}
                onChange={(e) => setDeckName(e.target.value)}
                className="w-full h-11 px-4 text-sm rounded-lg"
                style={{
                  background: colors.void.medium,
                  border: `1px solid ${deckName ? colors.gold.dim : colors.border.standard}`,
                  color: colors.text.standard,
                  outline: "none",
                }}
              />
            </div>

            {/* Summary */}
            <div
              className="mb-4 p-4 rounded-lg"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div className="flex items-center gap-4 flex-wrap">
                {parseResult.format && (
                  <span
                    className="text-xs px-2 py-1 rounded"
                    style={{
                      background: `${getFormatColor(parseResult.format)}20`,
                      color: getFormatColor(parseResult.format),
                      border: `1px solid ${getFormatColor(parseResult.format)}40`,
                    }}
                  >
                    {parseResult.format.toUpperCase()}
                  </span>
                )}
                <span
                  className="text-sm"
                  style={{ color: colors.text.standard }}
                >
                  {totalCards} cards
                </span>
                {sideboardCards > 0 && (
                  <span
                    className="text-sm"
                    style={{ color: colors.text.muted }}
                  >
                    +{sideboardCards} sideboard
                  </span>
                )}
                {maybeboardCards > 0 && (
                  <span className="text-sm" style={{ color: colors.text.dim }}>
                    +{maybeboardCards} maybe
                  </span>
                )}
              </div>
              {parseResult.commander && (
                <div
                  className="mt-2 flex items-center gap-2"
                  style={{ color: colors.gold.standard }}
                >
                  <i className="ms ms-planeswalker" style={{ fontSize: 12 }} />
                  <span className="text-sm">{parseResult.commander}</span>
                </div>
              )}
            </div>

            {/* Card Preview */}
            <div
              className="max-h-48 overflow-auto rounded-lg p-3"
              style={{
                background: colors.void.medium,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {parseResult.cards.slice(0, 20).map((card, i) => (
                  <div
                    key={i}
                    className="text-xs truncate"
                    style={{ color: colors.text.dim }}
                  >
                    {card.quantity}x {card.name}
                  </div>
                ))}
                {parseResult.cards.length > 20 && (
                  <div
                    className="text-xs col-span-2 mt-2"
                    style={{ color: colors.text.muted }}
                  >
                    ... and {parseResult.cards.length - 20} more cards
                  </div>
                )}
              </div>
            </div>

            {/* Warnings */}
            {parseResult.errors.length > 0 && (
              <div
                className="mt-3 p-3 rounded-lg text-xs"
                style={{
                  background: `rgba(255, 180, 0, 0.1)`,
                  border: `1px solid rgba(255, 180, 0, 0.3)`,
                  color: "#ffb400",
                }}
              >
                {parseResult.errors.map((err, i) => (
                  <div key={i}>{err}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Buttons */}
        <div
          className="flex justify-end gap-3 mt-6 pt-4 border-t"
          style={{ borderColor: colors.border.subtle }}
        >
          <button
            type="button"
            onClick={handleClose}
            className="px-5 py-2.5 text-sm font-display tracking-wide rounded-lg transition-colors"
            style={{
              background: colors.void.lighter,
              color: colors.text.dim,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            Cancel
          </button>
          {parseResult && (
            <button
              onClick={handleImport}
              disabled={!deckName.trim() || isImporting}
              className="px-5 py-2.5 text-sm font-display tracking-wide rounded-lg transition-colors"
              style={{
                background:
                  deckName.trim() && !isImporting
                    ? colors.gold.standard
                    : colors.void.lighter,
                color:
                  deckName.trim() && !isImporting
                    ? colors.void.deepest
                    : colors.text.muted,
                cursor:
                  deckName.trim() && !isImporting ? "pointer" : "not-allowed",
              }}
            >
              {isImporting ? "Importing..." : "Import Deck"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface DecksScreenProps {
  onSelectDeck?: (deckId: number) => void;
}

export function DecksScreen({ onSelectDeck }: DecksScreenProps): ReactNode {
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const fetchDecks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await window.electronAPI.decks.list();
      setDecks(result);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDecks();
  }, [fetchDecks]);

  const handleCreateDeck = async (
    formData: CreateDeckFormData,
  ): Promise<void> => {
    setIsCreating(true);
    try {
      await window.electronAPI.decks.create({
        name: formData.name,
        format: formData.format || null,
        commander: formData.commander || null,
        description: formData.description || null,
      });
      setShowCreateModal(false);
      await fetchDecks();
    } catch (err) {
      setError(String(err));
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteDeck = async (deck: DeckSummary): Promise<void> => {
    try {
      await window.electronAPI.decks.delete(deck.id);
      await fetchDecks();
    } catch (err) {
      setError(String(err));
    }
  };

  const handleSelectDeck = (deck: DeckSummary): void => {
    onSelectDeck?.(deck.id);
  };

  const handleImportDeck = async (deckId: number): Promise<void> => {
    await fetchDecks();
    onSelectDeck?.(deckId);
  };

  // Filter decks
  const filteredDecks = decks.filter(
    (deck) =>
      deck.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (deck.commander?.toLowerCase().includes(searchFilter.toLowerCase()) ??
        false) ||
      (deck.format?.toLowerCase().includes(searchFilter.toLowerCase()) ??
        false),
  );

  // Group by format
  const decksByFormat = filteredDecks.reduce<Record<string, DeckSummary[]>>(
    (acc, deck) => {
      const format = deck.format || "No Format";
      if (!acc[format]) acc[format] = [];
      acc[format].push(deck);
      return acc;
    },
    {},
  );

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 120% 80% at 0% 0%, rgba(255, 107, 53, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse 100% 60% at 100% 100%, rgba(255, 215, 0, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse 80% 50% at 50% 50%, rgba(74, 158, 255, 0.04) 0%, transparent 60%),
      ${colors.void.deepest}
    `,
  };

  if (isLoading) {
    return (
      <div
        className="h-full flex items-center justify-center relative"
        style={containerStyle}
      >
        <ConstellationBackground />
        <div className="text-center relative z-10">
          <div
            className="w-10 h-10 mx-auto mb-4 rounded-full border-2 border-t-transparent"
            style={{
              borderColor: colors.gold.dim,
              borderTopColor: "transparent",
              animation: "spin 1s linear infinite",
            }}
          />
          <p
            className="font-display tracking-wider text-sm"
            style={{ color: colors.text.muted }}
          >
            Loading decks...
          </p>
        </div>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative" style={containerStyle}>
      <ConstellationBackground />

      {/* Header */}
      <div
        className="relative z-10 p-8 border-b"
        style={{ borderColor: `${colors.border.subtle}80` }}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, rgba(255, 107, 53, 0.2) 0%, rgba(255, 215, 0, 0.2) 100%)`,
                  border: `1px solid rgba(255, 215, 0, 0.3)`,
                  boxShadow: `0 0 20px rgba(255, 107, 53, 0.2)`,
                }}
              >
                <i
                  className="ms ms-saga"
                  style={{ color: "#ff6b35", fontSize: 20 }}
                />
              </div>
              <h1
                className="font-display text-3xl tracking-widest"
                style={{
                  background: `linear-gradient(135deg, #ff6b35 0%, #ffd700 50%, #4a9eff 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  textShadow: `0 0 40px rgba(255, 107, 53, 0.3)`,
                }}
              >
                GRIMOIRE
              </h1>
            </div>
            <p
              className="text-sm font-body ml-14"
              style={{ color: colors.text.dim }}
            >
              {decks.length} deck{decks.length !== 1 ? "s" : ""} in your arcane
              library
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2.5 font-display text-sm tracking-wide rounded-lg transition-all duration-200 flex items-center gap-2"
              style={{
                background: colors.void.lighter,
                color: colors.mana.blue.color,
                border: `1px solid ${colors.mana.blue.color}50`,
                fontWeight: 500,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = colors.mana.blue.color;
                e.currentTarget.style.background = `${colors.mana.blue.color}15`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = `${colors.mana.blue.color}50`;
                e.currentTarget.style.background = colors.void.lighter;
              }}
            >
              <i className="ms ms-dfc-modal-face" style={{ fontSize: 14 }} />
              Import
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-5 py-2.5 font-display text-sm tracking-wide rounded-lg transition-all duration-200 flex items-center gap-2"
              style={{
                background: "linear-gradient(135deg, #ffd700 0%, #ff6b35 100%)",
                color: colors.void.deepest,
                boxShadow: `0 0 15px rgba(255, 215, 0, 0.3)`,
                fontWeight: 600,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = `0 0 20px rgba(255, 215, 0, 0.4)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = `0 0 15px rgba(255, 215, 0, 0.3)`;
              }}
            >
              + New Deck
            </button>
          </div>
        </div>

        {error && (
          <div
            className="mb-5 p-4 rounded-xl text-sm flex items-center gap-3"
            style={{
              background: `linear-gradient(135deg, rgba(255, 68, 68, 0.15) 0%, rgba(255, 68, 68, 0.05) 100%)`,
              border: `1px solid rgba(255, 68, 68, 0.3)`,
              color: "#ff4444",
            }}
          >
            <i className="ms ms-ability-menace" />
            {error}
          </div>
        )}

        <div className="w-96">
          <SearchBar
            value={searchFilter}
            onChange={setSearchFilter}
            placeholder="Search your grimoire..."
          />
        </div>
      </div>

      {/* Deck list */}
      <div className="relative z-10 flex-1 overflow-auto p-8">
        {filteredDecks.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <i
                className="ms ms-saga"
                style={{
                  fontSize: 64,
                  color: colors.gold.dim,
                  opacity: 0.2,
                }}
              />
              <p
                className="mt-6 font-display text-lg tracking-wide"
                style={{ color: colors.text.muted }}
              >
                {searchFilter
                  ? "No decks match your search"
                  : "Your library is empty"}
              </p>
              {!searchFilter && (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-6 px-5 py-2.5 font-display text-sm tracking-wide rounded-lg transition-all duration-200"
                  style={{
                    background:
                      "linear-gradient(135deg, #ffd700 0%, #ff6b35 100%)",
                    color: colors.void.deepest,
                    boxShadow: `0 0 15px rgba(255, 215, 0, 0.3)`,
                  }}
                >
                  Create Your First Deck
                </button>
              )}
            </div>
          </div>
        ) : (
          Object.entries(decksByFormat)
            .sort(([a], [b]) => {
              if (a === "No Format") return 1;
              if (b === "No Format") return -1;
              return a.localeCompare(b);
            })
            .map(([format, formatDecks]) => {
              const formatColor = getFormatColor(
                format === "No Format" ? null : format,
              );
              const formatIcon = getFormatIcon(
                format === "No Format" ? null : format,
              );

              return (
                <div key={format} className="mb-10">
                  {/* Section header with format styling */}
                  <div className="flex items-center gap-4 mb-6">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{
                        background: `${formatColor}20`,
                        border: `1px solid ${formatColor}40`,
                      }}
                    >
                      <i
                        className={formatIcon}
                        style={{ fontSize: 14, color: formatColor }}
                      />
                    </div>
                    <span
                      className="text-sm font-display uppercase tracking-[0.2em]"
                      style={{ color: formatColor }}
                    >
                      {format}
                    </span>
                    <span
                      className="text-xs px-2.5 py-1 rounded-full font-display"
                      style={{
                        background: `${formatColor}15`,
                        color: formatColor,
                        border: `1px solid ${formatColor}30`,
                      }}
                    >
                      {formatDecks.length}
                    </span>
                    <span
                      className="flex-1 h-px"
                      style={{
                        background: `linear-gradient(to right, ${formatColor}40, transparent)`,
                      }}
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {formatDecks.map((deck) => (
                      <DeckCard
                        key={deck.id}
                        deck={deck}
                        onSelect={handleSelectDeck}
                        onDelete={handleDeleteDeck}
                      />
                    ))}
                  </div>
                </div>
              );
            })
        )}
      </div>

      {/* Create Deck Modal */}
      <CreateDeckModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateDeck}
        isCreating={isCreating}
      />

      {/* Import Deck Modal */}
      <ImportDeckModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImport={handleImportDeck}
      />

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
      `}</style>
    </div>
  );
}

export default DecksScreen;
