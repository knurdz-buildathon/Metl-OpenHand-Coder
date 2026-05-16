"use client";

import JobForm from "@/components/JobForm";
import JobList from "@/components/JobList";

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Autonomous Coding Agent</h1>
        <p className="text-muted-foreground mt-1">
          Submit a job with a GitHub repository and prompt to start autonomous
          development.
        </p>
      </div>
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <JobForm />
        </div>
        <div className="lg:col-span-2">
          <JobList />
        </div>
      </div>
    </div>
  );
}