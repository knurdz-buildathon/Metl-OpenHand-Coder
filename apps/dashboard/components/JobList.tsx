"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listJobs, type Job } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const STATUS_VARIANTS: Record<string, "secondary" | "default" | "success" | "destructive" | "warning"> = {
  pending: "secondary",
  queued: "secondary",
  executing: "default",
  running: "default",
  in_progress: "default",
  completed: "success",
  success: "success",
  failed: "destructive",
  error: "destructive",
  cancelled: "warning",
  canceled: "warning",
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncate(str: string, len: number): string {
  if (str.length <= len) return str;
  return str.slice(0, len) + "...";
}

export default function JobList() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const data = await listJobs();
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch jobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-destructive">
            <p>{error}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={fetchJobs}
            >
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-lg font-medium">No jobs yet</p>
            <p className="text-sm mt-1">
              Submit your first job using the form on the left.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Jobs</CardTitle>
        <span className="text-sm text-muted-foreground">
          {jobs.length} job{jobs.length !== 1 ? "s" : ""}
        </span>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-3 font-medium">ID</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Repository</th>
                <th className="pb-3 font-medium">Prompt</th>
                <th className="pb-3 font-medium">Created</th>
                <th className="pb-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  className="border-b last:border-0 hover:bg-muted/50 cursor-pointer transition-colors"
                  onClick={() => router.push(`/jobs/${job.id}`)}
                >
                  <td className="py-3 pr-2 font-mono text-xs">
                    {truncate(job.id, 8)}
                  </td>
                  <td className="py-3 pr-2">
                    <Badge variant={STATUS_VARIANTS[job.status] || "secondary"}>
                      {job.status}
                    </Badge>
                  </td>
                  <td className="py-3 pr-2 max-w-[200px] truncate">
                    {truncate(
                      job.github_url.replace("https://github.com/", ""),
                      24
                    )}
                  </td>
                  <td className="py-3 pr-2 max-w-[200px] text-muted-foreground truncate">
                    {truncate(job.prompt, 40)}
                  </td>
                  <td className="py-3 pr-2 text-muted-foreground whitespace-nowrap">
                    {formatDate(job.created_at)}
                  </td>
                  <td className="py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/jobs/${job.id}`);
                      }}
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}