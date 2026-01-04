/**
 * SplashScreen - Epic loading screen with iconic MTG card artwork
 *
 * Features a dramatic battle scene using art from legendary cards,
 * with 3D transforms, particle effects, and cinematic animations.
 */
import { useEffect, useState, useCallback, useMemo, useRef } from "react";

import { colors, gradients, animations } from "../theme";

import type { ReactNode, CSSProperties } from "react";
import type { components } from "../../../shared/types/api-generated";

type SetupStatus = components["schemas"]["SetupStatus"];

type InitPhase =
  | "starting"
  | "checking_api"
  | "checking_databases"
  | "updating_data"
  | "ensuring_user_db"
  | "ready"
  | "error";

interface InitStatus {
  phase: InitPhase;
  message: string;
  progress: number;
  error?: string;
  setupStatus?: SetupStatus;
}

interface SplashScreenProps {
  onReady: () => void;
}

// Card position layout - shared across all themes
type CardPosition =
  | "center"
  | "left"
  | "right"
  | "top"
  | "bottom-left"
  | "bottom-right"
  | "far-left"
  | "far-right";

interface BattleCardData {
  name: string;
  art: string;
  position: CardPosition;
  scale: number;
  zIndex: number;
}

// Multiple card themes that rotate
const CARD_THEMES: BattleCardData[][] = [
  // Theme 1: Eldrazi & Phyrexian Horror
  [
    {
      name: "Emrakul, the Aeons Torn",
      art: "https://cards.scryfall.io/art_crop/front/7/6/765fd969-d3da-426a-8bf2-d4e1bb7ae878.jpg?1674097105",
      position: "center",
      scale: 1.4,
      zIndex: 10,
    },
    {
      name: "Sheoldred, the Apocalypse",
      art: "https://cards.scryfall.io/art_crop/front/d/6/d67be074-cdd4-41d9-ac89-0a0456c4e4b2.jpg?1674057568",
      position: "left",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Atraxa, Praetors' Voice",
      art: "https://cards.scryfall.io/art_crop/front/d/0/d0d33d52-3d28-4635-b985-51e126289259.jpg?1599707796",
      position: "right",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Ulamog, the Ceaseless Hunger",
      art: "https://cards.scryfall.io/art_crop/front/1/1/1192f7a9-102e-4b3a-b154-18c8eb332217.jpg?1562899233",
      position: "top",
      scale: 1.2,
      zIndex: 9,
    },
    {
      name: "Kozilek, Butcher of Truth",
      art: "https://cards.scryfall.io/art_crop/front/6/4/64b4b6cd-6d0f-4060-b51f-61f481000d51.jpg?1674097112",
      position: "bottom-left",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Elesh Norn, Grand Cenobite",
      art: "https://cards.scryfall.io/art_crop/front/0/e/0ee0719c-07d0-419a-b6ed-fc3bf982e4d3.jpg?1682347264",
      position: "bottom-right",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Void Winnower",
      art: "https://cards.scryfall.io/art_crop/front/8/c/8cbedb0a-34ca-4d42-bb43-cbea0f3c6d02.jpg?1587039576",
      position: "far-left",
      scale: 0.8,
      zIndex: 6,
    },
    {
      name: "Jin-Gitaxias, Core Augur",
      art: "https://cards.scryfall.io/art_crop/front/1/4/14a360b6-c7b4-4b25-8288-b3bb8d527571.jpg?1562846236",
      position: "far-right",
      scale: 0.8,
      zIndex: 6,
    },
  ],
  // Theme 2: Vampires & Dark Lords
  [
    {
      name: "Edgar Markov",
      art: "https://cards.scryfall.io/art_crop/front/8/d/8d94b8ec-ecda-43c8-a60e-1ba33e6a54a4.jpg?1562616128",
      position: "center",
      scale: 1.4,
      zIndex: 10,
    },
    {
      name: "Elenda, the Dusk Rose",
      art: "https://cards.scryfall.io/art_crop/front/d/1/d129496d-3ae0-4e61-9e20-6259c0754b9e.jpg?1674097423",
      position: "left",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Sorin, Imperious Bloodlord",
      art: "https://cards.scryfall.io/art_crop/front/9/f/9f764be3-dd3f-44b1-a4a6-807d1387590b.jpg?1592516778",
      position: "right",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Saint Elenda",
      art: "https://cards.scryfall.io/art_crop/front/6/1/61d89be7-0b3c-4d73-ac3c-95409278677f.jpg?1714874935",
      position: "top",
      scale: 1.2,
      zIndex: 9,
    },
    {
      name: "Olivia Voldaren",
      art: "https://cards.scryfall.io/art_crop/front/b/6/b6411d49-b108-423c-825f-67fe8dbe1f58.jpg?1593813442",
      position: "bottom-left",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Vona de Iedo, the Antifex",
      art: "https://cards.scryfall.io/art_crop/front/8/5/853e5a1e-91eb-486b-8121-b5bc78d3e827.jpg?1715144565",
      position: "bottom-right",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Blood Artist",
      art: "https://cards.scryfall.io/art_crop/front/8/a/8a5b65ed-250c-42a6-84c0-ac06662ca5ed.jpg?1599332214",
      position: "far-left",
      scale: 0.8,
      zIndex: 6,
    },
    {
      name: "Zyym, Mesmeric Lord",
      art: "https://cards.scryfall.io/art_crop/front/7/1/71615ac1-0df6-452e-a14e-237c35bac09f.jpg?1629920481",
      position: "far-right",
      scale: 0.8,
      zIndex: 6,
    },
  ],
  // Theme 3: Final Fantasy Crossover
  [
    {
      name: "Cloud, Ex-SOLDIER",
      art: "https://cards.scryfall.io/art_crop/front/0/7/07b4e4f8-6a31-4533-be51-668ce3ddc84f.jpg?1752052926",
      position: "center",
      scale: 1.4,
      zIndex: 10,
    },
    {
      name: "Tifa, Martial Artist",
      art: "https://cards.scryfall.io/art_crop/front/0/9/09f09db5-ee5a-4a4b-9dbb-aca0dff04fcf.jpg?1752477267",
      position: "left",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Lightning, Army of One",
      art: "https://cards.scryfall.io/art_crop/front/0/c/0c665905-183b-401f-b83c-a312d032e061.jpg?1748707553",
      position: "right",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Kefka, Ruler of Ruin",
      art: "https://cards.scryfall.io/art_crop/front/0/6/06b7ca77-7194-4a0b-a650-4afd7afb50eb.jpg?1748707894",
      position: "top",
      scale: 1.2,
      zIndex: 9,
    },
    {
      name: "Stay With Me",
      art: "https://cards.scryfall.io/art_crop/front/c/d/cd212de7-25f6-4b3b-a35b-df7d87fe205b.jpg?1749237396",
      position: "bottom-left",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Vivi Ornitier",
      art: "https://cards.scryfall.io/art_crop/front/0/c/0cfc4614-f6c1-4247-ab96-5bd41006ad85.jpg?1748707566",
      position: "bottom-right",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Y'shtola, Night's Blessed",
      art: "https://cards.scryfall.io/art_crop/front/0/b/0bda4de9-d0ec-4d27-b92b-8a76779747cf.jpg?1748704892",
      position: "far-left",
      scale: 0.8,
      zIndex: 6,
    },
    {
      name: "Emet-Selch, Unsundered",
      art: "https://cards.scryfall.io/art_crop/front/0/f/0f462d81-bb1b-4d44-8952-6dff52970792.jpg?1748707887",
      position: "far-right",
      scale: 0.8,
      zIndex: 6,
    },
  ],
  // Theme 4: Good Boys & Legendary Creatures
  [
    {
      name: "Phelia, Exuberant Shepherd",
      art: "https://cards.scryfall.io/art_crop/front/5/5/55707746-da6e-46e5-a5ca-7ac843fdc38e.jpg?1717011522",
      position: "center",
      scale: 1.4,
      zIndex: 10,
    },
    {
      name: "Avacyn, Angel of Hope",
      art: "https://cards.scryfall.io/art_crop/front/7/9/79d70eaa-33fe-4fcc-947f-f6c44c97b14f.jpg?1744789845",
      position: "left",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Goldspan Dragon",
      art: "https://cards.scryfall.io/art_crop/front/9/a/9a23c31d-a056-402a-8142-75189eda667a.jpg?1628381414",
      position: "right",
      scale: 1.0,
      zIndex: 8,
    },
    {
      name: "Nicol Bolas, Dragon-God",
      art: "https://cards.scryfall.io/art_crop/front/6/8/6830e76d-7d38-4f6e-8ab7-abd9ac3fb0d9.jpg?1588736877",
      position: "top",
      scale: 1.2,
      zIndex: 9,
    },
    {
      name: "Purphoros, God of the Forge",
      art: "https://cards.scryfall.io/art_crop/front/2/c/2c89261c-fff8-4145-9448-247a1f924409.jpg?1588680949",
      position: "bottom-left",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Ugin, the Spirit Dragon",
      art: "https://cards.scryfall.io/art_crop/front/1/b/1bacda35-bb91-4537-a14d-846650fa85f6.jpg?1594157535",
      position: "bottom-right",
      scale: 0.9,
      zIndex: 7,
    },
    {
      name: "Jace, the Mind Sculptor",
      art: "https://cards.scryfall.io/art_crop/front/9/d/9d20e671-9b41-4591-b1ef-2a297411beb7.jpg?1733168112",
      position: "far-left",
      scale: 0.8,
      zIndex: 6,
    },
    {
      name: "Liliana of the Veil",
      art: "https://cards.scryfall.io/art_crop/front/0/e/0ec6bee0-f3b9-48cc-9f75-e4029a8f5a8d.jpg?1675619927",
      position: "far-right",
      scale: 0.8,
      zIndex: 6,
    },
  ],
];

