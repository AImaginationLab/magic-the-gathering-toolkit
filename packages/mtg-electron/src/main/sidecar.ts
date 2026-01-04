/**
 * Sidecar Manager - Manages the Python mtg-api server lifecycle.
 *
 * Responsibilities:
 * - Spawn Python process on app startup using `uv run mtg-api`
 * - Health check polling until server is ready
 * - Graceful shutdown on app exit
 * - Auto-restart on crash with exponential backoff
 * - Log capture for debugging
 */

import { spawn, ChildProcess } from "child_process";
import { app } from "electron";
import path from "path";
import fs from "fs";
import { logger } from "./utils";

const DEFAULT_PORT = 8765;
const HEALTH_CHECK_INTERVAL_MS = 200;
const MAX_HEALTH_WAIT_MS = 10000;
const MAX_RESTARTS = 3;
const RESTART_BACKOFF_BASE_MS = 1000;

export type SidecarStatus = "stopped" | "starting" | "running" | "error";

export interface SidecarOptions {
  port?: number;
  host?: string;
  maxRestarts?: number;
  cwd?: string;
}

export class SidecarManager {
  private process: ChildProcess | null = null;
  private readonly port: number;
  private readonly host: string;
  private readonly maxRestarts: number;
  private readonly cwd: string | undefined;
  private restartCount = 0;
  private status: SidecarStatus = "stopped";
  private isShuttingDown = false;
  private isRestarting = false;

  constructor(options: SidecarOptions = {}) {
    this.port = options.port ?? DEFAULT_PORT;
    this.host = options.host ?? "127.0.0.1";
    this.maxRestarts = options.maxRestarts ?? MAX_RESTARTS;
    this.cwd = options.cwd;
  }

  /**
   * Start the Python sidecar process.
   * Spawns `uv run mtg-api` and waits for health check to pass.
   */
  async start(): Promise<void> {
    if (this.status === "running") {
      logger.debug("Sidecar already running");
      return;
    }

    this.isShuttingDown = false;
    this.status = "starting";
    logger.info(`Starting sidecar on ${this.host}:${this.port}...`);

    try {
      await this.spawnProcess();
      const healthy = await this.waitForHealth();

      if (!healthy) {
        throw new Error("Sidecar failed health check within timeout");
      }

      this.status = "running";
      this.restartCount = 0;
      logger.info("Sidecar is healthy and running");
    } catch (error) {
      this.status = "error";
      logger.error("Failed to start sidecar:", error);
      throw error;
    }
  }

