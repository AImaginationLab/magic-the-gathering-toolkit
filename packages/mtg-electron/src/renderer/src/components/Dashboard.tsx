/**
 * Dashboard - Arcane Library v2
 *
 * A mystical command center for planeswalkers. Dark, layered,
 * with floating magical elements and premium card aesthetics.
 *
 * v2: Enhanced with constellation connections, mana pulse rings,
 * card carousel, and dynamic time-of-day theming.
 */
import { useState, useEffect, useMemo, useCallback, useRef } from "react";

import { colors } from "../theme";

import type { ReactNode, CSSProperties } from "react";
import type { Screen } from "./Sidebar";

type TimeOfDay = "dawn" | "day" | "dusk" | "night";

function getTimeOfDay(): TimeOfDay {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 8) return "dawn";
  if (hour >= 8 && hour < 17) return "day";
  if (hour >= 17 && hour < 20) return "dusk";
  return "night";
}

const TIME_THEMES: Record<
  TimeOfDay,
  { accent: string; glow: string; greeting: string }
> = {
  dawn: {
    accent: "#ffb347",
    glow: "rgba(255, 179, 71, 0.3)",
    greeting: "The dawn breaks, Planeswalker",
  },
  day: {
    accent: colors.gold.standard,
    glow: colors.gold.glow,
    greeting: "Welcome back, Planeswalker",
  },
  dusk: {
    accent: "#c77dff",
    glow: "rgba(199, 125, 255, 0.3)",
    greeting: "The veil thins at dusk",
  },
  night: {
    accent: "#7eb8da",
    glow: "rgba(126, 184, 218, 0.3)",
    greeting: "The night holds secrets",
  },
};

function ArcaneParticles(): ReactNode {
  const particles = useMemo(() => {
    return Array.from({ length: 32 }, (_, i) => {
      const size = 1 + Math.random() * 4;
      const colorIndex = Math.random();
      let color: string;
      if (colorIndex < 0.3) color = colors.gold.dim;
      else if (colorIndex < 0.5) color = "rgba(126, 184, 218, 0.7)";
      else if (colorIndex < 0.7) color = "rgba(199, 125, 255, 0.6)";
      else color = "rgba(255, 179, 71, 0.5)";

      return {
        id: i,
        left: `${Math.random() * 100}%`,
        size,
        delay: `${Math.random() * 30}s`,
        duration: `${18 + Math.random() * 20}s`,
        opacity: 0.15 + Math.random() * 0.35,
        color,
        blur: size > 2.5 ? "blur(1px)" : "none",
      };
    });
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: p.left,
            width: p.size,
            height: p.size,
            background: p.color,
            opacity: p.opacity,
            filter: p.blur,
            animation: `float-up ${p.duration} linear infinite`,
            animationDelay: p.delay,
          }}
        />
      ))}
    </div>
  );
}

