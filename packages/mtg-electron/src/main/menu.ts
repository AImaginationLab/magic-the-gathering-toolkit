/**
 * Application menu configuration.
 * Creates native menus with keyboard shortcuts for macOS and other platforms.
 */
import { app, Menu, shell, BrowserWindow } from "electron";
import { is } from "@electron-toolkit/utils";

import type { MenuItemConstructorOptions } from "electron";

export function createApplicationMenu(mainWindow: BrowserWindow): void {
  const isMac = process.platform === "darwin";

  const template: MenuItemConstructorOptions[] = [
    // App menu (macOS only)
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              { role: "about" as const },
              { type: "separator" as const },
              {
                label: "Settings...",
                accelerator: "CmdOrCtrl+,",
                click: (): void =>
                  mainWindow.webContents.send("navigate", "settings"),
              },
              { type: "separator" as const },
              { role: "services" as const },
              { type: "separator" as const },
              { role: "hide" as const },
              { role: "hideOthers" as const },
              { role: "unhide" as const },
              { type: "separator" as const },
              { role: "quit" as const },
            ],
          } as MenuItemConstructorOptions,
        ]
      : []),

    // File menu
    {
      label: "File",
      submenu: [
        {
          label: "New Deck",
          accelerator: "CmdOrCtrl+N",
          click: (): void =>
            mainWindow.webContents.send("action", "new-deck"),
        },
        {
          label: "Import Collection...",
          accelerator: "CmdOrCtrl+I",
          click: (): void =>
            mainWindow.webContents.send("action", "import-collection"),
        },
        { type: "separator" as const },
        isMac
          ? { role: "close" as const }
          : { role: "quit" as const },
      ],
    },

    // Edit menu
    {
      label: "Edit",
      submenu: [
        { role: "undo" as const },
        { role: "redo" as const },
        { type: "separator" as const },
        { role: "cut" as const },
        { role: "copy" as const },
        { role: "paste" as const },
        { role: "delete" as const },
        { type: "separator" as const },
        { role: "selectAll" as const },
      ],
    },

    // View menu
    {
      label: "View",
      submenu: [
        {
          label: "Dashboard",
          accelerator: "CmdOrCtrl+1",
          click: (): void =>
            mainWindow.webContents.send("navigate", "dashboard"),
        },
        {
          label: "Search",
          accelerator: "CmdOrCtrl+2",
          click: (): void =>
            mainWindow.webContents.send("navigate", "search"),
        },
        {
          label: "Collection",
          accelerator: "CmdOrCtrl+3",
          click: (): void =>
            mainWindow.webContents.send("navigate", "collection"),
        },
        {
          label: "Decks",
          accelerator: "CmdOrCtrl+4",
          click: (): void =>
            mainWindow.webContents.send("navigate", "decks"),
        },
        {
          label: "Sets",
          accelerator: "CmdOrCtrl+5",
          click: (): void =>
            mainWindow.webContents.send("navigate", "sets"),
        },
        {
          label: "Synergies",
          accelerator: "CmdOrCtrl+6",
          click: (): void =>
            mainWindow.webContents.send("navigate", "synergies"),
        },
        {
          label: "Artists",
          accelerator: "CmdOrCtrl+7",
          click: (): void =>
            mainWindow.webContents.send("navigate", "artists"),
        },
        { type: "separator" as const },
        { role: "reload" as const },
        { role: "forceReload" as const },
        ...(is.dev ? [{ role: "toggleDevTools" as const }] : []),
        { type: "separator" as const },
        { role: "resetZoom" as const },
        { role: "zoomIn" as const },
        { role: "zoomOut" as const },
        { type: "separator" as const },
        { role: "togglefullscreen" as const },
      ],
    },

    // Go menu (navigation)
    {
      label: "Go",
      submenu: [
        {
          label: "Focus Search",
          accelerator: "CmdOrCtrl+K",
          click: (): void =>
            mainWindow.webContents.send("action", "focus-search"),
        },
        { type: "separator" as const },
        {
          label: "Back",
          accelerator: "CmdOrCtrl+[",
          click: (): void =>
            mainWindow.webContents.send("action", "go-back"),
        },
        {
          label: "Forward",
          accelerator: "CmdOrCtrl+]",
          click: (): void =>
            mainWindow.webContents.send("action", "go-forward"),
        },
      ],
    },

    // Window menu
    {
      label: "Window",
      submenu: [
        { role: "minimize" as const },
        { role: "zoom" as const },
        ...(isMac
          ? [
              { type: "separator" as const },
              { role: "front" as const },
              { type: "separator" as const },
              { role: "window" as const },
            ]
          : [{ role: "close" as const }]),
      ],
    },

    // Help menu
    {
      label: "Help",
      submenu: [
        {
          label: "MTG Spellbook Help",
          click: (): Promise<void> =>
            shell.openExternal(
              "https://github.com/your-repo/mtg-spellbook",
            ),
        },
        { type: "separator" as const },
        {
          label: "Scryfall",
          click: (): Promise<void> =>
            shell.openExternal("https://scryfall.com"),
        },
        {
          label: "EDHREC",
          click: (): Promise<void> =>
            shell.openExternal("https://edhrec.com"),
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}
