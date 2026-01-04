import { useCallback, useEffect, useState } from "react";

import { colors } from "../theme";
import Sidebar from "./Sidebar";
import StatusBar from "./StatusBar";

import type { ReactNode } from "react";
import type { Screen } from "./Sidebar";
import type { ApiStatus } from "./StatusBar";

interface AppShellProps {
  children: ReactNode;
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
  apiStatus: ApiStatus;
  cardCount: number;
  setCount: number;
  collectionCount: number;
  collectionValue: number;
}

export function AppShell({
  children,
  currentScreen,
  onNavigate,
  apiStatus,
  cardCount,
  setCount,
  collectionCount,
  collectionValue,
}: AppShellProps): ReactNode {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent): void => {
      // Don't trigger if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        // Allow Escape to work even in inputs
        if (e.key !== "Escape") return;
      }

      switch (e.key.toLowerCase()) {
        case "escape":
          onNavigate("dashboard");
          break;
        case "/":
          e.preventDefault();
          onNavigate("search");
          break;
        case "a":
          onNavigate("artists");
          break;
        case "s":
          onNavigate("sets");
          break;
        case "d":
          onNavigate("decks");
          break;
        case "c":
          onNavigate("collection");
          break;
        case "y":
          onNavigate("synergies");
          break;
        case "g":
          onNavigate("suggestions");
          break;
        case ",":
          onNavigate("settings");
          break;
        case "r":
          // TODO: random card
          break;
        case "[":
          setIsSidebarCollapsed((prev) => !prev);
          break;
      }
    },
    [onNavigate],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return (): void => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{ backgroundColor: colors.void.deepest }}
    >
      {/* Minimal header - just for window controls */}
      <header
        className="h-9 flex items-center px-4 app-drag"
        style={{
          background: colors.void.deep,
          borderBottom: `1px solid ${colors.border.subtle}`,
        }}
      >
        {/* macOS traffic lights space */}
        <div className="w-16" />

        {/* Centered title */}
        <div className="flex-1 flex items-center justify-center">
          <span
            className="font-display text-xs tracking-[0.2em] uppercase"
            style={{ color: colors.text.muted }}
          >
            Spellbook
          </span>
        </div>

        {/* API status indicator - only show when not ready */}
        <div className="w-16 flex justify-end">
          {apiStatus !== "ready" && (
            <div
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor:
                  apiStatus === "starting"
                    ? colors.status.warning
                    : colors.status.error,
              }}
              title={
                apiStatus === "starting" ? "API Starting..." : "API Offline"
              }
            />
          )}
        </div>
      </header>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          currentScreen={currentScreen}
          onNavigate={onNavigate}
          isCollapsed={isSidebarCollapsed}
        />

        <main
          className="flex-1 overflow-auto"
          style={{ backgroundColor: colors.void.deepest }}
        >
          {children}
        </main>
      </div>

      {/* Status bar */}
      <StatusBar
        cardCount={cardCount}
        setCount={setCount}
        collectionCount={collectionCount}
        collectionValue={collectionValue}
        apiStatus={apiStatus}
      />
    </div>
  );
}

export default AppShell;
