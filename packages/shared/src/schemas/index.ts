import { z } from "zod";
import {
  JobStatus,
  ResourceType,
  ResourceTier,
  ResourceStatus,
  LLMProvider,
  BrowserInspectionStatus,
  PreviewStatus,
  FrontendFramework,
} from "../types";

// Control Panel -> Coding Agent
export const CreateJobSchema = z.object({
  github_url: z.string().url(),
  plan_md_url: z.string().url().optional(),
  prompt: z.string().min(1),
  options: z.object({
    enable_v0: z.boolean().default(false),
    enable_cursor_sdk: z.boolean().default(false),
    llm_provider: z.nativeEnum(LLMProvider).default(LLMProvider.ANTHROPIC),
    llm_model: z.string().optional(),
  }).default({}),
});

export type CreateJobRequest = z.infer<typeof CreateJobSchema>;

export const JobSchema = z.object({
  id: z.string().uuid(),
  status: z.nativeEnum(JobStatus),
  github_url: z.string().url(),
  plan_md_url: z.string().url().optional(),
  prompt: z.string(),
  options: z.object({
    enable_v0: z.boolean(),
    enable_cursor_sdk: z.boolean(),
    llm_provider: z.nativeEnum(LLMProvider),
    llm_model: z.string().optional(),
  }),
  branch_name: z.string().optional(),
  repo_clone_path: z.string().optional(),
  preview_url: z.string().url().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  completed_at: z.string().datetime().optional(),
  error_message: z.string().optional(),
  logs: z.array(z.object({
    timestamp: z.string().datetime(),
    level: z.enum(["info", "warn", "error", "debug"]),
    message: z.string(),
    source: z.string(),
  })).optional(),
});

export type Job = z.infer<typeof JobSchema>;

// Resource Request
export const ResourceRequestSchema = z.object({
  id: z.string().uuid(),
  job_id: z.string().uuid(),
  requested: z.array(z.object({
    type: z.nativeEnum(ResourceType),
    tier: z.nativeEnum(ResourceTier).default(ResourceTier.SMALL),
    region: z.string().optional(),
    name: z.string().optional(),
  })),
  status: z.nativeEnum(ResourceStatus).default(ResourceStatus.PENDING),
  config: z.record(z.string()).optional(),
  env_vars: z.record(z.string()).optional(),
  created_at: z.string().datetime(),
  resolved_at: z.string().datetime().optional(),
});

export type ResourceRequest = z.infer<typeof ResourceRequestSchema>;

// Preview Build
export const PreviewBuildSchema = z.object({
  id: z.string().uuid(),
  job_id: z.string().uuid(),
  status: z.nativeEnum(PreviewStatus),
  framework: z.nativeEnum(FrontendFramework),
  build_log: z.string().optional(),
  url: z.string().url().optional(),
  container_id: z.string().optional(),
  port: z.number().optional(),
  created_at: z.string().datetime(),
  expires_at: z.string().datetime(),
});

export type PreviewBuild = z.infer<typeof PreviewBuildSchema>;

// Browser Inspection Report
export const BrowserInspectionReportSchema = z.object({
  id: z.string().uuid(),
  job_id: z.string().uuid(),
  preview_id: z.string().uuid(),
  status: z.nativeEnum(BrowserInspectionStatus),
  summary: z.string(),
  issues: z.array(z.object({
    severity: z.enum(["error", "warning", "info"]),
    category: z.enum(["console", "visual", "accessibility", "performance", "layout"]),
    message: z.string(),
    details: z.string().optional(),
    screenshot_url: z.string().optional(),
    element_selector: z.string().optional(),
    url: z.string().optional(),
    line: z.number().optional(),
  })).default([]),
  console_errors: z.array(z.object({
    level: z.enum(["error", "warning", "info", "log"]),
    message: z.string(),
    source: z.string().optional(),
    line: z.number().optional(),
    timestamp: z.string().datetime(),
  })).default([]),
  screenshots: z.array(z.object({
    type: z.enum(["full_page", "viewport", "element"]),
    url: z.string(),
    path: z.string(),
    width: z.number(),
    height: z.number(),
  })).default([]),
  performance_metrics: z.object({
    load_time_ms: z.number().optional(),
    dom_content_loaded_ms: z.number().optional(),
    first_paint_ms: z.number().optional(),
    first_contentful_paint_ms: z.number().optional(),
  }).optional(),
  created_at: z.string().datetime(),
});

export type BrowserInspectionReport = z.infer<typeof BrowserInspectionReportSchema>;

// Final Report (Coding Agent -> Control Panel)
export const CompletionReportSchema = z.object({
  job_id: z.string().uuid(),
  status: z.enum(["success", "partial_success", "failed"]),
  summary: z.string(),
  changes: z.array(z.object({
    type: z.enum(["created", "modified", "deleted", "renamed"]),
    file: z.string(),
    description: z.string().optional(),
  })),
  preview_url: z.string().url().optional(),
  screenshots: z.array(z.object({
    type: z.enum(["full_page", "viewport"]),
    url: z.string(),
    path: z.string(),
  })).optional(),
  browser_report_summary: z.string().optional(),
  resource_summary: z.string().optional(),
  artifacts_s3_prefix: z.string().optional(),
  duration_seconds: z.number(),
  completed_at: z.string().datetime(),
});

export type CompletionReport = z.infer<typeof CompletionReportSchema>;

// WebSocket Events
export const LogEntrySchema = z.object({
  timestamp: z.string().datetime(),
  level: z.enum(["info", "warn", "error", "debug"]),
  message: z.string(),
  source: z.string(),
  job_id: z.string().uuid(),
});

export type LogEntry = z.infer<typeof LogEntrySchema>;

export const JobStatusUpdateSchema = z.object({
  job_id: z.string().uuid(),
  status: z.nativeEnum(JobStatus),
  message: z.string().optional(),
  timestamp: z.string().datetime(),
});

export type JobStatusUpdate = z.infer<typeof JobStatusUpdateSchema>;