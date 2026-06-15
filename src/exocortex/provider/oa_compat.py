"""Exocortex CLI — OpenAI SDK adapter for oa-compat providers."""

from __future__ import annotations

import time
from typing import cast

from ..errors import APIError, BadResponseError, RetryableError
from ..retry import is_retryable, retry_with_backoff
from ..stats import Stats


class OACompatAdapter:
    """Wrapper around the OpenAI Python SDK for any oa-compat endpoint."""

    def __init__(self, base_url: str, api_key: str, timeout: float | None = None):
        self._base_url = base_url
        self._api_key = api_key
        # OpenAI SDK defaults to 60s when timeout=None; enforce CLI default.
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
        from openai import OpenAI

        params: dict = {
            "model": model,
            "messages": messages,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if temperature is not None:
            params["temperature"] = temperature

        if reasoning_effort is not None:
            params["reasoning_effort"] = reasoning_effort

        stats = Stats(model=model)
        start_time = time.monotonic()

        effective_timeout = timeout if timeout is not None else self._timeout
        client = OpenAI(api_key=self._api_key, base_url=self._base_url, timeout=effective_timeout)

        def _make_call():
            try:
                response = client.chat.completions.create(**params)
                stats.update_from_response(response)
                stats.latency_ms = (time.monotonic() - start_time) * 1000

                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise BadResponseError("Empty response from model")

                return content.strip()

            except BadResponseError:
                raise
            except Exception as e:
                import openai
                if isinstance(e, (openai.APIConnectionError, openai.APITimeoutError)):
                    stats.retries_used += 1
                    raise RetryableError(f"Connection error: {e}", status_code=None) from e
                status_code = getattr(e, "status_code", None)
                if status_code and is_retryable(status_code):
                    stats.retries_used += 1
                    raise RetryableError(str(e), status_code=status_code) from e
                raise APIError(str(e), status_code=status_code) from e

        result = cast(str, retry_with_backoff(_make_call, max_retries=retries))
        return result, stats

    def supports_model(self, model: str) -> bool:
        return True
