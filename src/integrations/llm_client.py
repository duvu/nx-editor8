"""
LiteLLM client integration following EngineX patterns for consistency.

This module provides async LiteLLM client functionality compatible with the existing
xProjects ecosystem, including multi-fallback configuration and comprehensive error handling.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class LiteLLMClientConfig:
    """Configuration container for LiteLLM client (consistent with EngineX)."""

    api_base: str
    api_key: str
    model: str
    timeout_seconds: int = 60
    max_tokens: int = 4000
    temperature: float = 0.7
    max_retries: int = 3
    backoff_factor: float = 1.5

    @classmethod
    def from_settings(cls) -> "LiteLLMClientConfig":
        """Create configuration from settings with validation."""
        settings = get_settings()
        if not settings.llm_api_base:
            raise ValueError(
                "LLM_API_BASE is required for LiteLLM client (consistent with EngineX/x-neews)"
            )
        if not settings.llm_api_key:
            raise ValueError(
                "LLM_API_KEY is required for LiteLLM client (consistent with EngineX/x-neews)"
            )

        return cls(
            api_base=settings.llm_api_base.rstrip("/"),
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )


class LiteLLMClient:
    """Async client for interacting with LiteLLM-compatible endpoints (following EngineX patterns)."""

    def __init__(self, config: LiteLLMClientConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers and configuration."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Accept": "application/json",
                    }
                    self._client = httpx.AsyncClient(
                        base_url=self.config.api_base,
                        headers=headers,
                        timeout=httpx.Timeout(self.config.timeout_seconds),
                    )
                    logger.info(
                        "nx-editor8 LiteLLM client initialised",
                        base_url=self.config.api_base,
                        model=self.config.model,
                    )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("nx-editor8 LiteLLM client closed")

    async def generate(
        self,
        prompt: str,
        *,
        system_message: str = "You are nx-editor8's AI content processing assistant.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Submit a prompt and return response text."""

        if not prompt.strip():
            raise ValueError("Prompt must not be empty")

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature or self.config.temperature,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        elif self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens

        attempt = 0
        wait_time = 0.5
        client = await self._get_client()

        while True:
            attempt += 1
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code == 429:
                    raise httpx.HTTPStatusError(
                        "Rate limited", request=response.request, response=response
                    )
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "LiteLLM response received",
                    model=self.config.model,
                    attempt=attempt,
                )

                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("LiteLLM response missing choices")

                message = choices[0].get("message") or {}
                content = message.get("content")
                if not content:
                    raise RuntimeError("LiteLLM response missing content")

                return content

            except (
                httpx.TimeoutException,
                httpx.HTTPStatusError,
                httpx.NetworkError,
            ) as exc:
                if attempt >= self.config.max_retries:
                    logger.error(
                        "LiteLLM invocation failed",
                        attempt=attempt,
                        error=str(exc),
                        status_code=getattr(exc, "response", None)
                        and exc.response.status_code,
                    )
                    raise RuntimeError("LiteLLM request failed") from exc

                wait = wait_time * self.config.backoff_factor ** (attempt - 1)
                logger.warning(
                    "LiteLLM invocation retry",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)
            except httpx.HTTPError as exc:
                logger.error(
                    "LiteLLM unexpected HTTP error",
                    error=str(exc),
                    attempt=attempt,
                )
                raise RuntimeError("LiteLLM request failed") from exc

    async def generate_json(
        self,
        prompt: str,
        *,
        system_message: str = "You are nx-editor8's AI content processing assistant. Return valid JSON only.",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Generate JSON response and parse it automatically."""
        response = await self.generate(
            prompt=prompt,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM response as JSON",
                response=response[:200],
                error=str(e),
            )
            # Return a fallback structure
            return {"error": "Invalid JSON response", "raw_response": response}


# Singleton client instance (following EngineX patterns)
_cached_client: Optional[LiteLLMClient] = None


def get_llm_client() -> LiteLLMClient:
    """Return singleton LiteLLM client instance."""
    global _cached_client

    if _cached_client is None:
        config = LiteLLMClientConfig.from_settings()
        _cached_client = LiteLLMClient(config)

    return _cached_client


async def close_llm_client() -> None:
    """Close the singleton LiteLLM client."""
    global _cached_client
    if _cached_client is not None:
        await _cached_client.close()
        _cached_client = None
