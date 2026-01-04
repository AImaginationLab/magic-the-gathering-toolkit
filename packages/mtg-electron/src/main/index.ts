/**
 * Main process entry point.
 * Creates the BrowserWindow and spawns the Python sidecar API server.
 */

import * as http from "http";

// Helper to check if error is a pipe/IO error (safe to ignore)
const isPipeError = (error: Error | undefined): boolean => {
  const msg = error?.message || "";
  return msg.includes("EIO") || msg.includes("EPIPE") || msg.includes("write ");
};

// Initialize unhandled error catching first
import unhandled from "electron-unhandled";
unhandled({
  showDialog: false, // Disable default dialog, we handle it ourselves
  logger: (error) => {
    // Ignore EIO/EPIPE errors - these are just broken pipe errors from logging
    // to a disconnected terminal (common in dev mode)
    if (isPipeError(error)) {
      return;
    }
    // Import logger dynamically to avoid circular deps
    import("./utils/logger").then(({ logger }) => {
      logger.error("Unhandled error:", error);
    });
  },
});

// Handle uncaught exceptions manually to filter pipe errors
process.on("uncaughtException", (error) => {
  if (isPipeError(error)) {
    return; // Silently ignore pipe errors
  }
  // Re-throw to let electron-unhandled handle it
  throw error;
});

import { app, BrowserWindow, shell, ipcMain, session } from "electron";

// GPU flags to prevent WebGL context loss (important for Three.js)
// See: https://github.com/electron/electron/issues/31625
app.commandLine.appendSwitch("enable-features", "SharedArrayBuffer");
app.commandLine.appendSwitch("disable-gpu-vsync");
app.commandLine.appendSwitch("ignore-gpu-blocklist");
app.commandLine.appendSwitch("enable-gpu-rasterization");
import { join } from "path";
import { electronApp, optimizer, is } from "@electron-toolkit/utils";
import contextMenu from "electron-context-menu";
import { getSidecar } from "./sidecar";
import {
  initApiClientFromSidecar,
  getApiClient,
  type CollectionSortField,
} from "./api-client-generated";
import {
  logger,
  store,
  getWindowBounds,
  setWindowBounds,
  getRecentSearches,
  clearRecentSearches,
  initDevTools,
} from "./utils";
import {
  initDatabases,
  closeDatabases,
  getCollectionList,
  getCollectionStats,
  getCollectionValue,
  updateCollectionCard,
  deleteCollectionCard,
  recordPriceSnapshot,
  getCardPriceHistory,
  getCollectionValueHistory,
} from "./collection-db";
import { createApplicationMenu } from "./menu";

// Enable context menu for all windows
contextMenu({
  showSaveImageAs: true,
  showCopyImage: true,
  showCopyLink: true,
  showInspectElement: is.dev,
});

// Cache for collection value (invalidated on add/update/delete or new pricing data)
// TTL of 5 minutes to prevent indefinitely stale data
const COLLECTION_VALUE_CACHE_TTL_MS = 5 * 60 * 1000;
// Cache uses the actual PriceCollectionResponse type from the API
import type { PriceCollectionResponse } from "./api-client-generated";
let collectionValueCache: PriceCollectionResponse | null = null;
let collectionValueCacheTime: number | null = null;

// Allowlist of permitted store keys for security
const ALLOWED_STORE_KEYS = ["theme", "windowBounds", "recentSearches"] as const;
type AllowedStoreKey = (typeof ALLOWED_STORE_KEYS)[number];

function invalidateCollectionValueCache(): void {
  collectionValueCache = null;
  collectionValueCacheTime = null;
  logger.debug("Collection value cache invalidated");
}

function isCollectionValueCacheValid(): boolean {
  if (collectionValueCache === null || collectionValueCacheTime === null) {
    return false;
  }
  return Date.now() - collectionValueCacheTime < COLLECTION_VALUE_CACHE_TTL_MS;
}

