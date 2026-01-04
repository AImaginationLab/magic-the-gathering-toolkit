/**
 * Collection database access using worker thread.
 * Keeps main thread responsive while running SQLite queries.
 */
import { Worker } from "worker_threads";
import { join } from "path";
import { logger } from "./utils";

let worker: Worker | null = null;
let messageId = 0;
const pendingRequests = new Map<
  number,
  {
    resolve: (value: unknown) => void;
    reject: (error: Error) => void;
  }
>();

export interface CollectionCard {
  cardName: string;
  quantity: number;
  foilQuantity: number;
  setCode: string | null;
  setName: string | null;
  collectorNumber: string | null;
  addedAt: string;
  // Enriched data from card database
  colors: string[];
  typeLine: string | null;
  rarity: string | null;
  cmc: number;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

export interface CollectionStats {
  unique: number;
  total: number;
  foils: number;
  colors: Record<string, number>;
  types: Record<string, number>;
  rarities: Record<string, number>;
  manaCurve: Record<number, number>;
  topSets: Array<{ code: string; count: number }>;
  avgCmc: number;
}

export interface CollectionValue {
  totalValue: number;
  mostValuable: Array<{
    cardName: string;
    value: number;
    setCode: string | null;
    collectorNumber: string | null;
  }>;
}

export interface CollectionResult {
  cards: CollectionCard[];
  stats: { unique: number; total: number; foils: number };
  total: number;
}

export function initDatabases(): void {
  if (worker) return;

  try {
    // Worker script path - in dev it's the .ts file compiled to .js in out/
    const workerPath = join(__dirname, "collection-worker.js");
    logger.debug("Starting collection worker:", workerPath);

    worker = new Worker(workerPath);

    worker.on(
      "message",
      (msg: { id: number; result?: unknown; error?: string }) => {
        const pending = pendingRequests.get(msg.id);
        if (pending) {
          pendingRequests.delete(msg.id);
          if (msg.error) {
            pending.reject(new Error(msg.error));
          } else {
            pending.resolve(msg.result);
          }
        }
      },
    );

    worker.on("error", (error) => {
      logger.error("Collection worker error:", error);
    });

    worker.on("exit", (code) => {
      if (code !== 0) {
        logger.error("Collection worker exited with code:", code);
      }
      // Reject all pending requests - worker is gone
      for (const [, { reject }] of pendingRequests) {
        reject(new Error("Worker exited unexpectedly"));
      }
      pendingRequests.clear();
      worker = null;
    });

    logger.info("Collection worker started");
  } catch (error) {
    logger.error("Failed to start collection worker:", error);
  }
}

export function closeDatabases(): void {
  if (worker) {
    worker.terminate();
    worker = null;
  }
}

const DEFAULT_WORKER_TIMEOUT_MS = 30000;

async function sendMessage<T>(
  type: string,
  args?: unknown,
  timeoutMs = DEFAULT_WORKER_TIMEOUT_MS,
): Promise<T> {
  if (!worker) {
    throw new Error("Collection worker not initialized");
  }

  const id = ++messageId;
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pendingRequests.delete(id);
      reject(new Error(`Worker request timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    pendingRequests.set(id, {
      resolve: (value: unknown) => {
        clearTimeout(timeout);
        resolve(value as T);
      },
      reject: (error: Error) => {
        clearTimeout(timeout);
        reject(error);
      },
    });
    worker!.postMessage({ id, type, args });
  });
}

export async function getCollectionList(
  limit: number = 100,
  offset: number = 0,
): Promise<CollectionResult> {
  try {
    return await sendMessage<CollectionResult>("list", { limit, offset });
  } catch (error) {
    logger.error("Failed to get collection list:", error);
    return { cards: [], stats: { unique: 0, total: 0, foils: 0 }, total: 0 };
  }
}

export async function getCollectionStats(): Promise<CollectionStats> {
  try {
    return await sendMessage<CollectionStats>("stats");
  } catch (error) {
    logger.error("Failed to get collection stats:", error);
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
    };
  }
}

export async function getCollectionValue(): Promise<CollectionValue> {
  try {
    return await sendMessage<CollectionValue>("value");
  } catch (error) {
    logger.error("Failed to get collection value:", error);
    return { totalValue: 0, mostValuable: [] };
  }
}

export interface UpdateCollectionCardArgs {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
  quantity: number;
  foilQuantity: number;
}

export interface UpdateCollectionCardResult {
  success: boolean;
  card?: CollectionCard;
}

export async function updateCollectionCard(
  args: UpdateCollectionCardArgs,
): Promise<UpdateCollectionCardResult> {
  try {
    return await sendMessage<UpdateCollectionCardResult>("update", args);
  } catch (error) {
    logger.error("Failed to update collection card:", error);
    return { success: false };
  }
}

export interface DeleteCollectionCardArgs {
  cardName: string;
  setCode: string | null;
  collectorNumber: string | null;
}

export interface DeleteCollectionCardResult {
  success: boolean;
}

export interface RecordPricesResult {
  success: boolean;
  cardsRecorded: number;
}

export interface CardPriceHistoryArgs {
  cardName: string;
  setCode?: string;
  collectorNumber?: string;
  days?: number;
}

export interface PriceHistoryEntry {
  date: string;
  priceUsd: number | null;
  priceUsdFoil: number | null;
}

export interface CollectionValueHistoryEntry {
  date: string;
  totalValue: number;
  cardCount: number;
}

export async function deleteCollectionCard(
  args: DeleteCollectionCardArgs,
): Promise<DeleteCollectionCardResult> {
  try {
    return await sendMessage<DeleteCollectionCardResult>("delete", args);
  } catch (error) {
    logger.error("Failed to delete collection card:", error);
    return { success: false };
  }
}

export async function recordPriceSnapshot(): Promise<RecordPricesResult> {
  try {
    return await sendMessage<RecordPricesResult>("recordPrices");
  } catch (error) {
    logger.error("Failed to record price snapshot:", error);
    return { success: false, cardsRecorded: 0 };
  }
}

export async function getCardPriceHistory(
  args: CardPriceHistoryArgs,
): Promise<PriceHistoryEntry[]> {
  try {
    return await sendMessage<PriceHistoryEntry[]>("priceHistory", args);
  } catch (error) {
    logger.error("Failed to get card price history:", error);
    return [];
  }
}

export async function getCollectionValueHistory(
  days?: number,
): Promise<CollectionValueHistoryEntry[]> {
  try {
    return await sendMessage<CollectionValueHistoryEntry[]>("valueHistory", {
      days,
    });
  } catch (error) {
    logger.error("Failed to get collection value history:", error);
    return [];
  }
}
