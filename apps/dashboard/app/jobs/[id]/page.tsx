"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getJob } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import LogStream from "@/components/LogStream";
import PreviewFrame from "@/components/PreviewFrame";
import ReportViewer from "@/components/ReportViewer";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  pending: "secondary",
  cloning: "secondary",
  planning: "secondary",
  executing: "default",
  resource_requested: "warning",
  preview_building: "default",
  browser_testing: "default",
  fixing_issues: "warning",
  completed: "success",
  partial_success: "warning",
  failed: "destructive",
  cancelled: "outline",
};

export default function JobDetailPage() {
  const { id } = useParams();
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    const fetchJob = () => {
      getJob(id as string)
        .then((data) => {
          setJob(data);
          setLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setLoading(false);
        });
    };

    fetchJob();
    const interval = setInterval(fetchJob, 3000);
    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl p-4 sm:p-6 space-y-4">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-muted rounded" />
          <div className="h-4 w-96 bg-muted rounded" />
          <div className="h-64 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-7xl p-4 sm:p-6">
        <h1 className="text-2xl font-bold">Job not found</h1>
        <p className="text-muted-foreground">The requested job does not exist.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Job Details</h1>
        <div className="flex gap-2 mt-2">
          <Badge variant={(STATUS_COLORS[job.status] as any) || "secondary"}>
            {job.status.replace(/_/g, " ")}
          </Badge>
          <span className="text-xs text-muted-foreground font-mono">{id}</span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Job Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <p className="text-xs text-muted-foreground">Repository</p>
              <a
                href={job.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline break-all"
              >
                {job.github_url}
              </a>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Prompt</p>
              <p className="text-sm">{job.prompt}</p>
            </div>
            {job.branch_name && (
              <div>
                <p className="text-xs text-muted-foreground">Branch</p>
                <p className="text-sm font-mono">{job.branch_name}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="text-sm">{new Date(job.created_at).toLocaleString()}</p>
            </div>
            {job.completed_at && (
              <div>
                <p className="text-xs text-muted-foreground">Completed</p>
                <p className="text-sm">{new Date(job.completed_at).toLocaleString()}</p>
              </div>
            )}
            {job.error_message && (
              <div>
                <p className="text-xs text-muted-foreground">Error</p>
                <p className="text-sm text-destructive">{job.error_message}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Options</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm">LLM Provider</span>
              <span className="text-sm font-medium">{job.options?.llm_provider || "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">Model</span>
              <span className="text-sm font-medium">
                {job.options?.llm_model || "Default"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">v0 Integration</span>
              <Badge variant={job.options?.enable_v0 ? "success" : "secondary"}>
                {job.options?.enable_v0 ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-sm">Cursor SDK</span>
              <Badge variant={job.options?.enable_cursor_sdk ? "success" : "secondary"}>
                {job.options?.enable_cursor_sdk ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {job.preview_url && (
        <PreviewFrame previewUrl={job.preview_url} />
      )}

      <LogStream jobId={id as string} />

      <ReportViewer jobId={id as string} />
    </div>
  );
}