// Dashboard settings page.
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export default function SettingsPage() {
  const [webhookUrl, setWebhookUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [azureKey, setAzureKey] = useState("");
  const [azureBaseUrl, setAzureBaseUrl] = useState("");
  const [azureModel, setAzureModel] = useState("gpt-4o");
  const [selectedProvider, setSelectedProvider] = useState("azure");
  const [defaultModel, setDefaultModel] = useState("gpt-4o");
  const [enableV0, setEnableV0] = useState(false);
  const [enableCursorSdk, setEnableCursorSdk] = useState(false);

  const handleSave = () => {
    localStorage.setItem("metl-settings", JSON.stringify({
      selectedProvider, defaultModel, enableV0, enableCursorSdk,
      azureKey, azureBaseUrl, azureModel, webhookUrl, githubToken,
    }));
    toast.success("Settings saved");
  };

  return (
    <div className="mx-auto max-w-3xl p-4 sm:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure LLM providers, integrations, and connection settings.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Azure AI Foundry</CardTitle>
          <CardDescription>
            Primary LLM provider. Uses an OpenAI-compatible endpoint.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">API Key</label>
            <Input type="password" placeholder="azure-api-key" value={azureKey} onChange={(e) => setAzureKey(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Base URL</label>
            <Input placeholder="https://your-resource.cognitiveservices.azure.com/openai/deployments/your-deployment" value={azureBaseUrl} onChange={(e) => setAzureBaseUrl(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Model</label>
            <Input placeholder="gpt-4o" value={azureModel} onChange={(e) => setAzureModel(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Other LLM Providers</CardTitle>
          <CardDescription>Fallback or alternative providers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">OpenAI API Key</label>
            <Input type="password" placeholder="sk-..." value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Anthropic API Key</label>
            <Input type="password" placeholder="sk-ant-..." value={anthropicKey} onChange={(e) => setAnthropicKey(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Default Provider</label>
            <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
              <option value="azure">Azure AI Foundry</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="google">Google</option>
              <option value="mistral">Mistral</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Default Model</label>
            <Input placeholder="gpt-4o" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>Optional integrations for enhanced development.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">v0.dev UI Generation</p>
              <p className="text-xs text-muted-foreground">Generate UI components via v0.dev</p>
            </div>
            <button className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enableV0 ? "bg-primary" : "bg-muted"}`} onClick={() => setEnableV0(!enableV0)}>
              <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${enableV0 ? "translate-x-6" : "translate-x-1"}`} />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Cursor Agent SDK</p>
              <p className="text-xs text-muted-foreground">Optional Cursor agent orchestration</p>
            </div>
            <button className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enableCursorSdk ? "bg-primary" : "bg-muted"}`} onClick={() => setEnableCursorSdk(!enableCursorSdk)}>
              <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${enableCursorSdk ? "translate-x-6" : "translate-x-1"}`} />
            </button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Control Panel Webhook</CardTitle>
          <CardDescription>URL where the agent sends completion reports.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Webhook URL</label>
            <Input placeholder="https://control-panel.example.com/api/webhook" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>GitHub</CardTitle>
          <CardDescription>GitHub token for private repositories.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">GitHub Personal Access Token</label>
            <Input type="password" placeholder="ghp_..." value={githubToken} onChange={(e) => setGithubToken(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave}>Save Settings</Button>
      </div>
    </div>
  );
}