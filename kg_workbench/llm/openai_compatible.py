from __future__ import annotations

import os
from typing import Any

import aiohttp

from .base import BaseLLMClient, LLMConfig


class OpenAICompatibleClient(BaseLLMClient):
    """Minimal async client for OpenAI-compatible chat completion APIs."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (config.base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        if not self.api_key:
            raise ValueError("Missing LLM API key. Set OPENAI_API_KEY or pass --llm-api-key.")

    async def generate(self, prompt: str, *, image_data_url: str | None = None) -> str:
        content: str | list[dict[str, Any]]
        if image_data_url:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ]
        else:
            content = prompt
        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": content}],
        }
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                text = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"LLM request failed ({response.status}): {text}")
                data = await response.json()
        return str(data["choices"][0]["message"]["content"])
