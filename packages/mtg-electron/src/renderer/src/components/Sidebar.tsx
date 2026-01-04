import { useState } from "react";

import { colors } from "../theme";

import type { ReactNode } from "react";

export type Screen =
  | "dashboard"
  | "search"
  | "artists"
  | "sets"
  | "decks"
  | "collection"
  | "synergies"
  | "suggestions"
  | "settings"
  | "gallery";

interface NavItem {
  id: Screen;
  label: string;
  manaSymbol: string;
  shortcut: string;
  accentColor: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "dashboard",
    label: "Home",
    manaSymbol: "c",
    shortcut: "Esc",
    accentColor: colors.gold.standard,
  },
  {
    id: "search",
    label: "Search",
    manaSymbol: "u",
    shortcut: "/",
    accentColor: colors.mana.blue.color,
  },
  {
    id: "synergies",
    label: "Synergies",
    manaSymbol: "b",
    shortcut: "Y",
    accentColor: "#ba68c8",
  },
  {
    id: "suggestions",
    label: "Suggestions",
    manaSymbol: "w",
    shortcut: "G",
    accentColor: "#4dd0e1",
  },
  {
    id: "artists",
    label: "Artists",
    manaSymbol: "w",
    shortcut: "A",
    accentColor: colors.mana.white.color,
  },
  {
    id: "sets",
    label: "Sets",
    manaSymbol: "u",
    shortcut: "S",
    accentColor: colors.mana.blue.color,
  },
  {
    id: "decks",
    label: "Decks",
    manaSymbol: "r",
    shortcut: "D",
    accentColor: colors.mana.red.color,
  },
  {
    id: "collection",
    label: "Collection",
    manaSymbol: "g",
    shortcut: "C",
    accentColor: colors.mana.green.color,
  },
];

interface SidebarProps {
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
  isCollapsed?: boolean;
}

