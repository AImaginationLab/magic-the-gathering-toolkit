/**
 * Centralized logging configuration using electron-log.
 * Logs to both console and file with automatic rotation.
 */
import log from "electron-log/main";

// Configure log file location and rotation
log.transports.file.level = "info";
log.transports.file.maxSize = 5 * 1024 * 1024; // 5MB max file size
log.transports.console.level = "debug";

// Format: [timestamp] [level] message
log.transports.file.format = "[{y}-{m}-{d} {h}:{i}:{s}] [{level}] {text}";
log.transports.console.format = "[{h}:{i}:{s}] [{level}] {text}";

// Wrap console transport to catch EIO errors (can happen when stdout is in bad state)
const originalConsoleWriteFn = log.transports.console.writeFn;
if (originalConsoleWriteFn) {
  log.transports.console.writeFn = (message) => {
    try {
      originalConsoleWriteFn(message);
    } catch {
      // Silently ignore write errors (EIO, etc.)
    }
  };
}

// Initialize for main process
log.initialize();

// Export configured logger
export const logger = log;

// Convenience exports for common log levels
export const logInfo = log.info.bind(log);
export const logWarn = log.warn.bind(log);
export const logError = log.error.bind(log);
export const logDebug = log.debug.bind(log);

export default logger;
