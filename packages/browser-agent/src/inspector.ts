import { chromium, type Browser, type Page } from "playwright";
import type {
  InspectorConfig,
  InspectionResult,
  ScreenshotInfo,
  ConsoleEntry,
  Issue,
  PerformanceMetrics,
} from "./types";

const DEFAULT_CONFIG: Required<InspectorConfig> = {
  screenshotDir: "./screenshots",
  maxWaitTimeMs: 30000,
  viewportWidth: 1440,
  viewportHeight: 900,
  captureFullPage: true,
  checkAccessibility: true,
  ignoreConsoleErrors: [],
  maxIssuesToReport: 50,
};

export class BrowserInspector {
  private config: Required<InspectorConfig>;
  private browser: Browser | null = null;
  private consoleEntries: ConsoleEntry[] = [];
  private issues: Issue[] = [];
  private screenshots: ScreenshotInfo[] = [];

  constructor(config: InspectorConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  async launch(): Promise<void> {
    this.browser = await chromium.launch({ headless: true });
    consoleEntries = [];
    issues = [];
    screenshots = [];
  }

  async inspect(url: string): Promise<InspectionResult> {
    if (!this.browser) {
      await this.launch();
    }

    const context = await this.browser!.newContext({
      viewport: {
        width: this.config.viewportWidth,
        height: this.config.viewportHeight,
      },
    });

    const page = await context.newPage();

    const navigationStart = Date.now();
    const metrics: PerformanceMetrics = {};

    page.on("console", (msg) => {
      const entry: ConsoleEntry = {
        level: msg.type() as ConsoleEntry["level"],
        message: msg.text(),
        source: msg.location().url || undefined,
        line: msg.location().lineNumber || undefined,
        timestamp: new Date().toISOString(),
      };

      if (
        (msg.type() === "error" || msg.type() === "warning") &&
        !this.config.ignoreConsoleErrors.some((p) => msg.text().includes(p))
      ) {
        issues.push({
          severity: msg.type() === "error" ? "error" : "warning",
          category: "console",
          message: msg.text(),
          source: msg.location().url || undefined,
          line: msg.location().lineNumber || undefined,
          url: page.url(),
        });
      }

      this.consoleEntries.push(entry);
    });

    page.on("pageerror", (error) => {
      issues.push({
        severity: "error",
        category: "console",
        message: error.message,
        url: page.url(),
      });
    });

    try {
      await page.goto(url, {
        waitUntil: "networkidle",
        timeout: this.config.maxWaitTimeMs,
      });

      metrics.load_time_ms = Date.now() - navigationStart;

      metrics.dom_content_loaded_ms = Date.now() - navigationStart;

      await page.waitForTimeout(2000);

      const fullPageScreenshot = await this.captureScreenshot(
        page,
        "full_page",
        this.config.captureFullPage
      );
      if (fullPageScreenshot) {
        this.screenshots.push(fullPageScreenshot);
      }

      const viewportScreenshot = await this.captureScreenshot(page, "viewport", false);
      if (viewportScreenshot) {
        this.screenshots.push(viewportScreenshot);
      }

      if (this.config.checkAccessibility) {
        await this.checkAccessibility(page);
      }

      await this.checkCommonVisualIssues(page);

      try {
        const paintTiming = await page.evaluate(() => {
          const nav = performance.getEntriesByType(
            "navigation"
          )[0] as PerformanceNavigationTiming;
          const paint = performance.getEntriesByType("paint");
          const fcp = paint.find((e) => e.name === "first-contentful-paint");
          const fp = paint.find((e) => e.name === "first-paint");
          return {
            first_paint_ms: fp ? Math.round(fp.startTime) : undefined,
            first_contentful_paint_ms: fcp ? Math.round(fcp.startTime) : undefined,
          };
        });
        metrics.first_paint_ms = paintTiming.first_paint_ms;
        metrics.first_contentful_paint_ms = paintTiming.first_contentful_paint_ms;
      } catch {
        // Performance API might not be available
      }
    } catch (error: any) {
      issues.push({
        severity: "error",
        category: "performance",
        message: `Page load failed: ${error.message}`,
        url,
      });
    } finally {
      await context.close();
    }

    // Limit issues
    const cappedIssues = issues.slice(0, this.config.maxIssuesToReport);
    const errorCount = cappedIssues.filter((i) => i.severity === "error").length;
    const warningCount = cappedIssues.filter((i) => i.severity === "warning").length;

    let status: InspectionResult["status"] = "passed";
    if (errorCount > 0) status = "failed";
    else if (warningCount > 3) status = "warning";

    const summaryParts: string[] = [];
    if (errorCount > 0) summaryParts.push(`${errorCount} error(s)`);
    if (warningCount > 0) summaryParts.push(`${warningCount} warning(s)`);
    const infoCount = cappedIssues.filter((i) => i.severity === "info").length;
    if (infoCount > 0) summaryParts.push(`${infoCount} info(s)`);
    summaryParts.push(
      `${this.consoleEntries.length} console message(s)`,
      `${this.screenshots.length} screenshot(s)`
    );

    return {
      status,
      summary: `Inspection ${status}: ${summaryParts.join(", ")}`,
      issues: cappedIssues,
      consoleErrors: consoleEntries,
      screenshots,
      performanceMetrics: metrics,
    };
  }

  private async captureScreenshot(
    page: Page,
    type: ScreenshotInfo["type"],
    fullPage: boolean
  ): Promise<ScreenshotInfo | null> {
    try {
      const buffer = await page.screenshot({ fullPage });
      const base64 = buffer.toString("base64");
      return {
        type,
        url: `data:image/png;base64,${base64}`,
        path: `${this.config.screenshotDir}/${type}_${Date.now()}.png`,
        width: fullPage ? await page.evaluate(() => document.body.scrollWidth) : this.config.viewportWidth,
        height: fullPage ? await page.evaluate(() => document.body.scrollHeight) : this.config.viewportHeight,
      };
    } catch {
      return null;
    }
  }

  private async checkAccessibility(page: Page): Promise<void> {
    try {
      const violations = await page.evaluate(() => {
        const issues: Array<{
          message: string;
          selector: string;
        }> = [];
        const images = document.querySelectorAll("img:not([alt])");
        images.forEach((img) => {
          issues.push({
            message: `Image missing alt attribute: ${(img as HTMLImageElement).src || "unknown"}`,
            selector: img.tagName,
          });
        });

        const inputs = document.querySelectorAll("input:not([aria-label]):not([aria-labelledby])");
        inputs.forEach((input) => {
          const hasLabel =
            (input as HTMLInputElement).labels?.length > 0 ||
            input.closest("label") !== null;
          if (!hasLabel) {
            issues.push({
              message: `Input missing label: ${(input as HTMLInputElement).name || "unnamed"}`,
              selector: `input[name="${(input as HTMLInputElement).name || ""}"]`,
            });
          }
        });

        return issues;
      });

      violations.forEach((v) => {
        issues.push({
          severity: "warning",
          category: "accessibility",
          message: v.message,
          element_selector: v.selector,
          url: page.url(),
        });
      });
    } catch {
      // Accessibility checks are best-effort without axe-core
    }
  }

  private async checkCommonVisualIssues(page: Page): Promise<void> {
    try {
      const issues_found = await page.evaluate(() => {
        const issues: Array<{
          message: string;
          selector: string;
        }> = [];
        const body = document.body;
        const style = window.getComputedStyle(body);
        const overflowHidden = style.overflow === "hidden";

        if (!overflowHidden) {
          const bodyHeight = body.scrollHeight;
          const viewportHeight = window.innerHeight;
          if (bodyHeight <= viewportHeight * 0.1) {
            issues.push({
              message: "Body content height is very small - page may be empty",
              selector: "body",
            });
          }
        }

        const bodyText = body.innerText?.trim() || "";
        if (bodyText.length < 10) {
          issues.push({
            message: "Very little text content detected",
            selector: "body",
          });
        }

        const allTexts = Array.from(document.querySelectorAll("*"))
          .map((el) => (el as HTMLElement).innerText)
          .filter((t) => t?.includes("404") || t?.includes("Not Found"));
        if (allTexts.length > 0) {
          issues.push({
            message: "Possible 404 error page detected",
            selector: "body",
          });
        }

        return issues;
      });

      issues_found.forEach((v) => {
        issues.push({
          severity: "info",
          category: "visual",
          message: v.message,
          element_selector: v.selector,
          url: page.url(),
        });
      });
    } catch {
      // Best-effort visual checks
    }
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }
}