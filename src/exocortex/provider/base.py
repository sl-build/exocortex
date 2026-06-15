"""Exocortex CLI — Adapter protocol for LLM providers."""

from __future__ import annotations

from typing import Protocol

from ..stats import Stats


class Adapter(Protocol):
    """Protocol that all provider adapters must satisfy."""

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
    ) -> tuple[str, Stats]: ...

    def supports_model(self, model: str) -> bool: ...
