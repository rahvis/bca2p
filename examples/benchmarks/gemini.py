"""Optional Gemini adapter for live agent reasoning tracks.

The deterministic benchmark is the default because leaderboard scores must be
reproducible in CI. This module is intentionally optional: it only imports the
Google GenAI SDK at call time and only reads ``GEMINI_API_KEY`` from the process
environment.
"""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass
from typing import Any


class GeminiUnavailableError(RuntimeError):
    """Raised when the optional Gemini track is requested but unavailable."""


@dataclass(frozen=True)
class GeminiAgentConfig:
    """Configuration shared by benchmark Gemini agents."""

    model: str = "gemini-2.5-flash"
    api_key_env: str = "GEMINI_API_KEY"
    temperature: float = 0.0


@dataclass(frozen=True)
class GeminiStructuredAgent:
    """Small structured-output wrapper for benchmark agents."""

    role: str
    output_schema: dict[str, Any]
    config: GeminiAgentConfig = GeminiAgentConfig()

    def generate_decision(self, prompt: str) -> dict[str, Any]:
        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            raise GeminiUnavailableError(f"{self.config.api_key_env} is not set")

        try:
            genai = importlib.import_module("google.genai")
        except ImportError as exc:
            raise GeminiUnavailableError("Install the optional google-genai package") from exc

        client = genai.Client(api_key=api_key)
        content = (
            f"You are the {self.role} in a bca2p benchmark. "
            "Return only JSON matching the supplied schema.\n\n"
            f"{prompt}"
        )
        response = self._generate(client, content)
        text = getattr(response, "text", None)
        if not text:
            raise GeminiUnavailableError("Gemini response did not include text")
        return json.loads(text)

    def _generate(self, client: Any, content: str) -> Any:
        modern_config = {
            "temperature": self.config.temperature,
            "response_format": {
                "text": {
                    "mime_type": "application/json",
                    "schema": self.output_schema,
                }
            },
        }
        try:
            return client.models.generate_content(
                model=self.config.model,
                contents=content,
                config=modern_config,
            )
        except TypeError:
            legacy_config = {
                "temperature": self.config.temperature,
                "response_mime_type": "application/json",
                "response_schema": self.output_schema,
            }
            return client.models.generate_content(
                model=self.config.model,
                contents=content,
                config=legacy_config,
            )
