"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  BrowserReport,
  BrowserIssue,
  PerformanceMetrics,
  CompletionReport,
  FileChange,
} from "@/lib/api";

interface ReportViewerProps {
  browserReport?: BrowserReport | null;
  completionReport?: CompletionReport | null;
  jobStatus: string;
}

function SeverityIcon({ severity }: { severity: BrowserIssue["severity"] }) {
  const colors: Record<string, string> = {
    critical: "text-red-500",
    high: "text-orange-500",
    medium: "text-yellow-500",
    low: "text-blue-500",
  };

  const labels: Record<string, string> = {
    critical: "Critical",
    high: "High",
    medium: "Medium",
    low: "Low",
  };

  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${colors[severity]}`}>
      <span className="inline-block h-2 w-2 rounded-full bg-current" />
      {labels[severity]}
    </span>
  );
}

function PerformanceCard({ metrics }: { metrics: PerformanceMetrics }) {
  const items = [
    { label: "First Contentful Paint", value: `${(metrics.fcp / 1000).toFixed(1)}s`, key: "fcp" },
    { label: "Largest Contentful Paint", value: `${(metrics.lcp / 1000).toFixed(1)}s`, key: "lcp" },
    { label: "Total Blocking Time", value: `${metrics.tbt}ms`, key: "tbt" },
    { label: "Cumulative Layout Shift", value: metrics.cls.toFixed(3), key: "cls" },
  ];

  const scoreColor = metrics.score >= 90 ? "text-green-500" : metrics.score >= 50 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Performance Score</h4>
        <span className={`text-2xl font-bold ${scoreColor}`}>{metrics.score}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => (
          <div key={item.key} className="rounded-md bg-muted/50 p-3">
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-semibold">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function FileChangeList({ files }: { files: FileChange[] }) {
  const actionColors: Record<string, string> = {
    created: "text-green-400",
    modified: "text-yellow-400",
    deleted: "text-red-400",
  };

  const actionIcons: Record<string, string> = {
    created: "A",
    modified: "M",
    deleted: "D",
  };

  return (
    <div className="space-y-1">
      {files.map((file, i) => (
        <div
          key={i}
          className="flex items-center gap-2 rounded px-2 py-1 font-mono text-xs hover:bg-muted/50"
        >
          <span className={`w-4 text-center font-bold ${actionColors[file.action] || "text-muted-foreground"}`}>
            {actionIcons[file.action] || "?"}
          </span>
          <span className="text-foreground">{file.path}</span>
        </div>
      ))}
    </div>
  );
}

export default function ReportViewer({
  browserReport,
  completionReport,
  jobStatus,
}: ReportViewerProps) {
  const hasReports = browserReport || completionReport;

  if (!hasReports) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center text-muted-foreground">
            {jobStatus === "completed" || jobStatus === "success"
              ? "No reports available yet."
              : "Reports will be available once the job completes."}
          </div>
        </CardContent>
      </Card>
    );
  }

  const handleDownload = () => {
    const report = {
      status: jobStatus,
      browser_report: browserReport,
      completion_report: completionReport,
      generated_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Reports</h3>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          Download Report
        </Button>
      </div>

      {browserReport && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Browser Inspection Report
              <Badge variant="default">Generated</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {browserReport.issues.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold">Issues Found</h4>
                <div className="space-y-2">
                  {browserReport.issues.map((issue, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-md border p-3"
                    >
                      <SeverityIcon severity={issue.severity} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm">{issue.message}</p>
                        {issue.element && (
                          <code className="mt-1 block truncate text-xs text-muted-foreground">
                            {issue.element}
                          </code>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {browserReport.screenshots.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold">Screenshots</h4>
                <div className="grid grid-cols-2 gap-3">
                  {browserReport.screenshots.map((src, i) => (
                    <div
                      key={i}
                      className="overflow-hidden rounded-md border bg-muted"
                    >
                      <img
                        src={src}
                        alt={`Screenshot ${i + 1}`}
                        className="h-48 w-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <PerformanceCard metrics={browserReport.performance} />
          </CardContent>
        </Card>
      )}

      {completionReport && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Completion Report
              <Badge variant="default">Generated</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md bg-muted/50 p-4">
              <p className="text-sm">{completionReport.summary}</p>
            </div>

            {completionReport.files_changed.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold">
                  Files Changed ({completionReport.files_changed.length})
                </h4>
                <FileChangeList files={completionReport.files_changed} />
              </div>
            )}

            {completionReport.errors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-destructive">
                  Errors ({completionReport.errors.length})
                </h4>
                <div className="space-y-1">
                  {completionReport.errors.map((err, i) => (
                    <div
                      key={i}
                      className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
                    >
                      {err}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}