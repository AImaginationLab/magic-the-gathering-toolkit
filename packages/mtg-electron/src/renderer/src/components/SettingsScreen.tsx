import { useState, useEffect, useCallback } from "react";

import { colors } from "../theme";

import type { ReactNode } from "react";

interface Settings {
  theme: "dark" | "light" | "system";
  showCardImages: boolean;
  defaultFormat: string;
}

const FORMATS = [
  { value: "commander", label: "Commander" },
  { value: "modern", label: "Modern" },
  { value: "standard", label: "Standard" },
  { value: "pioneer", label: "Pioneer" },
  { value: "legacy", label: "Legacy" },
  { value: "vintage", label: "Vintage" },
  { value: "pauper", label: "Pauper" },
];

export function SettingsScreen(): ReactNode {
  const [settings, setSettings] = useState<Settings>({
    theme: "dark",
    showCardImages: true,
    defaultFormat: "commander",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentSearchCount, setRecentSearchCount] = useState(0);

  useEffect(() => {
    async function loadSettings(): Promise<void> {
      try {
        const [theme, showCardImages, defaultFormat, recentSearches] =
          await Promise.all([
            window.electronAPI.store.get<"dark" | "light" | "system">("theme"),
            window.electronAPI.store.get<boolean>("showCardImages"),
            window.electronAPI.store.get<string>("defaultFormat"),
            window.electronAPI.store.getRecentSearches(),
          ]);
        setSettings({
          theme: theme ?? "dark",
          showCardImages: showCardImages ?? true,
          defaultFormat: defaultFormat ?? "commander",
        });
        setRecentSearchCount(recentSearches?.length ?? 0);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load settings",
        );
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const updateSetting = useCallback(
    async <K extends keyof Settings>(key: K, value: Settings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
      await window.electronAPI.store.set(key, value);
    },
    [],
  );

  const handleClearSearches = useCallback(async () => {
    await window.electronAPI.store.clearRecentSearches();
    setRecentSearchCount(0);
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span style={{ color: colors.text.muted }}>Loading settings...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span style={{ color: colors.status.error }}>Error: {error}</span>
      </div>
    );
  }

  return (
    <div
      className="flex-1 p-6 overflow-auto"
      style={{ background: colors.void.deepest }}
    >
      <h1
        className="font-display text-2xl mb-6"
        style={{ color: colors.text.bright }}
      >
        Settings
      </h1>

      <div className="max-w-2xl space-y-8">
        {/* Appearance Section */}
        <section>
          <h2
            className="font-display text-lg mb-4"
            style={{ color: colors.gold.standard }}
          >
            Appearance
          </h2>

          <div className="space-y-4">
            {/* Theme selector */}
            <div
              className="flex items-center justify-between p-4 rounded"
              style={{
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div>
                <div style={{ color: colors.text.bright }}>Theme</div>
                <div className="text-sm" style={{ color: colors.text.muted }}>
                  Choose your preferred color scheme
                </div>
              </div>
              <select
                value={settings.theme}
                onChange={(e) =>
                  updateSetting("theme", e.target.value as Settings["theme"])
                }
                className="px-3 py-2 rounded cursor-pointer"
                style={{
                  background: colors.void.deepest,
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.bright,
                  outline: "none",
                }}
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="system">System</option>
              </select>
            </div>

            {/* Show card images toggle */}
            <div
              className="flex items-center justify-between p-4 rounded"
              style={{
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div>
                <div style={{ color: colors.text.bright }}>
                  Show Card Images
                </div>
                <div className="text-sm" style={{ color: colors.text.muted }}>
                  Display card artwork in search results and lists
                </div>
              </div>
              <button
                onClick={() =>
                  updateSetting("showCardImages", !settings.showCardImages)
                }
                className="w-12 h-6 rounded-full transition-colors relative cursor-pointer"
                style={{
                  background: settings.showCardImages
                    ? colors.gold.standard
                    : colors.void.deepest,
                  border: `1px solid ${colors.border.standard}`,
                }}
              >
                <span
                  className="absolute top-0.5 w-5 h-5 rounded-full transition-all"
                  style={{
                    background: colors.text.bright,
                    left: settings.showCardImages ? "calc(100% - 22px)" : "2px",
                  }}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Game Settings Section */}
        <section>
          <h2
            className="font-display text-lg mb-4"
            style={{ color: colors.gold.standard }}
          >
            Game Settings
          </h2>

          <div className="space-y-4">
            {/* Default format */}
            <div
              className="flex items-center justify-between p-4 rounded"
              style={{
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div>
                <div style={{ color: colors.text.bright }}>Default Format</div>
                <div className="text-sm" style={{ color: colors.text.muted }}>
                  Used for legality checks and deck building
                </div>
              </div>
              <select
                value={settings.defaultFormat}
                onChange={(e) => updateSetting("defaultFormat", e.target.value)}
                className="px-3 py-2 rounded cursor-pointer"
                style={{
                  background: colors.void.deepest,
                  border: `1px solid ${colors.border.standard}`,
                  color: colors.text.bright,
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
          </div>
        </section>

        {/* Data Section */}
        <section>
          <h2
            className="font-display text-lg mb-4"
            style={{ color: colors.gold.standard }}
          >
            Data
          </h2>

          <div className="space-y-4">
            {/* Clear recent searches */}
            <div
              className="flex items-center justify-between p-4 rounded"
              style={{
                background: colors.void.light,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div>
                <div style={{ color: colors.text.bright }}>Recent Searches</div>
                <div className="text-sm" style={{ color: colors.text.muted }}>
                  {recentSearchCount} saved searches
                </div>
              </div>
              <button
                onClick={handleClearSearches}
                disabled={recentSearchCount === 0}
                className="px-4 py-2 rounded font-display text-sm cursor-pointer disabled:cursor-not-allowed"
                style={{
                  background: "transparent",
                  border: `1px solid ${colors.border.standard}`,
                  color:
                    recentSearchCount === 0
                      ? colors.text.muted
                      : colors.text.standard,
                  opacity: recentSearchCount === 0 ? 0.5 : 1,
                }}
              >
                Clear
              </button>
            </div>
          </div>
        </section>

        {/* About Section */}
        <section>
          <h2
            className="font-display text-lg mb-4"
            style={{ color: colors.gold.standard }}
          >
            About
          </h2>

          <div
            className="p-4 rounded"
            style={{
              background: colors.void.light,
              border: `1px solid ${colors.border.subtle}`,
            }}
          >
            <div className="font-display" style={{ color: colors.text.bright }}>
              MTG Spellbook
            </div>
            <div className="text-sm mt-1" style={{ color: colors.text.muted }}>
              Version 0.1.0
            </div>
            <div className="text-sm mt-3" style={{ color: colors.text.muted }}>
              Card data provided by Scryfall and MTGJson.
              <br />
              Prices from TCGPlayer and Cardmarket.
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default SettingsScreen;
