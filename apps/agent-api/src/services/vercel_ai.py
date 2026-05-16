"""
Vercel AI SDK integration module for plan generation and LLM queries.
Supports Azure AI Foundry (custom base URL + api-key header) and standard OpenAI/Anthropic.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from src.core.config import settings


class LLMProvider:
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    AZURE = "azure"


class VercelAIClient:
    """Client for interacting with AI models via OpenAI-compatible endpoints.

    Supports Azure AI Foundry by using a custom base URL and ``api-key`` header
    instead of the standard ``Authorization: Bearer`` header.
    """

    def __init__(
        self,
        provider: str = LLMProvider.ANTHROPIC,
        model: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model or self._default_model()
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()

    def _default_model(self) -> str:
        defaults = {
            LLMProvider.OPENAI: "gpt-4o",
            LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
            LLMProvider.GOOGLE: "gemini-2.0-flash",
            LLMProvider.MISTRAL: "mistral-large-latest",
            LLMProvider.AZURE: settings.AZURE_AI_MODEL or "gpt-4o",
        }
        return defaults.get(self.provider, "claude-sonnet-4-20250514")

    def _get_api_key(self) -> Optional[str]:
        keys = {
            LLMProvider.OPENAI: settings.LLM_OPENAI_API_KEY,
            LLMProvider.ANTHROPIC: settings.LLM_ANTHROPIC_API_KEY,
            LLMProvider.GOOGLE: settings.LLM_GOOGLE_API_KEY,
            LLMProvider.MISTRAL: settings.LLM_MISTRAL_API_KEY,
            LLMProvider.AZURE: settings.AZURE_AI_API_KEY,
        }
        return keys.get(self.provider)

    def _get_base_url(self) -> str:
        urls = {
            LLMProvider.OPENAI: "https://api.openai.com/v1",
            LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
            LLMProvider.MISTRAL: "https://api.mistral.ai/v1",
            LLMProvider.AZURE: settings.AZURE_AI_BASE_URL or "",
        }
        return urls.get(self.provider, "")

    async def generate_plan(
        self, prompt: str, plan_md: Optional[str] = None
    ) -> dict[str, Any]:
        """Generate a detailed implementation plan."""
        system_prompt = """You are an expert software architect.
Create a detailed implementation plan from the prompt.
Output as structured markdown with steps, files to create, and dependencies."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Prompt: {prompt}\n\nPlan: {plan_md or 'None'}"},
        ]
        return await self._call_llm(messages)

    async def review_code(self, code_diff: str, context: str = "") -> dict[str, Any]:
        """Review code changes."""
        messages = [
            {"role": "system", "content": "You are an expert code reviewer. Identify bugs and suggest improvements."},
            {"role": "user", "content": f"Context: {context}\n\nDiff:\n{code_diff}"},
        ]
        return await self._call_llm(messages)

    async def generate_completion_report(
        self, job_summary: str, changes: list[dict], issues: list[dict]
    ) -> str:
        """Generate a completion report."""
        messages = [
            {"role": "system", "content": "Create a concise completion report."},
            {"role": "user", "content": f"Summary: {job_summary}\nChanges: {changes}\nIssues: {issues}"},
        ]
        response = await self._call_llm(messages)
        return response.get("content", job_summary)

    async def _call_llm(self, messages: list[dict]) -> dict[str, Any]:
        if not self.api_key:
            return {"content": "No API key configured for LLM provider.", "role": "assistant"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if self.provider == LLMProvider.ANTHROPIC:
                    return await self._call_anthropic(client, messages)
                if self.provider == LLMProvider.AZURE:
                    return await self._call_azure(client, messages)
                return await self._call_openai_compatible(client, messages)
            except Exception as e:
                return {"content": f"LLM call failed: {str(e)}", "role": "assistant"}

    async def _call_azure(self, client: httpx.AsyncClient, messages: list[dict]) -> dict[str, Any]:
        if not self.base_url:
            return {"content": "Azure AI Foundry base URL not configured.", "role": "assistant"}
        resp = await client.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "api-key": self.api_key or "",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": 4096,
            },
        )
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"content": content, "role": "assistant"}

    async def _call_openai_compatible(self, client: httpx.AsyncClient, messages: list[dict]) -> dict[str, Any]:
        resp = await client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": 4096,
            },
        )
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"content": content, "role": "assistant"}

    async def _call_anthropic(self, client: httpx.AsyncClient, messages: list[dict]) -> dict[str, Any]:
        resp = await client.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": self.model, "max_tokens": 4096, "messages": messages},
        )
        data = resp.json()
        content_blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks)
        return {"content": text, "role": "assistant"}