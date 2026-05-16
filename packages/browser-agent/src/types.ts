import type { ScreenshotInfo, ConsoleEntry, Issue, InspectionResult } from "./types";

export interface ScreenshotInfo {
  type: "full_page" | "viewport" | "element";
  url: string;
  path: string;
  width: number;
  height: number;
}

export interface ConsoleEntry {
  level: "error" | "warning" | "info" | "log";
  message: string;
  source?: string;
  line?: number;
  timestamp: string;
}

export interface Issue {
  severity: "error" | "warning" | "info";
  category: "console" | "visual" | "accessibility" | "performance" | "layout";
  message: string;
  details?: string;
  screenshot_url?: string;
  element_selector?: string;
  url?: string;
  line?: number;
}

export interface PerformanceMetrics {
  load_time_ms?: number;
  dom_content_loaded_ms?: number;
  first_paint_ms?: number;
  first_contentful_paint_ms?: number;
}

export interface InspectionResult {
  status: "passed" | "failed" | "warning";
  summary: string;
  issues: Issue[];
  consoleErrors: ConsoleEntry[];
  screenshots: ScreenshotInfo[];
  performanceMetrics?: PerformanceMetrics;
}

export interface InspectorConfig {
  screenshotDir?: string;
  maxWaitTimeMs?: number;
  viewportWidth?: number;
  viewportHeight?: number;
  captureFullPage?: boolean;
  checkAccessibility?: boolean;
  ignoreConsoleErrors?: string[];
  maxIssuesToReport?: number;
}