// Rotation interval in milliseconds
const THEME_ROTATION_INTERVAL = 8000;

const PHASE_MESSAGES: Record<InitPhase, string> = {
  starting: "Initializing...",
  checking_api: "Connecting to the Multiverse...",
  checking_databases: "Consulting the Archives...",
  updating_data: "Downloading Spell Components...",
  ensuring_user_db: "Preparing Your Spellbook...",
  ready: "Ready to Battle!",
  error: "Planar Disruption Detected",
};

const PHASE_PROGRESS: Record<InitPhase, number> = {
  starting: 5,
  checking_api: 10,
  checking_databases: 15,
  updating_data: 20,
  ensuring_user_db: 90,
  ready: 100,
  error: 0,
};

// Particle component for magical effects
function MagicParticle({
  delay,
  duration,
  startX,
  startY,
}: {
  delay: number;
  duration: number;
  startX: number;
  startY: number;
}): ReactNode {
  const style: CSSProperties = {
    position: "absolute",
    left: `${startX}%`,
    top: `${startY}%`,
    width: Math.random() * 4 + 2,
    height: Math.random() * 4 + 2,
    borderRadius: "50%",
    background: `radial-gradient(circle, ${colors.gold.bright} 0%, transparent 70%)`,
    opacity: 0,
    animation: `particle-float ${duration}s ease-out ${delay}s infinite`,
    pointerEvents: "none",
  };
  return <div style={style} />;
}