function ConstellationLines(): ReactNode {
  // SVG constellation connecting random points
  const lines = useMemo(() => {
    const points = Array.from({ length: 12 }, () => ({
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

    // Connect nearby points
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = Math.hypot(
          points[i].x - points[j].x,
          points[i].y - points[j].y,
        );
        if (dist < 35 && connections.length < 15) {
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
        <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={colors.gold.dim} />
          <stop offset="100%" stopColor={colors.mana.blue.color} />
        </linearGradient>
      </defs>

      {/* Connection lines */}
      {lines.connections.map((line, i) => (
        <line
          key={`line-${i}`}
          x1={`${line.x1}%`}
          y1={`${line.y1}%`}
          x2={`${line.x2}%`}
          y2={`${line.y2}%`}
          stroke="url(#lineGrad)"
          strokeWidth="0.5"
          style={{
            animation: `constellation-pulse 4s ease-in-out infinite`,
            animationDelay: `${line.delay}s`,
          }}
        />
      ))}

      {/* Star points */}
      {lines.points.map((point, i) => (
        <circle
          key={`point-${i}`}
          cx={`${point.x}%`}
          cy={`${point.y}%`}
          r="1.5"
          fill={colors.gold.dim}
          style={{
            animation: `star-twinkle 3s ease-in-out infinite`,
            animationDelay: `${i * 0.3}s`,
          }}
        />
      ))}
    </svg>
  );
}

function MagicCircle(): ReactNode {
  return (
    <div
      className="absolute pointer-events-none"
      style={{
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        width: "140%",
        height: "140%",
        opacity: 0.04,
      }}
    >
      <svg viewBox="0 0 400 400" className="w-full h-full">
        <defs>
          <linearGradient id="circleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={colors.gold.standard} />
            <stop offset="100%" stopColor={colors.gold.dim} />
          </linearGradient>
        </defs>
        <circle
          cx="200"
          cy="200"
          r="195"
          fill="none"
          stroke="url(#circleGrad)"
          strokeWidth="0.5"
          style={{ animation: "spin 120s linear infinite" }}
        />
        <circle
          cx="200"
          cy="200"
          r="150"
          fill="none"
          stroke="url(#circleGrad)"
          strokeWidth="0.3"
          style={{ animation: "spin 90s linear infinite reverse" }}
        />
        <polygon
          points="200,50 235,140 325,140 255,190 275,280 200,230 125,280 145,190 75,140 165,140"
          fill="none"
          stroke="url(#circleGrad)"
          strokeWidth="0.3"
          style={{ animation: "spin 180s linear infinite" }}
        />
      </svg>
    </div>
  );
}

function ManaIcon({
  symbol,
  className = "",
}: {
  symbol: string;
  className?: string;
}): ReactNode {
  return <i className={`ms ms-${symbol} ms-cost ${className}`} />;
}

// Animated mana wheel that slowly rotates
function ManaWheel(): ReactNode {
  const symbols = ["w", "u", "b", "r", "g"];
  const manaColors = [
    colors.mana.white.color,
    colors.mana.blue.color,
    colors.mana.black.color,
    colors.mana.red.color,
    colors.mana.green.color,
  ];

  return (
    <div
      className="relative w-24 h-24"
      style={{ animation: "spin 60s linear infinite" }}
    >
      {symbols.map((symbol, i) => {
        const angle = (i * 72 - 90) * (Math.PI / 180);
        const x = 50 + 40 * Math.cos(angle);
        const y = 50 + 40 * Math.sin(angle);

        return (
          <div
            key={symbol}
            className="absolute text-lg transition-all duration-300"
            style={{
              left: `${x}%`,
              top: `${y}%`,
              transform: "translate(-50%, -50%)",
              color: manaColors[i],
              animation: `spin 60s linear infinite reverse`,
              textShadow: `0 0 10px ${manaColors[i]}`,
            }}
          >
            <ManaIcon symbol={symbol} />
          </div>
        );
      })}
    </div>
  );
}

interface CardData {
  name: string;
  imageUrl: string | null;
  setCode?: string;
}

interface CardCarouselProps {
  cards: CardData[];
  onRefresh: () => void;
  isLoading: boolean;
}

function CardCarousel({
  cards,
  onRefresh,
  isLoading,
}: CardCarouselProps): ReactNode {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  const cardRef = useRef<HTMLDivElement>(null);

  // Auto-rotate cards
  useEffect(() => {
    if (isHovered || cards.length <= 1) return;

    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % cards.length);
    }, 5000);

    return () => clearInterval(timer);
  }, [cards.length, isHovered]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>): void => {
      if (!cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      setMousePos({ x, y });
    },
    [],
  );

  const activeCard = cards[activeIndex];
  const rotateX = isHovered ? (mousePos.y - 0.5) * -15 : 0;
  const rotateY = isHovered ? (mousePos.x - 0.5) * 15 : 0;

  return (
    <div className="flex flex-col items-center">
      {/* Main card display */}
      <div
        ref={cardRef}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => {
          setIsHovered(false);
          setMousePos({ x: 0.5, y: 0.5 });
        }}
        onMouseMove={handleMouseMove}
        className="relative cursor-pointer mb-4"
        style={{
          width: 240,
          perspective: "1000px",
        }}
      >
        {/* Card stack effect - background cards */}
        {cards.length > 1 && (
          <>
            <div
              className="absolute rounded-xl"
              style={{
                width: "100%",
                aspectRatio: "488 / 680",
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
                transform: "translateX(12px) translateY(8px) rotate(3deg)",
                opacity: 0.4,
              }}
            />
            <div
              className="absolute rounded-xl"
              style={{
                width: "100%",
                aspectRatio: "488 / 680",
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
                transform: "translateX(6px) translateY(4px) rotate(1.5deg)",
                opacity: 0.6,
              }}
            />
          </>
        )}

        {/* Active card */}
        <div
          className="relative transition-transform duration-200 ease-out"
          style={{
            transform: `rotateX(${rotateX}deg) rotateY(${rotateY}deg) ${isHovered ? "scale(1.03)" : "scale(1)"}`,
            transformStyle: "preserve-3d",
          }}
        >
          {/* Glow */}
          <div
            className="absolute -inset-6 rounded-2xl transition-opacity duration-300"
            style={{
              background: `radial-gradient(ellipse at ${mousePos.x * 100}% ${mousePos.y * 100}%, ${colors.gold.glow} 0%, transparent 60%)`,
              opacity: isHovered ? 0.9 : 0.3,
              filter: "blur(25px)",
            }}
          />

          {/* Card */}
          <div
            className="relative overflow-hidden rounded-xl"
            style={{
              aspectRatio: "488 / 680",
              background: colors.void.medium,
              boxShadow: isHovered
                ? `0 25px 80px rgba(0,0,0,0.6), 0 0 50px ${colors.gold.glow}`
                : "0 15px 50px rgba(0,0,0,0.5)",
            }}
          >
            {isLoading ? (
              <div className="w-full h-full flex items-center justify-center">
                <div
                  className="w-8 h-8 rounded-full border-2 border-t-transparent"
                  style={{
                    borderColor: colors.gold.dim,
                    borderTopColor: "transparent",
                    animation: "spin 1s linear infinite",
                  }}
                />
              </div>
            ) : activeCard?.imageUrl ? (
              <img
                src={activeCard.imageUrl}
                alt={activeCard.name}
                loading="lazy"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <ManaIcon symbol="c" className="text-5xl opacity-20" />
              </div>
            )}

            {/* Holographic shine */}
            <div
              className="absolute inset-0 pointer-events-none transition-opacity duration-300"
              style={{
                background: `linear-gradient(${105 + (mousePos.x - 0.5) * 40}deg,
                  transparent 20%,
                  rgba(255,255,255,0.08) 40%,
                  rgba(255,255,255,0.15) 50%,
                  rgba(255,255,255,0.08) 60%,
                  transparent 80%)`,
                opacity: isHovered ? 1 : 0,
              }}
            />

            {/* Rainbow edge effect on hover */}
            <div
              className="absolute inset-0 rounded-xl pointer-events-none transition-opacity duration-300"
              style={{
                background: `linear-gradient(${mousePos.x * 360}deg,
                  rgba(255,179,71,0.3),
                  rgba(199,125,255,0.3),
                  rgba(126,184,218,0.3),
                  rgba(155,211,174,0.3))`,
                opacity: isHovered ? 0.15 : 0,
                mixBlendMode: "overlay",
              }}
            />
          </div>

          {/* Card name */}
          <div
            className="mt-3 text-center transition-all duration-300"
            style={{ transform: "translateZ(20px)" }}
          >
            <p
              className="font-display text-sm tracking-wide truncate"
              style={{
                color: isHovered ? colors.text.bright : colors.text.standard,
              }}
            >
              {activeCard?.name || "Loading..."}
            </p>
            {activeCard?.setCode && (
              <p
                className="text-xs mt-0.5 font-mono uppercase"
                style={{ color: colors.text.muted }}
              >
                {activeCard.setCode}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Card indicators */}
      {cards.length > 1 && (
        <div className="flex items-center gap-2 mb-4">
          {cards.map((_, i) => (
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className="transition-all duration-300"
              style={{
                width: i === activeIndex ? 20 : 6,
                height: 6,
                borderRadius: 3,
                background:
                  i === activeIndex
                    ? colors.gold.standard
                    : colors.void.lighter,
                boxShadow:
                  i === activeIndex ? `0 0 10px ${colors.gold.glow}` : "none",
              }}
            />
          ))}
        </div>
      )}

      {/* Refresh button */}
      <button
        onClick={onRefresh}
        disabled={isLoading}
        className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300 group"
        style={{
          background: colors.void.light,
          border: `1px solid ${colors.border.standard}`,
          opacity: isLoading ? 0.5 : 1,
        }}
        onMouseEnter={(e) => {
          if (!isLoading) {
            e.currentTarget.style.borderColor = colors.rarity.mythic.color;
            e.currentTarget.style.boxShadow = `0 0 20px ${colors.rarity.mythic.glow}`;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = colors.border.standard;
          e.currentTarget.style.boxShadow = "none";
        }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{
            color: colors.text.muted,
            animation: isLoading ? "spin 1s linear infinite" : "none",
          }}
        >
          <path d="M21 12a9 9 0 11-9-9" />
          <path d="M21 3v9h-9" />
        </svg>
        <span className="text-xs font-body" style={{ color: colors.text.dim }}>
          {isLoading ? "Loading..." : "Discover cards"}
        </span>
      </button>
    </div>
  );
}

interface StatsOrbProps {
  value: string | number;
  label: string;
  icon: ReactNode;
  accentColor?: string;
  onClick?: () => void;
}

function StatsOrb({
  value,
  label,
  icon,
  accentColor = colors.gold.standard,
  onClick,
}: StatsOrbProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative flex flex-col items-center group transition-transform duration-300"
      style={{
        transform: isHovered ? "translateY(-4px) scale(1.05)" : "none",
      }}
    >
      {/* Pulse ring on hover */}
      <div
        className="absolute rounded-full transition-all duration-500"
        style={{
          width: isHovered ? 72 : 56,
          height: isHovered ? 72 : 56,
          top: isHovered ? -8 : 0,
          left: "50%",
          transform: "translateX(-50%)",
          border: `1px solid ${accentColor}`,
          opacity: isHovered ? 0.3 : 0,
        }}
      />

      {/* Orb */}
      <div
        className="relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300"
        style={{
          background: `radial-gradient(circle at 30% 30%, ${colors.void.light} 0%, ${colors.void.deep} 100%)`,
          border: `1px solid ${isHovered ? accentColor : colors.border.standard}`,
          boxShadow: isHovered
            ? `0 0 30px ${accentColor}50, inset 0 0 25px ${accentColor}15`
            : `0 4px 20px rgba(0,0,0,0.3)`,
        }}
      >
        <div
          className="text-xl transition-all duration-300"
          style={{
            color: isHovered ? accentColor : colors.text.dim,
            filter: isHovered ? `drop-shadow(0 0 12px ${accentColor})` : "none",
            transform: isHovered ? "scale(1.1)" : "scale(1)",
          }}
        >
          {icon}
        </div>
      </div>

      {/* Value */}
      <p
        className="font-display text-base mt-2 tracking-wide transition-all duration-300"
        style={{
          color: isHovered ? colors.text.bright : colors.text.standard,
          textShadow: isHovered ? `0 0 20px ${accentColor}` : "none",
        }}
      >
        {typeof value === "number" ? value.toLocaleString() : value}
      </p>

      {/* Label */}
      <p
        className="text-xs font-body tracking-wider uppercase"
        style={{ color: colors.text.muted }}
      >
        {label}
      </p>
    </button>
  );
}

interface SigilProps {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  accentColor?: string;
  onClick: () => void;
}

function Sigil({
  icon,
  title,
  subtitle,
  accentColor = colors.gold.standard,
  onClick,
}: SigilProps): ReactNode {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="relative flex items-center gap-4 px-4 py-3 text-left transition-all duration-300 group w-full"
      style={{
        background: isHovered
          ? `linear-gradient(135deg, ${colors.void.light} 0%, ${colors.void.medium} 100%)`
          : "transparent",
        borderRadius: 12,
        border: `1px solid ${isHovered ? accentColor + "50" : "transparent"}`,
        transform: isHovered ? "translateX(8px)" : "none",
      }}
    >
      {/* Accent line */}
      <div
        className="absolute left-0 top-1/2 -translate-y-1/2 w-1 transition-all duration-300"
        style={{
          height: isHovered ? "70%" : "0%",
          background: `linear-gradient(180deg, ${accentColor}, ${accentColor}00)`,
          borderRadius: 2,
          boxShadow: isHovered ? `0 0 15px ${accentColor}` : "none",
        }}
      />

      {/* Icon container */}
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-300"
        style={{
          background: isHovered ? `${accentColor}20` : `${accentColor}10`,
          border: `1px solid ${isHovered ? accentColor + "50" : accentColor + "20"}`,
          transform: isHovered ? "rotate(-5deg) scale(1.1)" : "none",
        }}
      >
        <div
          className="text-lg transition-all duration-300"
          style={{
            color: isHovered ? accentColor : colors.text.dim,
            filter: isHovered ? `drop-shadow(0 0 8px ${accentColor})` : "none",
          }}
        >
          {icon}
        </div>
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p
          className="font-display text-base tracking-wide transition-colors duration-300"
          style={{
            color: isHovered ? colors.text.bright : colors.text.standard,
          }}
        >
          {title}
        </p>
        {subtitle && (
          <p
            className="text-sm font-body truncate transition-colors duration-300"
            style={{ color: isHovered ? colors.text.dim : colors.text.muted }}
          >
            {subtitle}
          </p>
        )}
      </div>

      {/* Arrow */}
      <div
        className="transition-all duration-300"
        style={{
          color: isHovered ? accentColor : "transparent",
          transform: isHovered ? "translateX(4px)" : "none",
          fontSize: 18,
        }}
      >
        →
      </div>
    </button>
  );
}

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  accentColor: string;
}

