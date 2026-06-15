"""Exocortex CLI — Provider adapter layer.

Registry and factory for routing model+provider pairs to the correct adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..keys import get_adapter_name, get_api_key, get_base_url
from ..stats import Stats

if TYPE_CHECKING:
    from .base import Adapter

_REGISTRY: dict[str, Adapter] = {}


def register_adapter(name: str, adapter: Adapter) -> None:
    """Register an adapter instance by name."""
    _REGISTRY[name] = adapter


def _build_adapter(name: str, provider: str, timeout: float | None = None) -> Adapter:
    """Instantiate (or retrieve cached) adapter for a provider."""
    cache_key = f"{name}:{provider}"
    existing = _REGISTRY.get(cache_key)
    if existing is not None:
        return existing

    base_url = get_base_url(provider)
    api_key = get_api_key(provider)

    if name == "reasoning":
        from .reasoning import ReasoningAdapter

        adapter: Adapter = ReasoningAdapter(base_url=base_url, api_key=api_key, timeout=timeout)
    else:
        from .oa_compat import OACompatAdapter

        adapter = OACompatAdapter(base_url=base_url, api_key=api_key, timeout=timeout)

    _REGISTRY[cache_key] = adapter
    return adapter


def get_adapter(model: str, provider: str, timeout: float | None = None) -> Adapter:
    """Resolve the correct adapter for a model+provider pair.

    1. Checks model_map in provider config.
    2. Falls back to the provider's default_adapter.
    """
    name = get_adapter_name(provider, model)
    return _build_adapter(name, provider, timeout=timeout)


def complete(
    messages: list[dict],
    model: str,
    provider: str,
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
    timeout: float | None = None,
    retries: int = 3,
) -> tuple[str, Stats]:
    """Send messages through the correct adapter for the model+provider pair."""
    adapter = get_adapter(model, provider, timeout=timeout)
    return adapter.complete(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        retries=retries,
    )
