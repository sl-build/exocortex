"""Exocortex CLI — Anthropic SDK adapter for reasoning models.

Uses the official anthropic SDK which handles thinking blocks, streaming,
and proper error categorization. Works with any Anthropic Messages API
compatible endpoint (e.g. opencode_go's /zen/go/v1).
"""

from __future__ import annotations

import time
from typing import cast

from ..errors import APIError, BadResponseError, RetryableError
from ..retry import retry_with_backoff
from ..stats import Stats


class ReasoningAdapter:
    """Adapter for Anthropic Messages API compatible reasoning models.

    Wraps the official anthropic SDK for streaming, thinking blocks,
    connection pooling, and proper timeout/retry semantics.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float | None = None):
        # SDK appends /v1/messages to base_url. Our config has /v1 in it
        # (e.g. https://opencode.ai/zen/go/v1), so strip it here.
        self._base_url = base_url.rstrip("/")
        if self._base_url.endswith("/v1"):
            self._base_url = self._base_url[:-3]
        self._api_key = api_key
        # Match CLI default timeout (config default is 180s).
        self._timeout = timeout or 180.0

    def _build_client(self, timeout: float | None):
        """Lazy import + build anthropic client with given timeout."""
        import anthropic

        effective_timeout = timeout if timeout is not None else self._timeout
        return anthropic.Anthropic(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=effective_timeout,
        )

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
        import anthropic

        system_prompt: str | None = None
        user_messages: list[dict] = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        stats = Stats(model=model)
        start_time = time.monotonic()

        def _make_call():
            client = self._build_client(timeout)
            try:
                kwargs: dict = {
                    "model": model,
                    "messages": user_messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                if temperature is not None:
                    kwargs["temperature"] = temperature

                msg = client.messages.create(**kwargs)
                stats.latency_ms = (time.monotonic() - start_time) * 1000

                usage = msg.usage
                stats.prompt_tokens = usage.input_tokens or 0
                stats.completion_tokens = usage.output_tokens or 0
                stats.total_tokens = stats.prompt_tokens + stats.completion_tokens
                stats.model = msg.model or model

                # Concatenate text from all text-type content blocks.
                # ThinkingBlock and other types are ignored.
                text_parts: list[str] = []
                for block in msg.content:
                    if block.type == "text":
                        text_parts.append(block.text)

                text = "".join(text_parts).strip()
                if not text:
                    raise BadResponseError("Empty response from model")

                return text

            except BadResponseError:
                raise
            except anthropic.APIConnectionError as e:
                stats.retries_used += 1
                raise RetryableError(f"Connection error: {e}", status_code=None) from e
            except anthropic.APITimeoutError as e:
                stats.retries_used += 1
                raise RetryableError(f"Timeout: {e}", status_code=None) from e
            except anthropic.APIStatusError as e:
                code = e.status_code
                if code == 429 or code >= 500:
                    stats.retries_used += 1
                    raise RetryableError(str(e), status_code=code) from e
                raise APIError(str(e), status_code=code) from e
            except anthropic.APIError as e:
                raise APIError(str(e), status_code=getattr(e, "status_code", None)) from e

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
