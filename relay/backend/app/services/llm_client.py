from __future__ import annotations

"""Async LLM client adapters used by the chat service."""
# @tag:backend,services,llm

# --- Imports -----------------------------------------------------------------
import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import get_settings


@dataclass
class LLMResult:
    """Structured result from any LLM provider."""

    text: str
    model_name: str
    latency_ms: int


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> LLMResult:  # pragma: no cover - protocol
        ...


class EchoLLMClient:
    """Predictable test double that simply echoes prompts."""

    async def generate(self, prompt: str) -> LLMResult:
        start = time.perf_counter()
        await asyncio.sleep(0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResult(
            text=f"[echo] {prompt}",
            model_name="echo",
            latency_ms=latency_ms,
        )


class OpenAILLMClient:
    """Thin wrapper around OpenAI's Chat Completions endpoint."""

    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._base_url = "https://api.openai.com/v1/chat/completions"

    async def generate(self, prompt: str) -> LLMResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
        }
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._base_url, headers=headers, json=payload)
        resp.raise_for_status()
        latency_ms = int((time.perf_counter() - start) * 1000)
        data = resp.json()
        message = data["choices"][0]["message"]["content"].strip()
        model_name = data.get("model", self.model)
        return LLMResult(text=message, model_name=model_name, latency_ms=latency_ms)


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a singleton LLM client based on configuration."""

    global _llm_client
    if _llm_client is not None:
        return _llm_client

    settings = get_settings()
    if settings.llm_provider == "openai" and settings.openai_api_key:
        _llm_client = OpenAILLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            max_tokens=settings.max_response_tokens,
        )
    else:
        _llm_client = EchoLLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """Force recreation of the cached LLM client (primarily for tests)."""

    global _llm_client
    _llm_client = None
