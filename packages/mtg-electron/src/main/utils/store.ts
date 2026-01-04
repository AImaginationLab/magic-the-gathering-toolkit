/**
 * Persistent user preferences using electron-store.
 * Type-safe with schema validation.
 */
import Store from "electron-store";

// Store schema for type safety
export interface StoreSchema {
  // Window position and size
  windowBounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;

  // Recent searches for quick access
  recentSearches: string[];

  // UI preferences
  theme: "dark" | "light" | "system";
  showCardImages: boolean;

  // Default game settings
  defaultFormat: string;

  // Last selected deck for "Add to Deck" operations
  lastSelectedDeckId: number | null;
}

// Default values for all settings
const defaults: StoreSchema = {
  windowBounds: null,
  recentSearches: [],
  theme: "dark",
  showCardImages: true,
  defaultFormat: "commander",
  lastSelectedDeckId: null,
};

// Create typed store instance
export const store = new Store<StoreSchema>({
  name: "mtg-spellbook-preferences",
  defaults,
  // Clear invalid data on schema mismatch
  clearInvalidConfig: true,
});

// Helper functions for common operations
export function getWindowBounds(): StoreSchema["windowBounds"] {
  return store.get("windowBounds");
}

export function setWindowBounds(bounds: StoreSchema["windowBounds"]): void {
  store.set("windowBounds", bounds);
}

export function addRecentSearch(query: string): void {
  const searches = store.get("recentSearches");
  // Remove duplicate if exists, add to front, keep last 10
  const filtered = searches.filter((s) => s !== query);
  const updated = [query, ...filtered].slice(0, 10);
  store.set("recentSearches", updated);
}

export function getRecentSearches(): string[] {
  return store.get("recentSearches");
}

export function clearRecentSearches(): void {
  store.set("recentSearches", []);
}

export default store;
