from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMConfig:
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    timeout: float = 120.0


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, *, image_data_url: str | None = None) -> str:
        raise NotImplementedError