export function Sidebar({
  currentScreen,
  onNavigate,
  isCollapsed = false,
}: SidebarProps): ReactNode {
  const [hoveredItem, setHoveredItem] = useState<Screen | null>(null);

  return (
    <aside
      className="h-full flex flex-col transition-all duration-300 relative"
      style={{
        width: isCollapsed ? "56px" : "180px",
        background: colors.void.deep,
        borderRight: `1px solid ${colors.border.subtle}`,
      }}
    >
      {/* Logo area */}
      <div
        className="p-4 border-b app-drag"
        style={{ borderColor: colors.border.subtle }}
      >
        <div className="flex items-center gap-3">
          {/* Planeswalker-style icon using tap symbol */}
          <div
            className="w-8 h-8 rounded flex items-center justify-center"
            style={{
              background: colors.void.medium,
              border: `1px solid ${colors.gold.dim}`,
            }}
          >
            <i
              className="ms ms-planeswalker"
              style={{ color: colors.gold.standard, fontSize: "16px" }}
            />
          </div>
          {!isCollapsed && (
            <div
              className="font-display text-sm tracking-widest"
              style={{ color: colors.gold.standard }}
            >
              MTG
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2">
        {NAV_ITEMS.map((item) => {
          const isActive = currentScreen === item.id;
          const isHovered = hoveredItem === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              onMouseEnter={() => setHoveredItem(item.id)}
              onMouseLeave={() => setHoveredItem(null)}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 mb-0.5 rounded
                transition-all duration-150 cursor-pointer relative
                ${isCollapsed ? "justify-center" : ""}
              `}
              style={{
                background: isActive
                  ? `${colors.void.lighter}`
                  : isHovered
                    ? `${colors.void.light}`
                    : "transparent",
              }}
              title={
                isCollapsed ? `${item.label} (${item.shortcut})` : undefined
              }
            >
              {/* Active indicator */}
              {isActive && (
                <div
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
                  style={{
                    background: item.accentColor,
                    boxShadow: `0 0 6px ${item.accentColor}`,
                  }}
                />
              )}

              {/* Mana symbol icon */}
              <i
                className={`ms ms-${item.manaSymbol} ms-cost`}
                style={{
                  color: isActive
                    ? item.accentColor
                    : isHovered
                      ? colors.gold.standard
                      : colors.text.muted,
                  fontSize: "14px",
                  transition: "color 0.15s",
                }}
              />

              {!isCollapsed && (
                <>
                  {/* Label */}
                  <span
                    className="flex-1 text-left text-sm tracking-wide transition-colors duration-150"
                    style={{
                      color: isActive
                        ? colors.text.bright
                        : isHovered
                          ? colors.text.standard
                          : colors.text.dim,
                    }}
                  >
                    {item.label}
                  </span>

                  {/* Shortcut key */}
                  <span
                    className="text-xs font-mono px-1.5 py-0.5 rounded transition-all duration-150"
                    style={{
                      color: isActive ? item.accentColor : colors.text.muted,
                      background:
                        isActive || isHovered
                          ? colors.void.medium
                          : "transparent",
                    }}
                  >
                    {item.shortcut}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Separator */}
      <div className="px-4 py-2">
        <div className="h-px" style={{ background: colors.border.subtle }} />
      </div>

      {/* Random card button */}
      <div className="p-2 pb-1">
        <button
          className={`
            w-full flex items-center gap-3 px-3 py-2.5 rounded
            transition-all duration-150 relative
            ${isCollapsed ? "justify-center" : ""}
          `}
          style={{
            background: colors.void.light,
            border: `1px solid ${colors.border.standard}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = colors.rarity.mythic.color;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = colors.border.standard;
          }}
          title={isCollapsed ? "Random Card (R)" : undefined}
        >
          <i
            className="ms ms-instant"
            style={{ color: colors.rarity.mythic.color, fontSize: "14px" }}
          />
          {!isCollapsed && (
            <>
              <span
                className="flex-1 text-left text-sm tracking-wide"
                style={{ color: colors.text.dim }}
              >
                Random
              </span>
              <span
                className="text-xs font-mono px-1.5 py-0.5 rounded"
                style={{
                  color: colors.rarity.mythic.color,
                  background: colors.void.medium,
                }}
              >
                R
              </span>
            </>
          )}
        </button>
      </div>

      {/* Settings button */}
      <div className="px-2 pb-3">
        <button
          onClick={() => onNavigate("settings")}
          className={`
            w-full flex items-center gap-3 px-3 py-2.5 rounded
            transition-all duration-150 relative cursor-pointer
            ${isCollapsed ? "justify-center" : ""}
          `}
          style={{
            background:
              currentScreen === "settings"
                ? colors.void.lighter
                : "transparent",
          }}
          onMouseEnter={(e) => {
            if (currentScreen !== "settings") {
              e.currentTarget.style.background = colors.void.light;
            }
          }}
          onMouseLeave={(e) => {
            if (currentScreen !== "settings") {
              e.currentTarget.style.background = "transparent";
            }
          }}
          title={isCollapsed ? "Settings (,)" : undefined}
        >
          {currentScreen === "settings" && (
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r"
              style={{
                background: colors.gold.standard,
                boxShadow: `0 0 6px ${colors.gold.glow}`,
              }}
            />
          )}
          <i
            className="ms ms-artifact"
            style={{
              color:
                currentScreen === "settings"
                  ? colors.gold.standard
                  : colors.text.muted,
              fontSize: "14px",
              transition: "color 0.15s",
            }}
          />
          {!isCollapsed && (
            <>
              <span
                className="flex-1 text-left text-sm tracking-wide transition-colors duration-150"
                style={{
                  color:
                    currentScreen === "settings"
                      ? colors.text.bright
                      : colors.text.dim,
                }}
              >
                Settings
              </span>
              <span
                className="text-xs font-mono px-1.5 py-0.5 rounded transition-all duration-150"
                style={{
                  color:
                    currentScreen === "settings"
                      ? colors.gold.standard
                      : colors.text.muted,
                  background:
                    currentScreen === "settings"
                      ? colors.void.medium
                      : "transparent",
                }}
              >
                ,
              </span>
            </>
          )}
        </button>
      </div>

      {/* Collapse hint */}
      {!isCollapsed && (
        <div
          className="px-4 pb-3 text-center text-xs font-body"
          style={{ color: colors.text.muted }}
        >
          <span className="font-mono" style={{ color: colors.gold.dim }}>
            [
          </span>{" "}
          to collapse
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
