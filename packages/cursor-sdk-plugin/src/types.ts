export interface IAgentOrchestrator {
  name: string;
  initialize(config: AgentConfig): Promise<void>;
  executePrompt(prompt: string, options?: AgentOptions): Promise<AgentResponse>;
  streamPrompt(
    prompt: string,
    onChunk: (chunk: string) => void,
    options?: AgentOptions
  ): Promise<AgentResponse>;
  cancel(): Promise<void>;
  cleanup(): Promise<void>;
}

export interface AgentConfig {
  workspacePath: string;
  llmProvider: string;
  llmModel?: string;
  llmApiKey?: string;
  maxIterations?: number;
  enableBrowser?: boolean;
  envVars?: Record<string, string>;
}

export interface AgentOptions {
  maxIterations?: number;
  resumePreviousId?: string;
  additionalContext?: string;
}

export interface AgentResponse {
  success: boolean;
  summary: string;
  changes: Array<{
    type: "created" | "modified" | "deleted" | "renamed";
    file: string;
    description?: string;
  }>;
  error?: string;
  iterations: number;
  durationMs: number;
}