function SearchBar({
  value,
  onChange,
  onSubmit,
  accentColor,
}: SearchBarProps): ReactNode {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="relative">
      {/* Animated border gradient */}
      <div
        className="absolute -inset-[1px] rounded-2xl transition-opacity duration-500"
        style={{
          background: `linear-gradient(90deg, ${accentColor}, ${colors.mana.blue.color}, ${colors.mana.red.color}, ${accentColor})`,
          backgroundSize: "300% 100%",
          animation: isFocused ? "gradient-shift 3s linear infinite" : "none",
          opacity: isFocused ? 0.8 : 0,
        }}
      />

      {/* Glow */}
      <div
        className="absolute -inset-2 rounded-2xl transition-opacity duration-300"
        style={{
          background: `radial-gradient(ellipse at center, ${accentColor}40 0%, transparent 70%)`,
          opacity: isFocused ? 1 : 0,
          filter: "blur(15px)",
        }}
      />

      {/* Input container */}
      <div
        className="relative flex items-center transition-all duration-300"
        style={{
          background: colors.void.deep,
          border: `1px solid ${isFocused ? "transparent" : colors.border.standard}`,
          borderRadius: 16,
          boxShadow: isFocused
            ? `0 0 40px ${accentColor}30, inset 0 1px 0 ${colors.border.subtle}`
            : `0 4px 20px rgba(0,0,0,0.3), inset 0 1px 0 ${colors.border.subtle}`,
        }}
      >
        {/* Search icon */}
        <div
          className="pl-6 pr-4 transition-colors duration-300"
          style={{ color: isFocused ? accentColor : colors.text.muted }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>

        {/* Input */}
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSubmit()}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Search the multiverse..."
          className="flex-1 h-12 bg-transparent font-body text-base outline-none"
          style={{ color: colors.text.standard }}
        />

        {/* Keyboard hint */}
        <div
          className="pr-6 flex items-center gap-2 transition-opacity duration-300"
          style={{ opacity: isFocused ? 0 : 0.4 }}
        >
          <kbd
            className="px-2.5 py-1 rounded-lg text-xs font-mono"
            style={{
              background: colors.void.lighter,
              color: colors.text.muted,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            /
          </kbd>
        </div>
      </div>
    </div>
  );
}

interface DashboardProps {
  onNavigate: (screen: Screen) => void;
  onSearch: (query: string) => void;
  cardCount: number;
  setCount: number;
}

export function Dashboard({
  onNavigate,
  onSearch,
  cardCount,
  setCount,
}: DashboardProps): ReactNode {
  const [searchQuery, setSearchQuery] = useState("");
  const [collectionStats, setCollectionStats] = useState({
    total: 0,
    unique: 0,
  });
  const [featuredCards, setFeaturedCards] = useState<CardData[]>([]);
  const [isLoadingCards, setIsLoadingCards] = useState(true);
  const [timeTheme, setTimeTheme] = useState(() => TIME_THEMES[getTimeOfDay()]);

  // Update time theme periodically
  useEffect(() => {
    const updateTheme = (): void => {
      setTimeTheme(TIME_THEMES[getTimeOfDay()]);
    };

    const timer = setInterval(updateTheme, 60000); // Check every minute
    return () => clearInterval(timer);
  }, []);

  const loadRandomCards = useCallback(async (): Promise<void> => {
    setIsLoadingCards(true);
    try {
      const results = await Promise.all([
        window.electronAPI.api.cards.random(),
        window.electronAPI.api.cards.random(),
        window.electronAPI.api.cards.random(),
      ]);

      const cards: CardData[] = results
        .filter((result) => result.cards && result.cards.length > 0)
        .map((result) => {
          const card = result.cards![0];
          return {
            name: card.name,
            imageUrl: card.image || card.image_small || null,
            setCode: card.set_code || undefined,
          };
        });

      setFeaturedCards(cards);
    } catch (err) {
      console.error("Failed to load random cards:", err);
    } finally {
      setIsLoadingCards(false);
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    let mounted = true;

    window.electronAPI.collection
      .stats()
      .then((stats) => {
        if (mounted && !stats.error) {
          setCollectionStats({
            total: stats.total,
            unique: stats.unique,
          });
        }
      })
      .catch((err) => {
        if (mounted) {
          console.error("Failed to load collection stats:", err);
        }
      });

    const loadInitialCards = async (): Promise<void> => {
      setIsLoadingCards(true);
      try {
        const results = await Promise.all([
          window.electronAPI.api.cards.random(),
          window.electronAPI.api.cards.random(),
          window.electronAPI.api.cards.random(),
        ]);

        if (!mounted) return;

        const cards: CardData[] = results
          .filter((result) => result.cards && result.cards.length > 0)
          .map((result) => {
            const card = result.cards![0];
            return {
              name: card.name,
              imageUrl: card.image || card.image_small || null,
              setCode: card.set_code || undefined,
            };
          });

        setFeaturedCards(cards);
      } catch (err) {
        if (mounted) {
          console.error("Failed to load random cards:", err);
        }
      } finally {
        if (mounted) {
          setIsLoadingCards(false);
        }
      }
    };

    loadInitialCards();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSearch = (): void => {
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const containerStyle: CSSProperties = {
    background: `
      radial-gradient(ellipse 120% 80% at 10% 10%, ${timeTheme.glow} 0%, transparent 40%),
      radial-gradient(ellipse 100% 60% at 90% 90%, rgba(100, 120, 180, 0.05) 0%, transparent 40%),
      radial-gradient(ellipse 80% 80% at 50% 50%, ${colors.void.light}20 0%, transparent 50%),
      ${colors.void.deepest}
    `,
  };

  return (
    <div className="relative min-h-full overflow-hidden" style={containerStyle}>
      {/* Background effects */}
      <MagicCircle />
      <ConstellationLines />
      <ArcaneParticles />

      {/* Main content */}
      <div className="relative z-10 p-6 lg:p-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          {/* Title section */}
          <div className="flex items-start gap-6">
            {/* Mana wheel */}
            <div className="hidden lg:block">
              <ManaWheel />
            </div>

            <div>
              {/* Greeting based on time */}
              <p
                className="text-xs font-body tracking-widest uppercase mb-2"
                style={{ color: timeTheme.accent, opacity: 0.8 }}
              >
                {timeTheme.greeting}
              </p>

              <h1
                className="font-display text-4xl lg:text-5xl tracking-widest mb-2"
                style={{
                  background: `linear-gradient(135deg, ${timeTheme.accent} 0%, ${colors.gold.bright} 50%, ${timeTheme.accent} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                SPELLBOOK
              </h1>

              <p
                className="font-body text-sm"
                style={{ color: colors.text.dim }}
              >
                Your arcane library • {cardCount.toLocaleString()} cards indexed
              </p>
            </div>
          </div>
        </div>

        {/* Main layout */}
        <div className="flex gap-10 lg:gap-12">
          {/* Left column */}
          <div className="flex-1 max-w-xl">
            {/* Search */}
            <div className="mb-6">
              <SearchBar
                value={searchQuery}
                onChange={setSearchQuery}
                onSubmit={handleSearch}
                accentColor={timeTheme.accent}
              />
            </div>

            {/* Stats */}
            <div className="flex items-center justify-center gap-8 mb-8">
              <StatsOrb
                value={cardCount}
                label="Cards"
                icon={<ManaIcon symbol="c" />}
                accentColor={timeTheme.accent}
                onClick={() => onNavigate("search")}
              />
              <StatsOrb
                value={setCount}
                label="Sets"
                icon={
                  <i className="ss ss-dom" style={{ fontSize: "1.25rem" }} />
                }
                accentColor={colors.mana.blue.color}
                onClick={() => onNavigate("sets")}
              />
              <StatsOrb
                value={collectionStats.unique}
                label="Owned"
                icon={<ManaIcon symbol="g" />}
                accentColor={colors.mana.green.color}
                onClick={() => onNavigate("collection")}
              />
            </div>

            {/* Quick actions */}
            <div>
              <p
                className="text-xs font-display uppercase tracking-widest mb-2 flex items-center gap-3"
                style={{ color: colors.text.muted }}
              >
                <span
                  className="w-6 h-px"
                  style={{ background: colors.border.standard }}
                />
                Quick Actions
                <span
                  className="flex-1 h-px"
                  style={{ background: colors.border.standard }}
                />
              </p>

              <div className="space-y-1">
                <Sigil
                  icon={<ManaIcon symbol="r" />}
                  title="Build a Deck"
                  subtitle="Create and manage your decks"
                  accentColor={colors.mana.red.color}
                  onClick={() => onNavigate("decks")}
                />
                <Sigil
                  icon={<ManaIcon symbol="u" />}
                  title="Find Synergies"
                  subtitle="Discover powerful combinations"
                  accentColor={colors.mana.blue.color}
                  onClick={() => onNavigate("synergies")}
                />
                <Sigil
                  icon={<ManaIcon symbol="w" />}
                  title="Browse Artists"
                  subtitle="Explore card illustrations"
                  accentColor={colors.mana.white.color}
                  onClick={() => onNavigate("artists")}
                />
                <Sigil
                  icon={<i className="ms ms-ability-constellation" />}
                  title="Deck Suggestions"
                  subtitle="AI-powered recommendations"
                  accentColor={colors.rarity.mythic.color}
                  onClick={() => onNavigate("suggestions")}
                />
              </div>
            </div>
          </div>

          {/* Right column - Card Carousel */}
          <div className="hidden lg:flex flex-col items-center justify-start">
            <p
              className="text-xs font-display uppercase tracking-widest mb-4 flex items-center gap-3"
              style={{ color: colors.text.muted }}
            >
              <span
                className="w-6 h-px"
                style={{ background: colors.border.standard }}
              />
              Discover
              <span
                className="w-6 h-px"
                style={{ background: colors.border.standard }}
              />
            </p>

            <CardCarousel
              cards={featuredCards}
              onRefresh={loadRandomCards}
              isLoading={isLoadingCards}
            />
          </div>
        </div>

        {/* Bottom tagline - positioned just above footer */}
        <div
          className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-4 text-xs font-display tracking-widest"
          style={{ color: timeTheme.accent, opacity: 0.25 }}
        >
          <span
            className="w-12 h-px"
            style={{ background: timeTheme.accent }}
          />
          <span>GATHER</span>
          <span>·</span>
          <span>BUILD</span>
          <span>·</span>
          <span>CONQUER</span>
          <span
            className="w-12 h-px"
            style={{ background: timeTheme.accent }}
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
