const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export interface CreateJobPayload {
  github_url: string;
  prompt: string;
  plan_md_url?: string;
  options?: Record<string, unknown>;
}

export interface Job {
  id: string;
  status: string;
  github_url: string;
  prompt: string;
  created_at: string;
  updated_at: string;
  plan_md_url?: string;
  options?: Record<string, unknown>;
}

export interface JobListParams {
  status?: string;
  page?: number;
  limit?: number;
}

export interface PreviewData {
  url: string;
  ready: boolean;
}

export interface BrowserReport {
  issues: BrowserIssue[];
  screenshots: string[];
  performance: PerformanceMetrics;
}

export interface BrowserIssue {
  severity: "critical" | "high" | "medium" | "low";
  message: string;
  element?: string;
}

export interface PerformanceMetrics {
  fcp: number;
  lcp: number;
  tbt: number;
  cls: number;
  score: number;
}

export interface CompletionReport {
  summary: string;
  files_changed: FileChange[];
  errors: string[];
}

export interface FileChange {
  path: string;
  action: "created" | "modified" | "deleted";
  diff?: string;
}

export function createJob(data: CreateJobPayload): Promise<Job> {
  return fetchApi<Job>("/v1/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listJobs(params?: JobListParams): Promise<Job[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  return fetchApi<Job[]>(`/v1/jobs?${searchParams.toString()}`);
}

export function getJob(jobId: string): Promise<Job> {
  return fetchApi<Job>(`/v1/jobs/${jobId}`);
}

export function cancelJob(jobId: string): Promise<void> {
  return fetchApi<void>(`/v1/jobs/${jobId}`, { method: "DELETE" });
}

export function getPreview(jobId: string): Promise<PreviewData> {
  return fetchApi<PreviewData>(`/v1/jobs/${jobId}/preview`);
}

export function getBrowserReport(jobId: string): Promise<BrowserReport> {
  return fetchApi<BrowserReport>(`/v1/jobs/${jobId}/reports/browser`);
}

export function getCompletionReport(jobId: string): Promise<CompletionReport> {
  return fetchApi<CompletionReport>(`/v1/jobs/${jobId}/reports/completion`);
}