  /**
   * Stop the sidecar process gracefully.
   */
  async stop(): Promise<void> {
    if (!this.process) {
      this.status = "stopped";
      return;
    }

    this.isShuttingDown = true;
    logger.info("Stopping sidecar...");

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        // Force kill if graceful shutdown takes too long
        if (this.process) {
          logger.warn("Sidecar did not exit gracefully, forcing kill");
          this.process.kill("SIGKILL");
        }
        this.cleanup();
        resolve();
      }, 5000);

      if (this.process) {
        this.process.once("exit", () => {
          clearTimeout(timeout);
          this.cleanup();
          resolve();
        });

        // Send SIGTERM for graceful shutdown
        this.process.kill("SIGTERM");
      } else {
        clearTimeout(timeout);
        this.cleanup();
        resolve();
      }
    });
  }

  /**
   * Get the base URL for API requests.
   */
  get baseUrl(): string {
    return `http://${this.host}:${this.port}`;
  }

  /**
   * Get the current status of the sidecar.
   */
  getStatus(): SidecarStatus {
    return this.status;
  }

  /**
   * Check if the sidecar is running and healthy.
   */
  isRunning(): boolean {
    return this.status === "running";
  }

  /**
   * Get the path to the bundled executable, if it exists.
   * With onedir mode, PyInstaller outputs: sidecar/mtg-api/mtg-api (folder containing exe)
   */
  private getBundledExecutablePath(): string | null {
    const exeName = process.platform === "win32" ? "mtg-api.exe" : "mtg-api";

    if (app.isPackaged) {
      // In packaged app, resources are in process.resourcesPath
      // onedir structure: sidecar/mtg-api/mtg-api
      return path.join(process.resourcesPath, "sidecar", "mtg-api", exeName);
    }

    // In dev, check local resources folder (won't exist unless you run build:sidecar)
    // onedir structure: resources/sidecar/mtg-api/mtg-api
    const devPath = path.join(
      __dirname,
      "../../resources/sidecar/mtg-api",
      exeName,
    );
    return fs.existsSync(devPath) ? devPath : null;
  }

  /**
   * Spawn the Python process.
   */
  private async spawnProcess(): Promise<void> {
    return new Promise((resolve, reject) => {
      let command: string;
      let args: string[];

      const bundledPath = this.getBundledExecutablePath();

      if (bundledPath && fs.existsSync(bundledPath)) {
        // Production: use bundled executable
        command = bundledPath;
        args = ["--host", this.host, "--port", String(this.port)];
        logger.info(`Using bundled sidecar: ${bundledPath}`);
      } else {
        // Development: use uv run
        command = "uv";
        args = [
          "run",
          "mtg-api",
          "--host",
          this.host,
          "--port",
          String(this.port),
        ];
        logger.info("Using development sidecar (uv run)");
      }

      logger.debug(`Spawning: ${command} ${args.join(" ")}`);

      this.process = spawn(command, args, {
        cwd: this.cwd,
        stdio: ["ignore", "pipe", "pipe"],
        // Ensure process is killed when parent exits
        detached: false,
      });

      // Capture stdout
      this.process.stdout?.on("data", (data: Buffer) => {
        const lines = data.toString().trim().split("\n");
        for (const line of lines) {
          logger.debug(`[mtg-api] ${line}`);
        }
      });

      // Capture stderr
      this.process.stderr?.on("data", (data: Buffer) => {
        const lines = data.toString().trim().split("\n");
        for (const line of lines) {
          // uvicorn logs to stderr by default, so not all stderr is errors
          if (line.toLowerCase().includes("error")) {
            logger.error(`[mtg-api] ${line}`);
          } else {
            logger.debug(`[mtg-api] ${line}`);
          }
        }
      });

      // Handle process exit
      this.process.on("exit", (code, signal) => {
        logger.info(`Sidecar exited with code ${code}, signal ${signal}`);
        this.process = null;

        if (!this.isShuttingDown && this.status === "running") {
          // Unexpected exit - attempt restart
          this.handleUnexpectedExit();
        }
      });

      // Handle spawn errors
      this.process.on("error", (error) => {
        logger.error("Failed to spawn sidecar:", error);
        this.process = null;
        this.status = "error";
        reject(error);
      });

      // Give the process a moment to fail on spawn errors
      setTimeout(() => {
        if (this.process) {
          resolve();
        }
      }, 100);
    });
  }

  /**
   * Wait for the health endpoint to respond.
   */
  private async waitForHealth(
    maxWaitMs = MAX_HEALTH_WAIT_MS,
  ): Promise<boolean> {
    const startTime = Date.now();
    const healthUrl = `${this.baseUrl}/health`;

    logger.debug(`Waiting for health check at ${healthUrl}...`);

    while (Date.now() - startTime < maxWaitMs) {
      try {
        const response = await fetch(healthUrl, {
          method: "GET",
          signal: AbortSignal.timeout(1000),
        });

        if (response.ok) {
          const data = await response.json();
          logger.debug("Health check passed:", data);
          return true;
        }
      } catch {
        // Expected while server is starting up
      }

      await this.sleep(HEALTH_CHECK_INTERVAL_MS);
    }

    logger.error(`Health check failed after ${maxWaitMs}ms`);
    return false;
  }

  /**
   * Handle unexpected process exit with restart logic.
   * Uses isRestarting flag to prevent concurrent restart attempts.
   */
  private async handleUnexpectedExit(): Promise<void> {
    if (this.isShuttingDown || this.isRestarting) {
      return;
    }

    this.isRestarting = true;

    try {
      this.restartCount++;
      logger.warn(
        `Sidecar exited unexpectedly (restart ${this.restartCount}/${this.maxRestarts})`,
      );

      if (this.restartCount > this.maxRestarts) {
        logger.error("Max restart attempts reached, giving up");
        this.status = "error";
        return;
      }

      // Exponential backoff
      const backoffMs =
        RESTART_BACKOFF_BASE_MS * Math.pow(2, this.restartCount - 1);
      logger.info(`Restarting sidecar in ${backoffMs}ms...`);

      await this.sleep(backoffMs);

      await this.start();
    } catch (error) {
      logger.error("Restart failed:", error);
    } finally {
      this.isRestarting = false;
    }
  }

  /**
   * Clean up process references.
   */
  private cleanup(): void {
    this.process = null;
    this.status = "stopped";
    logger.info("Sidecar stopped");
  }

  /**
   * Sleep helper.
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// Singleton instance for the application
let sidecarInstance: SidecarManager | null = null;

/**
 * Get the singleton sidecar manager instance.
 */
export function getSidecar(): SidecarManager {
  if (!sidecarInstance) {
    sidecarInstance = new SidecarManager();
  }
  return sidecarInstance;
}

/**
 * Create a new sidecar manager with custom options.
 * This replaces the singleton instance.
 */
export function createSidecar(options: SidecarOptions): SidecarManager {
  sidecarInstance = new SidecarManager(options);
  return sidecarInstance;
}
