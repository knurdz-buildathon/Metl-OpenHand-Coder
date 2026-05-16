import type { IAgentOrchestrator, AgentConfig, AgentResponse, AgentOptions } from "./types";

/**
 * Cursor Agent SDK Adapter - wraps @cursor/sdk behind the IAgentOrchestrator interface.
 * This can be removed at any time by:
 * 1. Deleting packages/cursor-sdk-plugin/
 * 2. Updating the orchestrator to use the default OpenHands-based adapter
 *
 * The core services never import from this package directly;
 * they go through a factory that picks the implementation based on config.
 */
export class CursorAgentAdapter implements IAgentOrchestrator {
  name = "cursor-sdk";
  private config: AgentConfig | null = null;
  private agent: any = null;

  async initialize(config: AgentConfig): Promise<void> {
    this.config = config;

    try {
      const { Agent } = await import("@cursor/sdk");

      this.agent = Agent.create({
        model: config.llmModel || "default",
        workspacePath: config.workspacePath,
        ...(config.maxIterations && { maxIterations: config.maxIterations }),
      });
    } catch (error) {
      throw new Error(
        `Failed to initialize Cursor Agent SDK: ${error instanceof Error ? error.message : "Unknown error"}. Make sure @cursor/sdk is installed.`
      );
    }
  }

  async executePrompt(prompt: string, options?: AgentOptions): Promise<AgentResponse> {
    if (!this.agent) {
      throw new Error("Agent not initialized. Call initialize() first.");
    }

    const startTime = Date.now();
    let iterations = 0;

    try {
      const result = await this.agent.prompt(prompt);

      iterations = result.iterations || 1;

      return {
        success: true,
        summary: result.summary || "Task completed",
        changes: (result.changes || []).map((c: any) => ({
          type: c.type || "modified",
          file: c.file || "",
          description: c.description,
        })),
        iterations,
        durationMs: Date.now() - startTime,
      };
    } catch (error: any) {
      return {
        success: false,
        summary: "Agent execution failed",
        changes: [],
        error: error.message || "Unknown error",
        iterations,
        durationMs: Date.now() - startTime,
      };
    }
  }

  async streamPrompt(
    prompt: string,
    onChunk: (chunk: string) => void,
    options?: AgentOptions
  ): Promise<AgentResponse> {
    if (!this.agent) {
      throw new Error("Agent not initialized. Call initialize() first.");
    }

    const startTime = Date.now();
    let iterations = 0;
    const allChanges: AgentResponse["changes"] = [];

    try {
      for await (const chunk of this.agent.stream(prompt)) {
        onChunk(typeof chunk === "string" ? chunk : JSON.stringify(chunk));
        if (chunk.iterations) iterations = chunk.iterations;
      }

      return {
        success: true,
        summary: "Task completed via streaming",
        changes: allChanges,
        iterations,
        durationMs: Date.now() - startTime,
      };
    } catch (error: any) {
      return {
        success: false,
        summary: "Streaming execution failed",
        changes: [],
        error: error.message || "Unknown error",
        iterations,
        durationMs: Date.now() - startTime,
      };
    }
  }

  async cancel(): Promise<void> {
    if (this.agent?.cancel) {
      await this.agent.cancel();
    }
  }

  async cleanup(): Promise<void> {
    this.agent = null;
    this.config = null;
  }
}