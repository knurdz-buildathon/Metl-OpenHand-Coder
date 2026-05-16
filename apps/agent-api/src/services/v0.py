"""
v0.dev integration module.
When the control panel requests UI generation, this module calls v0.dev's API
and injects the generated code into the project.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx


class V0Client:
    """Client for v0.dev UI generation API."""

    def __init__(self):
        self.base_url = "https://v0.dev/api"

    async def generate_ui(
        self,
        prompt: str,
        framework: str = "next",
        existing_components: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """
        Generate UI components using v0.dev.

        Args:
            prompt: Description of the UI to generate
            framework: Target framework (next, react, vue, etc.)
            existing_components: List of existing components for context

        Returns:
            Dictionary with generated_code, component_files, and metadata
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/generate",
                    json={
                        "prompt": prompt,
                        "framework": framework,
                        "existing_components": existing_components or [],
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {
                        "status": "error",
                        "message": f"v0 API returned {resp.status_code}: {resp.text}",
                        "generated_code": None,
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to call v0 API: {str(e)}",
                    "generated_code": None,
                }

    async def inject_into_project(
        self,
        generated_code: str,
        target_dir: str,
        component_paths: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Inject generated code into the project filesystem.

        Args:
            generated_code: The generated code content
            target_dir: Root directory of the project
            component_paths: List of {path: str, content: str} for each file

        Returns:
            Status of the injection
        """
        results = []
        if component_paths:
            for item in component_paths:
                file_path = os.path.join(target_dir, item["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(item["content"])
                results.append({"path": item["path"], "status": "created"})

        return {"status": "success", "files_created": len(results), "files": results}


# Initialize as singleton
v0_client = V0Client()