"""Exocortex CLI — httpx-based adapter for OpenCode Go reasoning API."""

from __future__ import annotations

import time
from typing import cast

import httpx

from ..errors import APIError, BadResponseError, RetryableError
from ..retry import retry_with_backoff
from ..stats import Stats


class ReasoningAdapter:
    """Adapter for OpenCode Go reasoning models (Qwen3.7 Max/Plus).

    Uses raw httpx (no OpenAI SDK dependency).
    Uses Anthropic Messages API format at /zen/go/v1/messages.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        # Match CLI default timeout (config default is 180s).
        self._timeout = timeout or 180.0

    def complete(
        self,
        messages: list[dict],
        model: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        timeout: float | None = None,
        retries: int = 3,
    ) -> tuple[str, Stats]:
        system_prompt: str | None = None
        user_messages: list[dict] = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        body: dict = {
            "model": model,
            "messages": user_messages,
        }

        if system_prompt:
            body["system"] = system_prompt

        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        if temperature is not None:
            body["temperature"] = temperature

        stats = Stats(model=model)
        start_time = time.monotonic()

        def _make_call():
            try:
                effective_timeout = timeout if timeout is not None else self._timeout
                with httpx.Client(timeout=effective_timeout) as hclient:
                    resp = hclient.post(
                        f"{self._base_url}/messages",
                        headers={
                            "x-api-key": self._api_key,
                            "Content-Type": "application/json",
                            "anthropic-version": "2023-06-01",
                        },
                        json=body,
                    )

                stats.latency_ms = (time.monotonic() - start_time) * 1000

                if resp.status_code >= 500:
                    stats.retries_used += 1
                    raise RetryableError(
                        f"Server error: {resp.status_code}",
                        status_code=resp.status_code,
                    )

                if resp.status_code == 429:
                    stats.retries_used += 1
                    raise RetryableError("Rate limited", status_code=resp.status_code)

                if resp.status_code != 200:
                    raise APIError(
                        f"API error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )

                data = resp.json()

                usage = data.get("usage", {})
                stats.prompt_tokens = usage.get("input_tokens", 0) or 0
                stats.completion_tokens = usage.get("output_tokens", 0) or 0
                stats.total_tokens = stats.prompt_tokens + stats.completion_tokens
                stats.model = data.get("model", model)

                content_items = data.get("content", [])
                if not content_items:
                    raise BadResponseError("Empty content from reasoning API")

                text = ""
                for item in content_items:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        if text.strip():
                            break

                if not text or not text.strip():
                    raise BadResponseError("Empty response from model")

                return text.strip()

            except (BadResponseError, APIError):
                raise
            except RetryableError:
                raise
            except Exception as e:
                raise APIError(str(e)) from e

        result = cast(str, retry_with_backoff(_make_call, max_retries=retries))
        return result, stats

    def supports_model(self, model: str) -> bool:
        from ..keys import get_all_providers

        for provider_name, prov in get_all_providers().items():
            model_map = prov.get("model_map", {})
            if model in model_map and model_map[model] == "reasoning":
                return True
            if prov.get("default_adapter") == "reasoning" and model in prov.get("models", []):
                return True
        return False
