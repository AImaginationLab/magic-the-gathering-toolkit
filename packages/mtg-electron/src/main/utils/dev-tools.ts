/**
 * Development-only utilities.
 * Only loaded when running in dev mode.
 */
import { is } from "@electron-toolkit/utils";
import { logger } from "./logger";

/**
 * Initialize development tools.
 * Call this early in app startup, but only in dev mode.
 */
export async function initDevTools(): Promise<void> {
  if (!is.dev) {
    return;
  }

  logger.info("Initializing development tools...");

  // Enable electron-debug (F12 for DevTools, Ctrl+R reload)
  try {
    const debug = await import("electron-debug");
    debug.default({ showDevTools: false }); // Don't auto-open DevTools
    logger.debug("electron-debug initialized");
  } catch (error) {
    logger.warn("Failed to initialize electron-debug:", error);
  }

  // Install React DevTools
  // Note: Known issue - may need page reload to appear (electron/electron#41613)
  try {
    const { default: installExtension, REACT_DEVELOPER_TOOLS } = await import(
      "electron-devtools-installer"
    );
    const result = await installExtension(REACT_DEVELOPER_TOOLS, {
      loadExtensionOptions: { allowFileAccess: true },
      forceDownload: false,
    });
    logger.debug(
      `Installed DevTools extension: ${typeof result === "string" ? result : result?.name || "React DevTools"}`,
    );
    logger.info(
      "React DevTools installed - if not visible, reload page (Cmd+R)",
    );
  } catch (error) {
    logger.warn("Failed to install React DevTools:", error);
  }

  // Enable hot reload for main process
  // Note: electron-reloader requires CommonJS `module` which doesn't exist in ESM
  // Skip it entirely in ESM mode - Vite handles HMR for renderer anyway
  if (typeof module !== "undefined") {
    try {
      const reloader = await import("electron-reloader");
      reloader.default(module, {
        debug: false,
        watchRenderer: false, // Vite handles renderer HMR
      });
      logger.debug("electron-reloader initialized");
    } catch (error) {
      logger.warn("Failed to initialize electron-reloader:", error);
    }
  } else {
    logger.debug("electron-reloader: ESM mode, skipping (module not defined)");
  }

  logger.info("Development tools ready");
}

export default initDevTools;