// Card artwork component with 3D transforms
function BattleCard({
  art,
  position,
  scale,
  zIndex,
  isLoaded,
  onLoad,
  index,
}: {
  art: string;
  position: string;
  scale: number;
  zIndex: number;
  isLoaded: boolean;
  onLoad: () => void;
  index: number;
}): ReactNode {
  // Stagger glow animation based on card index for organic feel
  const glowDelay = index * 0.5;

  const getPositionStyle = (): CSSProperties => {
    const base: CSSProperties = {
      position: "absolute",
      width: 280 * scale,
      height: 200 * scale,
      borderRadius: 12,
      overflow: "hidden",
      border: `2px solid rgba(201, 162, 39, 0.4)`,
      opacity: isLoaded ? 1 : 0,
      transition: "opacity 1s ease-out",
      transformStyle: "preserve-3d",
      backfaceVisibility: "hidden",
      animation: isLoaded
        ? `card-glow-pulse 3s ease-in-out ${glowDelay}s infinite`
        : "none",
    };

    switch (position) {
      case "center":
        return {
          ...base,
          left: "50%",
          top: "35%",
          transform: `translate(-50%, -50%) perspective(1000px) rotateX(5deg) scale(${scale})`,
          zIndex,
        };
      case "left":
        return {
          ...base,
          left: "15%",
          top: "45%",
          transform: `translate(-50%, -50%) perspective(1000px) rotateY(25deg) rotateX(5deg) scale(${scale})`,
          zIndex,
        };
      case "right":
        return {
          ...base,
          right: "15%",
          top: "45%",
          transform: `translate(50%, -50%) perspective(1000px) rotateY(-25deg) rotateX(5deg) scale(${scale})`,
          zIndex,
        };
      case "top":
        return {
          ...base,
          left: "50%",
          top: "5%",
          transform: `translate(-50%, 0) perspective(1000px) rotateX(15deg) scale(${scale})`,
          zIndex,
        };
      case "bottom-left":
        return {
          ...base,
          left: "8%",
          bottom: "15%",
          transform: `perspective(1000px) rotateY(20deg) rotateX(-5deg) scale(${scale})`,
          zIndex,
        };
      case "bottom-right":
        return {
          ...base,
          right: "8%",
          bottom: "15%",
          transform: `perspective(1000px) rotateY(-20deg) rotateX(-5deg) scale(${scale})`,
          zIndex,
        };
      case "far-left":
        return {
          ...base,
          left: "-5%",
          top: "30%",
          transform: `perspective(1000px) rotateY(35deg) rotateX(10deg) scale(${scale})`,
          zIndex,
          opacity: isLoaded ? 0.7 : 0,
        };
      case "far-right":
        return {
          ...base,
          right: "-5%",
          top: "30%",
          transform: `perspective(1000px) rotateY(-35deg) rotateX(10deg) scale(${scale})`,
          zIndex,
          opacity: isLoaded ? 0.7 : 0,
        };
      default:
        return base;
    }
  };

  return (
    <div style={getPositionStyle()}>
      <img
        src={art}
        alt=""
        onLoad={onLoad}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />
      {/* Glow overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.5) 100%)",
          pointerEvents: "none",
        }}
      />
    </div>
  );
}

function SplashScreen({ onReady }: SplashScreenProps): ReactNode {
  const [status, setStatus] = useState<InitStatus>({
    phase: "starting",
    message: PHASE_MESSAGES.starting,
    progress: PHASE_PROGRESS.starting,
  });
  const [retryCount, setRetryCount] = useState(0);
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set());
  const [currentThemeIndex, setCurrentThemeIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [downloadDetails, setDownloadDetails] = useState<string | null>(null);
  const initializingRef = useRef(false);

  // Rotate through card themes
  useEffect(() => {
    let transitionTimeout: ReturnType<typeof setTimeout> | null = null;

    const rotationTimer = setInterval(() => {
      setIsTransitioning(true);
      transitionTimeout = setTimeout(() => {
        setCurrentThemeIndex((prev) => (prev + 1) % CARD_THEMES.length);
        setIsTransitioning(false);
      }, 500); // Half second for fade out, then switch
    }, THEME_ROTATION_INTERVAL);

    return () => {
      clearInterval(rotationTimer);
      if (transitionTimeout) {
        clearTimeout(transitionTimeout);
      }
    };
  }, []);

  const currentCards = CARD_THEMES[currentThemeIndex];

  // Generate particles
  const particles = useMemo(() => {
    return Array.from({ length: 30 }, (_, i) => ({
      id: i,
      delay: Math.random() * 5,
      duration: 3 + Math.random() * 4,
      startX: Math.random() * 100,
      startY: 60 + Math.random() * 40,
    }));
  }, []);

  const handleImageLoad = useCallback((art: string) => {
    setLoadedImages((prev) => new Set(prev).add(art));
  }, []);

  const updateStatus = useCallback(
    (
      phase: InitPhase,
      options?: {
        message?: string;
        progress?: number;
        error?: string;
        setupStatus?: SetupStatus;
      },
    ): void => {
      setStatus((prev) => ({
        phase,
        message: options?.message || options?.error || PHASE_MESSAGES[phase],
        progress: options?.progress ?? PHASE_PROGRESS[phase],
        error: options?.error,
        setupStatus: options?.setupStatus ?? prev.setupStatus,
      }));
    },
    [],
  );

  const runUpdateWithProgress = useCallback(
    async (force: boolean = false): Promise<boolean> => {
      return new Promise((resolve) => {
        const downloadStartTime = Date.now();

        window.electronAPI.api.setup.onUpdateProgress((data) => {
          const phase = data.phase;
          const progress = data.progress;
          const message = data.message;
          const mappedProgress = 20 + progress * 60;

          // Calculate elapsed time for display
          const elapsed = Math.floor((Date.now() - downloadStartTime) / 1000);
          const minutes = Math.floor(elapsed / 60);
          const seconds = elapsed % 60;
          const timeStr =
            minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

          // Show detailed progress info
          let details: string | null = null;
          if (progress > 0 && progress < 1) {
            const pct = Math.round(progress * 100);
            details = `${pct}% complete • ${timeStr} elapsed`;
          }
          setDownloadDetails(details);

          if (phase === "complete") {
            setDownloadDetails(null);
            window.electronAPI.api.setup.removeUpdateProgressListener();
            resolve(true);
          } else if (phase === "up_to_date") {
            setDownloadDetails(null);
            window.electronAPI.api.setup.removeUpdateProgressListener();
            resolve(true);
          } else if (phase === "error") {
            setDownloadDetails(null);
            window.electronAPI.api.setup.removeUpdateProgressListener();
            updateStatus("error", { error: message });
            resolve(false);
          } else {
            updateStatus("updating_data", {
              message,
              progress: mappedProgress,
            });
          }
        });

        window.electronAPI.api.setup
          .runUpdateWithProgress(force)
          .then((result) => {
            setDownloadDetails(null);
            window.electronAPI.api.setup.removeUpdateProgressListener();
            if (result.success) {
              resolve(true);
            } else {
              updateStatus("error", { error: result.error || "Update failed" });
              resolve(false);
            }
          })
          .catch((err) => {
            setDownloadDetails(null);
            window.electronAPI.api.setup.removeUpdateProgressListener();
            updateStatus("error", {
              error: err instanceof Error ? err.message : "Update failed",
            });
            resolve(false);
          });
      });
    },
    [updateStatus],
  );

  const initialize = useCallback(async (): Promise<void> => {
    // Prevent double initialization (React StrictMode in dev)
    if (initializingRef.current) {
      return;
    }
    initializingRef.current = true;

    try {
      updateStatus("checking_api");

      let apiReady = false;
      let attempts = 0;
      const maxAttempts = 30;

      while (!apiReady && attempts < maxAttempts) {
        try {
          const health = await window.electronAPI.api.health();
          if (health.status === "healthy") {
            apiReady = true;
          } else {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            attempts++;
          }
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          attempts++;
        }
      }

      if (!apiReady) {
        throw new Error("Failed to connect to the Multiverse. Please restart.");
      }

      updateStatus("checking_databases");
      const setupStatus = await window.electronAPI.api.setup.getStatus();
      updateStatus("checking_databases", { setupStatus });

      const needsUpdate =
        setupStatus.needs_initial_setup ||
        !setupStatus.mtg_db_exists ||
        setupStatus.needs_update ||
        !setupStatus.combo_db_exists ||
        !setupStatus.gameplay_db_exists;

      if (needsUpdate) {
        updateStatus("updating_data", {
          message: setupStatus.needs_initial_setup
            ? "Summoning 110,000+ cards from the Blind Eternities..."
            : "Checking for new spells...",
          progress: 20,
        });

        const success = await runUpdateWithProgress(false);

        if (
          !success &&
          (setupStatus.needs_initial_setup || !setupStatus.mtg_db_exists)
        ) {
          throw new Error(
            "Failed to download card database. The Blind Eternities are unreachable.",
          );
        }

        // Initialize database connection after download completes
        // (server may have started without database in setup mode)
        if (success) {
          await window.electronAPI.api.setup.initDatabase();
        }
      }

      updateStatus("ensuring_user_db");
      await window.electronAPI.api.setup.ensureUserDb();

      updateStatus("ready");
      setTimeout(() => {
        onReady();
      }, 1000);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown planar disruption";
      updateStatus("error", { error: errorMessage });
    }
  }, [updateStatus, runUpdateWithProgress, onReady]);

  useEffect(() => {
    initialize();
    return (): void => {
      window.electronAPI.api.setup.removeUpdateProgressListener();
    };
  }, [initialize, retryCount]);

  const handleRetry = (): void => {
    setRetryCount((prev) => prev + 1);
    setStatus({
      phase: "starting",
      message: PHASE_MESSAGES.starting,
      progress: PHASE_PROGRESS.starting,
    });
  };

  return (
    <div style={styles.container}>
      {/* Particle animation styles */}
      <style>{`
        @keyframes particle-float {
          0% {
            opacity: 0;
            transform: translateY(0) scale(0);
          }
          10% {
            opacity: 1;
          }
          90% {
            opacity: 0.5;
          }
          100% {
            opacity: 0;
            transform: translateY(-200px) scale(1.5);
          }
        }
        @keyframes pulse-glow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.1); }
        }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes card-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
        @keyframes card-glow-pulse {
          0%, 100% {
            box-shadow: 0 0 40px rgba(201, 162, 39, 0.3), 0 0 80px rgba(201, 162, 39, 0.15), 0 20px 60px rgba(0, 0, 0, 0.5);
          }
          50% {
            box-shadow: 0 0 60px rgba(201, 162, 39, 0.5), 0 0 100px rgba(201, 162, 39, 0.25), 0 20px 60px rgba(0, 0, 0, 0.5);
          }
        }
        @keyframes card-breathe {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.02); }
        }
        @keyframes title-shimmer {
          0%, 100% {
            filter: drop-shadow(0 0 30px rgba(201, 162, 39, 0.6)) drop-shadow(0 4px 8px rgba(0,0,0,0.8));
          }
          50% {
            filter: drop-shadow(0 0 50px rgba(201, 162, 39, 0.9)) drop-shadow(0 0 80px rgba(201, 162, 39, 0.4)) drop-shadow(0 4px 8px rgba(0,0,0,0.8));
          }
        }
        @keyframes mana-pulse {
          0%, 100% { transform: scale(1); opacity: 0.9; }
          50% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>

      {/* Dark gradient background */}
      <div style={styles.backgroundGradient} />

      {/* Battle scene with card artwork */}
      <div
        style={{
          ...styles.battleScene,
          opacity: isTransitioning ? 0 : 1,
          transition: "opacity 0.5s ease-in-out",
        }}
      >
        {currentCards.map((card, index) => (
          <BattleCard
            key={`${currentThemeIndex}-${card.name}`}
            art={card.art}
            position={card.position}
            scale={card.scale}
            zIndex={card.zIndex}
            isLoaded={loadedImages.has(card.art)}
            onLoad={() => handleImageLoad(card.art)}
            index={index}
          />
        ))}
      </div>

      {/* Magical particles */}
      <div style={styles.particleContainer}>
        {particles.map((p) => (
          <MagicParticle key={p.id} {...p} />
        ))}
      </div>

      {/* Radial glow effects */}
      <div style={styles.centerGlow} />
      <div style={styles.topGlow} />

      {/* Content overlay */}
      <div style={styles.contentOverlay}>
        <div style={styles.content}>
          {/* Logo */}
          <div style={styles.logoContainer}>
            {/* Mana symbols with glow */}
            <div style={styles.manaSymbols}>
              <span
                className="ms ms-w ms-cost"
                style={{ color: "#fffcd6", textShadow: "0 0 15px #fffcd6" }}
              />
              <span
                className="ms ms-u ms-cost"
                style={{ color: "#aad5f5", textShadow: "0 0 15px #aad5f5" }}
              />
              <span
                className="ms ms-b ms-cost"
                style={{ color: "#cbc2d9", textShadow: "0 0 15px #cbc2d9" }}
              />
              <span
                className="ms ms-r ms-cost"
                style={{ color: "#e86a58", textShadow: "0 0 15px #e86a58" }}
              />
              <span
                className="ms ms-g ms-cost"
                style={{ color: "#7bc96a", textShadow: "0 0 15px #7bc96a" }}
              />
            </div>

            {/* Epic title with Cinzel font */}
            <div style={styles.titleContainer}>
              <h1 className="font-display" style={styles.title}>
                <span style={styles.titleMtg}>MTG</span>
                <span style={styles.titleSpellbook}>SPELLBOOK</span>
              </h1>
              {/* Decorative line */}
              <div style={styles.titleDecoration}>
                <div style={styles.decorLine} />
                <div style={styles.decorDiamond} />
                <div style={styles.decorLine} />
              </div>
            </div>

            <p className="font-display" style={styles.subtitle}>
              Magic: The Gathering Toolkit
            </p>
          </div>

          {/* Progress Section */}
          <div style={styles.progressSection}>
            <div style={styles.progressBarContainer}>
              <div
                style={{
                  ...styles.progressBar,
                  width: `${status.progress}%`,
                  background:
                    status.phase === "error"
                      ? colors.status.error
                      : gradients.goldShimmer,
                }}
              />
              <div style={styles.progressGlow} />
            </div>

            <p
              style={{
                ...styles.statusMessage,
                color:
                  status.phase === "error"
                    ? colors.status.error
                    : colors.text.bright,
              }}
            >
              {status.message}
            </p>

            {/* Download progress details */}
            {downloadDetails && (
              <p style={styles.downloadDetails}>{downloadDetails}</p>
            )}

            {status.phase === "error" && (
              <button style={styles.retryButton} onClick={handleRetry}>
                Retry Connection
              </button>
            )}

            {status.phase !== "error" && status.phase !== "ready" && (
              <div style={styles.loadingDots}>
                <span style={{ ...styles.dot, animationDelay: "0s" }} />
                <span style={{ ...styles.dot, animationDelay: "0.2s" }} />
                <span style={{ ...styles.dot, animationDelay: "0.4s" }} />
              </div>
            )}
          </div>

          <p style={styles.version}>v0.1.0</p>
        </div>
      </div>

      {/* Bottom vignette */}
      <div style={styles.bottomVignette} />
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    overflow: "hidden",
    background: "#030305",
  },
  backgroundGradient: {
    position: "absolute",
    inset: 0,
    background: `
      radial-gradient(ellipse at 50% 0%, rgba(30, 20, 50, 0.8) 0%, transparent 50%),
      radial-gradient(ellipse at 20% 50%, rgba(50, 30, 20, 0.4) 0%, transparent 40%),
      radial-gradient(ellipse at 80% 50%, rgba(20, 30, 50, 0.4) 0%, transparent 40%),
      linear-gradient(180deg, #0a0812 0%, #030305 100%)
    `,
    zIndex: 1,
  },
  battleScene: {
    position: "absolute",
    inset: 0,
    zIndex: 2,
    perspective: "1500px",
    perspectiveOrigin: "50% 60%",
  },
  particleContainer: {
    position: "absolute",
    inset: 0,
    zIndex: 5,
    pointerEvents: "none",
  },
  centerGlow: {
    position: "absolute",
    top: "30%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: 800,
    height: 600,
    background: `radial-gradient(ellipse, rgba(201, 162, 39, 0.15) 0%, transparent 60%)`,
    zIndex: 3,
    pointerEvents: "none",
  },
  topGlow: {
    position: "absolute",
    top: 0,
    left: "50%",
    transform: "translateX(-50%)",
    width: "100%",
    height: 400,
    background: `radial-gradient(ellipse at 50% 0%, rgba(100, 50, 150, 0.2) 0%, transparent 70%)`,
    zIndex: 3,
    pointerEvents: "none",
  },
  contentOverlay: {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "center",
    paddingBottom: 60,
    zIndex: 10,
  },
  content: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 24,
    maxWidth: 500,
    width: "100%",
    padding: 32,
  },
  logoContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 12,
  },
  manaSymbols: {
    display: "flex",
    gap: 16,
    fontSize: 24,
    marginBottom: 4,
  },
  titleContainer: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
  },
  title: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 0,
    margin: 0,
    lineHeight: 1,
  },
  titleMtg: {
    fontSize: 28,
    fontWeight: 400,
    color: colors.text.dim,
    letterSpacing: 16,
    textShadow: `
      0 0 30px rgba(201, 162, 39, 0.4),
      0 2px 4px rgba(0,0,0,0.8)
    `,
  },
  titleSpellbook: {
    fontSize: 52,
    fontWeight: 600,
    letterSpacing: 8,
    background: `linear-gradient(180deg,
      ${colors.gold.bright} 0%,
      ${colors.gold.standard} 40%,
      #8B6914 70%,
      ${colors.gold.bright} 100%
    )`,
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    backgroundClip: "text",
    filter:
      "drop-shadow(0 0 30px rgba(201, 162, 39, 0.6)) drop-shadow(0 4px 8px rgba(0,0,0,0.8))",
    animation: "title-shimmer 3s ease-in-out infinite",
  },
  titleDecoration: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginTop: 4,
  },
  decorLine: {
    width: 80,
    height: 1,
    background: `linear-gradient(90deg, transparent, ${colors.gold.standard}, transparent)`,
  },
  decorDiamond: {
    width: 8,
    height: 8,
    background: colors.gold.standard,
    transform: "rotate(45deg)",
    boxShadow: `0 0 10px ${colors.gold.glow}`,
  },
  subtitle: {
    fontSize: 13,
    color: colors.text.muted,
    margin: 0,
    marginTop: 8,
    letterSpacing: 6,
    textTransform: "uppercase",
  },
  progressSection: {
    width: "100%",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 16,
  },
  progressBarContainer: {
    width: "100%",
    height: 6,
    background: "rgba(255,255,255,0.1)",
    borderRadius: 3,
    overflow: "hidden",
    position: "relative",
    boxShadow: "inset 0 1px 3px rgba(0,0,0,0.5)",
  },
  progressBar: {
    height: "100%",
    borderRadius: 3,
    transition: "width 0.4s ease-out",
    boxShadow: "0 0 20px rgba(201, 162, 39, 0.5)",
  },
  progressGlow: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background:
      "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
    backgroundSize: "200% 100%",
    animation: "shimmer 2s infinite",
    pointerEvents: "none",
  },
  statusMessage: {
    fontSize: 15,
    margin: 0,
    textAlign: "center",
    minHeight: 24,
    textShadow: "0 2px 8px rgba(0,0,0,0.8)",
  },
  downloadDetails: {
    fontSize: 12,
    margin: 0,
    marginTop: 4,
    textAlign: "center",
    color: colors.text.muted,
    fontFamily: "monospace",
    letterSpacing: 0.5,
  },
  retryButton: {
    padding: "12px 32px",
    fontSize: 14,
    fontWeight: 600,
    color: colors.void.deep,
    background: `linear-gradient(135deg, ${colors.gold.bright} 0%, ${colors.gold.standard} 100%)`,
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    transition: "all 0.2s ease",
    textTransform: "uppercase",
    letterSpacing: 1,
    boxShadow: `0 4px 20px ${colors.gold.glow}`,
  },
  loadingDots: {
    display: "flex",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: colors.gold.standard,
    animation: `${animations.pulseGlow}`,
    boxShadow: `0 0 10px ${colors.gold.glow}`,
  },
  version: {
    fontSize: 11,
    color: colors.text.muted,
    margin: 0,
    letterSpacing: 1,
  },
  bottomVignette: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 300,
    background:
      "linear-gradient(to top, rgba(3,3,5,0.95) 0%, transparent 100%)",
    zIndex: 8,
    pointerEvents: "none",
  },
};

export default SplashScreen;
