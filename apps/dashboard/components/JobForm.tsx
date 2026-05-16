"use client";

import { useState } from "react";
import { toast } from "sonner";
import { createJob } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Input, Textarea, Select } from "@/components/ui/input";

interface JobFormData {
  github_url: string;
  prompt: string;
  plan_md_url: string;
  enable_v0: boolean;
  enable_cursor_sdk: boolean;
  llm_provider: string;
  llm_model: string;
}

const LLM_PROVIDERS = [
  { value: "azure", label: "Azure AI Foundry" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google AI" },
  { value: "mistral", label: "Mistral" },
];

const DEFAULT_MODELS: Record<string, string> = {
  openai: "gpt-4o",
  anthropic: "claude-sonnet-4-20250514",
  google: "gemini-2.5-pro",
  mistral: "mistral-large-latest",
};

export default function JobForm() {
  const [form, setForm] = useState<JobFormData>({
    github_url: "",
    prompt: "",
    plan_md_url: "",
    enable_v0: false,
    enable_cursor_sdk: true,
    llm_provider: "anthropic",
    llm_model: "claude-sonnet-4-20250514",
  });
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value, type } = e.target;
    const checked =
      type === "checkbox" ? (e.target as HTMLInputElement).checked : undefined;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value;
    setForm((prev) => ({
      ...prev,
      llm_provider: provider,
      llm_model: DEFAULT_MODELS[provider] || prev.llm_model,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!form.github_url.trim()) {
      toast.error("GitHub URL is required");
      return;
    }
    if (!form.prompt.trim()) {
      toast.error("Prompt is required");
      return;
    }

    setSubmitting(true);

    try {
      await createJob({
        github_url: form.github_url,
        prompt: form.prompt,
        plan_md_url: form.plan_md_url || undefined,
        options: {
          enable_v0: form.enable_v0,
          enable_cursor_sdk: form.enable_cursor_sdk,
          llm_provider: form.llm_provider,
          llm_model: form.llm_model,
        },
      });

      toast.success("Job submitted successfully!");

      setForm((prev) => ({
        ...prev,
        github_url: "",
        prompt: "",
        plan_md_url: "",
      }));
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to submit job"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>New Job</CardTitle>
        <CardDescription>
          Configure and submit a new autonomous coding job.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="github_url"
              className="text-sm font-medium leading-none"
            >
              GitHub URL <span className="text-destructive">*</span>
            </label>
            <Input
              id="github_url"
              name="github_url"
              placeholder="https://github.com/user/repo"
              value={form.github_url}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="prompt"
              className="text-sm font-medium leading-none"
            >
              Prompt <span className="text-destructive">*</span>
            </label>
            <Textarea
              id="prompt"
              name="prompt"
              placeholder="Describe the changes you want the agent to make..."
              rows={4}
              value={form.prompt}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="plan_md_url"
              className="text-sm font-medium leading-none"
            >
              Plan Markdown URL{" "}
              <span className="text-muted-foreground">(optional)</span>
            </label>
            <Input
              id="plan_md_url"
              name="plan_md_url"
              placeholder="https://example.com/plan.md"
              value={form.plan_md_url}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>

          <div className="space-y-3 pt-2">
            <p className="text-sm font-medium leading-none">Options</p>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                name="enable_v0"
                checked={form.enable_v0}
                onChange={handleChange}
                disabled={submitting}
                className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <span className="text-sm">Enable v0</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                name="enable_cursor_sdk"
                checked={form.enable_cursor_sdk}
                onChange={handleChange}
                disabled={submitting}
                className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <span className="text-sm">Enable Cursor SDK</span>
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label
                htmlFor="llm_provider"
                className="text-sm font-medium leading-none"
              >
                LLM Provider
              </label>
              <Select
                id="llm_provider"
                name="llm_provider"
                value={form.llm_provider}
                onChange={handleProviderChange}
                disabled={submitting}
              >
                {LLM_PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="llm_model"
                className="text-sm font-medium leading-none"
              >
                Model
              </label>
              <Input
                id="llm_model"
                name="llm_model"
                placeholder="claude-sonnet-4-20250514"
                value={form.llm_model}
                onChange={handleChange}
                disabled={submitting}
              />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Submitting...
              </span>
            ) : (
              "Submit Job"
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}