function createWindow(): BrowserWindow {
  // Restore previous window bounds or use defaults
  const savedBounds = getWindowBounds();

  const mainWindow = new BrowserWindow({
    width: savedBounds?.width ?? 1280,
    height: savedBounds?.height ?? 800,
    x: savedBounds?.x,
    y: savedBounds?.y,
    minWidth: 800,
    minHeight: 600,
    show: false,
    backgroundColor: "#1a1a2e",
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"),
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      webgl: true,
      enableWebSQL: false,
    },
  });

  mainWindow.on("ready-to-show", () => {
    mainWindow.show();
  });

  // Save window bounds on close
  mainWindow.on("close", () => {
    const bounds = mainWindow.getBounds();
    setWindowBounds(bounds);
    logger.debug("Window bounds saved:", bounds);
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url);
    return { action: "deny" };
  });

  // Load the renderer
  if (is.dev && process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }

  // Create application menu with keyboard shortcuts
  createApplicationMenu(mainWindow);

  return mainWindow;
}

// Register IPC handlers
function registerIpcHandlers(): void {
  ipcMain.handle("app:get-version", () => {
    return app.getVersion();
  });

  ipcMain.handle("app:get-platform", () => {
    return process.platform;
  });

  // Sidecar status handler
  ipcMain.handle("sidecar:status", () => {
    const sidecar = getSidecar();
    return {
      status: sidecar.getStatus(),
      isRunning: sidecar.isRunning(),
      baseUrl: sidecar.baseUrl,
    };
  });

  // API client handlers - these use the mtg-core HTTP API
  ipcMain.handle("api:health", async () => {
    try {
      const client = getApiClient();
      return await client.health();
    } catch (error) {
      logger.error("API health check failed:", error);
      return { status: "error", error: String(error) };
    }
  });

  ipcMain.handle("api:setup-status", async () => {
    try {
      const client = getApiClient();
      return await client.getSetupStatus();
    } catch (error) {
      logger.error("Setup status check failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:ensure-user-db", async () => {
    try {
      const client = getApiClient();
      return await client.ensureUserDb();
    } catch (error) {
      logger.error("Ensure user DB failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:run-update", async (_event, force: boolean = false) => {
    try {
      const client = getApiClient();
      const result = await client.runUpdate(force);
      // Invalidate pricing cache since new data may have been downloaded
      invalidateCollectionValueCache();
      return result;
    } catch (error) {
      logger.error("Run update failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:init-database", async () => {
    try {
      const client = getApiClient();
      return await client.initDatabase();
    } catch (error) {
      logger.error("Init database failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:get-update-stream-url",
    async (_event, force: boolean = false) => {
      try {
        const client = getApiClient();
        return client.getUpdateStreamUrl(force);
      } catch (error) {
        logger.error("Get update stream URL failed:", error);
        throw error;
      }
    },
  );

  // SSE-based update with progress - runs in main process to avoid CSP issues
  ipcMain.handle(
    "api:run-update-with-progress",
    async (event, force: boolean = false) => {
      const client = getApiClient();
      const streamUrl = client.getUpdateStreamUrl(force);

      return new Promise<{
        success: boolean;
        message?: string;
        error?: string;
      }>((resolve) => {
        logger.info("Starting update stream from:", streamUrl);
        let resolved = false;

        const safeResolve = (result: {
          success: boolean;
          message?: string;
          error?: string;
        }): void => {
          if (!resolved) {
            resolved = true;
            resolve(result);
          }
        };

        // Use Node's http module to fetch SSE stream
        const url = new URL(streamUrl);

        const req = http.request(
          {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname + url.search,
            method: "GET",
            headers: {
              Accept: "text/event-stream",
              "Cache-Control": "no-cache",
            },
          },
          (res: import("http").IncomingMessage) => {
            let buffer = "";
            let lastPhase = "";

            res.on("data", (chunk: Buffer) => {
              buffer += chunk.toString();

              // Parse SSE messages
              const lines = buffer.split("\n");
              buffer = lines.pop() || ""; // Keep incomplete line in buffer

              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    lastPhase = data.phase;
                    // Send progress to renderer (safely check if window still exists)
                    if (!event.sender.isDestroyed()) {
                      try {
                        event.sender.send("update-progress", data);
                      } catch (sendErr) {
                        logger.warn("Failed to send progress update:", sendErr);
                      }
                    }

                    if (data.phase === "complete") {
                      // Invalidate pricing cache since new data was downloaded
                      invalidateCollectionValueCache();
                      // Automatically record a price snapshot with the new data
                      recordPriceSnapshot()
                        .then((result) => {
                          if (result.success) {
                            logger.info(
                              `Auto-recorded price snapshot for ${result.cardsRecorded} cards`,
                            );
                          }
                        })
                        .catch((err) => {
                          logger.warn(
                            "Failed to auto-record price snapshot:",
                            err,
                          );
                        });
                      safeResolve({
                        success: true,
                        message: "Update complete",
                      });
                    } else if (data.phase === "up_to_date") {
                      safeResolve({
                        success: true,
                        message: "Already up to date",
                      });
                    } else if (data.phase === "error") {
                      safeResolve({ success: false, error: data.message });
                    }
                  } catch (parseErr) {
                    logger.warn("Failed to parse SSE message:", parseErr);
                  }
                }
              }
            });

            res.on("end", () => {
              logger.info("Update stream ended, last phase:", lastPhase);
              // If stream ended without a terminal phase, it was interrupted
              if (!resolved) {
                safeResolve({
                  success: false,
                  error: `Update stream ended unexpectedly (last phase: ${lastPhase || "none"})`,
                });
              }
            });

            res.on("error", (err: Error) => {
              logger.error("Update stream error:", err);
              safeResolve({ success: false, error: err.message });
            });
          },
        );

        req.on("error", (err: Error) => {
          logger.error("Update request error:", err);
          safeResolve({ success: false, error: err.message });
        });

        // Set a long timeout for the update (30 minutes)
        req.setTimeout(30 * 60 * 1000, () => {
          logger.error("Update request timed out");
          req.destroy();
          safeResolve({ success: false, error: "Update timed out" });
        });

        req.end();
      });
    },
  );

  ipcMain.handle("api:search-cards", async (_event, filters) => {
    try {
      const client = getApiClient();
      return await client.searchCards(filters);
    } catch (error) {
      logger.error("API search failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:card-details", async (_event, name: string) => {
    try {
      const client = getApiClient();
      return await client.getCardDetails(name);
    } catch (error) {
      logger.error("API card details failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:card-rulings", async (_event, name: string) => {
    try {
      const client = getApiClient();
      return await client.getCardRulings(name);
    } catch (error) {
      logger.error("API card rulings failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:card-printings", async (_event, name: string) => {
    try {
      const client = getApiClient();
      return await client.getCardPrintings(name);
    } catch (error) {
      logger.error("API card printings failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:find-synergies",
    async (
      _event,
      cardName: string,
      options?: { limit?: number; formatLegal?: string },
    ) => {
      try {
        const client = getApiClient();
        return await client.findSynergies(cardName, options);
      } catch (error) {
        logger.error("API find synergies failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:detect-combos", async (_event, cardNames: string[]) => {
    try {
      const client = getApiClient();
      return await client.detectCombos(cardNames);
    } catch (error) {
      logger.error("API detect combos failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:combos-for-card", async (_event, cardName: string) => {
    try {
      const client = getApiClient();
      return await client.getCombosForCard(cardName);
    } catch (error) {
      logger.error("API combos for card failed:", error);
      throw error;
    }
  });

  // Recommendations IPC handlers
  ipcMain.handle("api:get-filter-options", async () => {
    try {
      const client = getApiClient();
      return await client.getFilterOptions();
    } catch (error) {
      logger.error("API get filter options failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:suggest-cards",
    async (
      _event,
      deckCards: string[],
      options?: {
        formatLegal?: string;
        budgetMax?: number;
        maxResults?: number;
        setCodes?: string[];
        themes?: string[];
        creatureTypes?: string[];
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.suggestCards(deckCards, options);
      } catch (error) {
        logger.error("API suggest cards failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:find-commanders",
    async (
      _event,
      options?: {
        collectionCards?: string[];
        useCollection?: boolean;
        colors?: string[];
        creatureType?: string;
        creatureTypes?: string[];
        theme?: string;
        themes?: string[];
        format?: string;
        setCodes?: string[];
        limit?: number;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.findCommanders(options);
      } catch (error) {
        logger.error("API find commanders failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:find-decks",
    async (
      _event,
      options?: {
        collectionCards?: string[];
        useCollection?: boolean;
        colors?: string[];
        creatureType?: string;
        creatureTypes?: string[];
        theme?: string;
        themes?: string[];
        format?: string;
        setCodes?: string[];
        minCompletion?: number;
        limit?: number;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.findDecks(options);
      } catch (error) {
        logger.error("API find decks failed:", error);
        throw error;
      }
    },
  );

  // Store IPC handlers
  ipcMain.handle("store:get-recent-searches", () => {
    return getRecentSearches();
  });

  ipcMain.handle("store:clear-recent-searches", () => {
    clearRecentSearches();
    return { success: true };
  });

  ipcMain.handle("store:get", (_event, key: string) => {
    if (!ALLOWED_STORE_KEYS.includes(key as AllowedStoreKey)) {
      logger.warn(`Attempted to get invalid store key: ${key}`);
      return undefined;
    }
    return store.get(key as AllowedStoreKey);
  });

  ipcMain.handle("store:set", (_event, key: string, value: unknown) => {
    if (!ALLOWED_STORE_KEYS.includes(key as AllowedStoreKey)) {
      logger.warn(`Attempted to set invalid store key: ${key}`);
      return { success: false, error: `Invalid store key: ${key}` };
    }
    store.set(key as AllowedStoreKey, value);
    return { success: true };
  });

  // Collection IPC handlers - async worker thread queries
  ipcMain.handle(
    "collection:list",
    async (_event, args: { limit?: number; offset?: number }) => {
      try {
        const limit = args.limit ?? 100;
        const offset = args.offset ?? 0;
        return await getCollectionList(limit, offset);
      } catch (error) {
        logger.error("Failed to fetch collection:", error);
        return {
          cards: [],
          stats: { unique: 0, total: 0, foils: 0 },
          total: 0,
          error: String(error),
        };
      }
    },
  );

  ipcMain.handle("collection:stats", async () => {
    try {
      return await getCollectionStats();
    } catch (error) {
      logger.error("Failed to fetch collection stats:", error);
      return {
        unique: 0,
        total: 0,
        foils: 0,
        colors: {},
        types: {},
        rarities: {},
        manaCurve: {},
        topSets: [],
        avgCmc: 0,
        error: String(error),
      };
    }
  });

  ipcMain.handle("collection:value", async () => {
    try {
      return await getCollectionValue();
    } catch (error) {
      logger.error("Failed to fetch collection value:", error);
      return {
        totalValue: 0,
        mostValuable: [],
        error: String(error),
      };
    }
  });

  ipcMain.handle(
    "collection:update",
    async (
      _event,
      args: {
        cardName: string;
        setCode: string | null;
        collectorNumber: string | null;
        quantity: number;
        foilQuantity: number;
      },
    ) => {
      try {
        const result = await updateCollectionCard(args);
        if (result.success) {
          invalidateCollectionValueCache();
        }
        return result;
      } catch (error) {
        logger.error("Failed to update collection card:", error);
        return { success: false, error: String(error) };
      }
    },
  );

  ipcMain.handle(
    "collection:delete",
    async (
      _event,
      args: {
        cardName: string;
        setCode: string | null;
        collectorNumber: string | null;
      },
    ) => {
      try {
        const result = await deleteCollectionCard(args);
        if (result.success) {
          invalidateCollectionValueCache();
        }
        return result;
      } catch (error) {
        logger.error("Failed to delete collection card:", error);
        return { success: false, error: String(error) };
      }
    },
  );

  ipcMain.handle("collection:record-prices", async () => {
    try {
      return await recordPriceSnapshot();
    } catch (error) {
      logger.error("Failed to record price snapshot:", error);
      return { success: false, cardsRecorded: 0, error: String(error) };
    }
  });

  ipcMain.handle(
    "collection:price-history",
    async (
      _event,
      args: {
        cardName: string;
        setCode?: string;
        collectorNumber?: string;
        days?: number;
      },
    ) => {
      try {
        return await getCardPriceHistory(args);
      } catch (error) {
        logger.error("Failed to get card price history:", error);
        return [];
      }
    },
  );

  ipcMain.handle("collection:value-history", async (_event, days?: number) => {
    try {
      return await getCollectionValueHistory(days);
    } catch (error) {
      logger.error("Failed to get collection value history:", error);
      return [];
    }
  });

  // Deck IPC handlers - use HTTP API via generated client
  ipcMain.handle("api:list-decks", async () => {
    try {
      const client = getApiClient();
      return await client.listDecks();
    } catch (error) {
      logger.error("API list decks failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:create-deck",
    async (
      _event,
      request: {
        name: string;
        format?: string | null;
        commander?: string | null;
        description?: string | null;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.createDeck(request);
      } catch (error) {
        logger.error("API create deck failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:get-deck", async (_event, deckId: number) => {
    try {
      const client = getApiClient();
      return await client.getDeck(deckId);
    } catch (error) {
      logger.error("API get deck failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:update-deck",
    async (
      _event,
      deckId: number,
      request: {
        name?: string | null;
        format?: string | null;
        commander?: string | null;
        description?: string | null;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.updateDeck(deckId, request);
      } catch (error) {
        logger.error("API update deck failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:delete-deck", async (_event, deckId: number) => {
    try {
      const client = getApiClient();
      return await client.deleteDeck(deckId);
    } catch (error) {
      logger.error("API delete deck failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:add-card-to-deck",
    async (
      _event,
      deckId: number,
      request: {
        card_name: string;
        quantity?: number;
        is_sideboard?: boolean;
        is_commander?: boolean;
        set_code?: string | null;
        collector_number?: string | null;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.addCardToDeck(deckId, request);
      } catch (error) {
        logger.error("API add card to deck failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:remove-card-from-deck",
    async (
      _event,
      deckId: number,
      cardName: string,
      sideboard: boolean = false,
      maybeboard: boolean = false,
    ) => {
      try {
        const client = getApiClient();
        return await client.removeCardFromDeck(
          deckId,
          cardName,
          sideboard,
          maybeboard,
        );
      } catch (error) {
        logger.error("API remove card from deck failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:update-card-quantity",
    async (
      _event,
      deckId: number,
      cardName: string,
      quantity: number,
      sideboard: boolean = false,
      maybeboard: boolean = false,
    ) => {
      try {
        const client = getApiClient();
        return await client.updateCardQuantity(
          deckId,
          cardName,
          quantity,
          sideboard,
          maybeboard,
        );
      } catch (error) {
        logger.error("API update card quantity failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:parse-import-deck",
    async (
      _event,
      input: {
        url?: string | null;
        text?: string | null;
        name?: string | null;
        format?: string | null;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.parseImportDeck(input);
      } catch (error) {
        logger.error("API parse import deck failed:", error);
        throw error;
      }
    },
  );

  // Deck analysis IPC handlers
  ipcMain.handle("api:validate-deck", async (_event, input) => {
    try {
      const client = getApiClient();
      return await client.validateDeck(input);
    } catch (error) {
      logger.error("API validate deck failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:analyze-mana-curve", async (_event, input) => {
    try {
      const client = getApiClient();
      return await client.analyzeManaCurve(input);
    } catch (error) {
      logger.error("API analyze mana curve failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:analyze-colors", async (_event, input) => {
    try {
      const client = getApiClient();
      return await client.analyzeColors(input);
    } catch (error) {
      logger.error("API analyze colors failed:", error);
      throw error;
    }
  });

  ipcMain.handle("api:analyze-composition", async (_event, input) => {
    try {
      const client = getApiClient();
      return await client.analyzeComposition(input);
    } catch (error) {
      logger.error("API analyze composition failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:analyze-deck-health",
    async (
      _event,
      { input, deckFormat }: { input: unknown; deckFormat?: string | null },
    ) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckHealth(
          input as Parameters<typeof client.analyzeDeckHealth>[0],
          deckFormat,
        );
      } catch (error) {
        logger.error("API analyze deck health failed:", error);
        throw error;
      }
    },
  );

  // Analyze deck by ID (fetches cards from database)
  ipcMain.handle(
    "api:analyze-deck-health-by-id",
    async (_event, deckId: number) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckHealthById(deckId);
      } catch (error) {
        logger.error("API analyze deck health by ID failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:analyze-deck-mana-curve-by-id",
    async (_event, deckId: number) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckManaCurveById(deckId);
      } catch (error) {
        logger.error("API analyze deck mana curve by ID failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:analyze-deck-colors-by-id",
    async (_event, deckId: number) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckColorsById(deckId);
      } catch (error) {
        logger.error("API analyze deck colors by ID failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:analyze-deck-price-by-id",
    async (_event, deckId: number) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckPriceById(deckId);
      } catch (error) {
        logger.error("API analyze deck price by ID failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle(
    "api:analyze-deck-impact",
    async (
      _event,
      {
        cardName,
        deckId,
        quantity,
      }: { cardName: string; deckId: number; quantity?: number },
    ) => {
      try {
        const client = getApiClient();
        return await client.analyzeDeckImpact(cardName, deckId, quantity ?? 1);
      } catch (error) {
        logger.error("API analyze deck impact failed:", error);
        throw error;
      }
    },
  );

  // Sets IPC handlers
  ipcMain.handle(
    "api:list-sets",
    async (_event, params?: { name?: string; set_type?: string }) => {
      try {
        const client = getApiClient();
        return await client.listSets(params);
      } catch (error) {
        logger.error("API list sets failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:get-set", async (_event, code: string) => {
    try {
      const client = getApiClient();
      return await client.getSet(code);
    } catch (error) {
      logger.error("API get set failed:", error);
      throw error;
    }
  });

  ipcMain.handle(
    "api:get-set-cards",
    async (
      _event,
      {
        code,
        page,
        pageSize,
      }: { code: string; page?: number; pageSize?: number },
    ) => {
      try {
        const client = getApiClient();
        return await client.getSetCards(code, page, pageSize);
      } catch (error) {
        logger.error("API get set cards failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:get-set-analysis", async (_event, code: string) => {
    try {
      const client = getApiClient();
      return await client.getSetAnalysis(code);
    } catch (error) {
      logger.error("API get set analysis failed:", error);
      throw error;
    }
  });

  // Artists IPC handlers
  ipcMain.handle(
    "api:list-artists",
    async (
      _event,
      params?: {
        query?: string;
        min_cards?: number;
        limit?: number;
        offset?: number;
      },
    ) => {
      try {
        const client = getApiClient();
        return await client.listArtists(params);
      } catch (error) {
        logger.error("API list artists failed:", error);
        throw error;
      }
    },
  );

  ipcMain.handle("api:get-artist-cards", async (_event, name: string) => {
    try {
      const client = getApiClient();
      return await client.getArtistCards(name);
    } catch (error) {
      logger.error("API get artist cards failed:", error);
      throw error;
    }
  });

  // Collection parsing IPC handler
  ipcMain.handle(
    "api:parse-collection",
    async (_event, text: string, defaultQuantity?: number) => {
      try {
        const client = getApiClient();
        return await client.parseCollection(text, defaultQuantity);
      } catch (error) {
        logger.error("API parse collection failed:", error);
        throw error;
      }
    },
  );

  // Collection pricing IPC handler
  ipcMain.handle("api:price-collection", async (_event, cards) => {
    try {
      const client = getApiClient();
      return await client.priceCollection(cards);
    } catch (error) {
      logger.error("API price collection failed:", error);
      throw error;
    }
  });

  // Import collection - accepts raw text, parses and batch-inserts server-side
  ipcMain.handle(
    "api:collection-import",
    async (_event, text: string, mode: "add" | "replace" = "add") => {
      try {
        const client = getApiClient();
        const result = await client.importCollection(text, mode);
        // Invalidate cache when cards are added/replaced
        if (result.added_count > 0 || mode === "replace") {
          invalidateCollectionValueCache();
        }
        return result;
      } catch (error) {
        logger.error("API collection import failed:", error);
        throw error;
      }
    },
  );

  // Collection list with sorting and pagination
  ipcMain.handle(
    "api:collection-list",
    async (
      _event,
      options: {
        sortBy?: string;
        sortOrder?: "asc" | "desc";
        page?: number;
        pageSize?: number;
      },
    ) => {
      try {
        const client = getApiClient();
        // Cast sortBy to the enum type - validation happens server-side
        return await client.listCollection({
          ...options,
          sortBy: options.sortBy as CollectionSortField | undefined,
        });
      } catch (error) {
        logger.error("API collection list failed:", error);
        throw error;
      }
    },
  );

  // Collection value IPC handler - prices entire collection from user_data.sqlite
  // Cached until collection changes, new pricing data is downloaded, or TTL expires
  ipcMain.handle("api:collection-value", async () => {
    try {
      // Return cached value if valid (not null and within TTL)
      if (isCollectionValueCacheValid()) {
        logger.debug("Returning cached collection value");
        return collectionValueCache;
      }

      // Fetch from API
      const client = getApiClient();
      const data = await client.getCollectionValue();

      // Cache the result with timestamp
      collectionValueCache = data;
      collectionValueCacheTime = Date.now();
      logger.debug("Collection value cached");

      return data;
    } catch (error) {
      logger.error("API collection value failed:", error);
      // Invalidate cache on error to prevent stale data
      invalidateCollectionValueCache();
      // Return safe fallback instead of throwing
      return { totalValue: 0, mostValuable: [], error: String(error) };
    }
  });
}

app.whenReady().then(async () => {
  logger.info("MTG Spellbook starting...");

  // Initialize collection databases (fast direct SQLite)
  initDatabases();

  // Initialize dev tools (only in dev mode)
  await initDevTools();

  // Set app user model id for Windows
  electronApp.setAppUserModelId("com.mtgspellbook.app");

  // Security: Set Content Security Policy for production
  if (!is.dev) {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      callback({
        responseHeaders: {
          ...details.responseHeaders,
          "Content-Security-Policy": [
            "default-src 'self'; " +
              "script-src 'self'; " +
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; " +
              "img-src 'self' https://cards.scryfall.io https://*.scryfall.com data:; " +
              "connect-src 'self' http://127.0.0.1:3179 http://127.0.0.1:8765; " +
              "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net;",
          ],
        },
      });
    });
    logger.debug("CSP headers configured for production");
  }

  // Security: Handle permission requests
  session.defaultSession.setPermissionRequestHandler(
    (_webContents, permission, callback) => {
      // Only allow specific permissions
      const allowedPermissions = [
        "clipboard-read",
        "clipboard-sanitized-write",
        "media", // Camera access for card scanning
      ];
      if (allowedPermissions.includes(permission)) {
        callback(true);
      } else {
        logger.warn(`Denied permission request: ${permission}`);
        callback(false);
      }
    },
  );

  // Register IPC handlers
  registerIpcHandlers();

  // Start the Python sidecar (mtg-api server)
  const sidecar = getSidecar();
  try {
    await sidecar.start();
    initApiClientFromSidecar(sidecar);
    logger.info("Sidecar started and API client initialized");
  } catch (error) {
    logger.warn("Sidecar not available, API features will be limited:", error);
  }

  // MCP server connection disabled - using HTTP API via sidecar instead

  // Optimize DevTools shortcuts in development
  app.on("browser-window-created", (_, window) => {
    optimizer.watchWindowShortcuts(window);
  });

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });

  logger.info("MTG Spellbook ready");
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", async () => {
  logger.info("MTG Spellbook shutting down...");
  closeDatabases();

  // Stop the Python sidecar
  const sidecar = getSidecar();
  await sidecar.stop();
});
