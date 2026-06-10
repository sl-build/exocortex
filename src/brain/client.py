"""Brain CLI v2 — OpenAI-compatible API client with lazy imports."""

from __future__ import annotations

from .context import assemble_messages
from .depth import get_depth_config, merge_depth_into_params
from .keys import get_default_model
from .profiles import get_all_profiles
from .stats import Stats

DEFAULT_MAX_TOKENS = 16384


def _supports_reasoning_effort(model: str) -> bool:
    """reasoning_effort is OpenAI o-series only."""
    return any(model.startswith(p) for p in ["o1", "o3", "o4"])


def _call_api(
    prompt: str,
    *,
    model: str | None = None,
    provider: str = "openrouter",
    api_key: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    context_block: str | None = None,
    depth: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    raw: bool = False,
    retries: int = 3,
    raw_model: bool = False,
) -> tuple[str, Stats]:
    """Call the API via provider adapter layer.

    Returns (response_text, Stats).
    Raises APIError after retries exhausted.
    """
    from .provider import complete

    actual_model = model or get_default_model(provider)

    # Build messages
    messages = assemble_messages(
        prompt=prompt,
        context_block=context_block,
        system_prompt=system_prompt,
        raw=raw,
    )

    # Build base params
    params: dict = {}

    # Apply depth preset if provided (sets max_tokens from depth config)
    if depth:
        params = merge_depth_into_params(params, depth)

    # Explicit --max-tokens override wins over everything
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    elif "max_tokens" not in params:
        params["max_tokens"] = DEFAULT_MAX_TOKENS

    if temperature is not None:
        params["temperature"] = temperature

    # reasoning_effort: only for OpenAI o-series models
    if depth and _supports_reasoning_effort(actual_model):
        preset = get_depth_config(depth)
        if "reasoning_effort" in preset:
            params["reasoning_effort"] = preset["reasoning_effort"]

    # raw_model: pass model name as-is, no transformation
    final_model = actual_model if raw_model else actual_model

    return complete(
        messages=messages,
        model=final_model,
        provider=provider,
        max_tokens=params.get("max_tokens"),
        temperature=params.get("temperature"),
        reasoning_effort=params.get("reasoning_effort"),
    )


def call_and_print(
    prompt: str,
    *,
    model: str | None = None,
    provider: str = "openrouter",
    api_key: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    context_block: str | None = None,
    depth: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    profile: str | None = None,
    raw: bool = False,
    json_output: bool = False,
    show_stats: bool = False,
    suppress_print: bool = False,
    retries: int = 3,
    raw_model: bool = False,
) -> str:
    """Call the API and print the result.

    Returns the response text (or JSON string if json_output=True).
    """
    # Apply profile if specified
    if profile:
        prof = get_all_profiles()[profile]
        if not system_prompt:
            system_prompt = prof["system_prompt"]
        # Only override depth if user didn't explicitly set one
        if depth is None:
            depth = prof["default_depth"]
        # Only override temperature if user didn't explicitly set one
        if temperature is None:
            temperature = prof["default_temperature"]

    # Default model comes from provider if not explicitly set
    if model is None:
        model = get_default_model(provider)

    response_text, stats = _call_api(
        prompt=prompt,
        model=model,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        system_prompt=system_prompt,
        context_block=context_block,
        depth=depth,
        max_tokens=max_tokens,
        temperature=temperature,
        raw=raw,
        retries=retries,
        raw_model=raw_model,
    )

    # Output
    output: str | None = None
    if json_output:
        from .structured import build_json_output

        if show_stats:
            output = build_json_output(
                response_text=response_text,
                model=stats.model,
                prompt_tokens=stats.prompt_tokens,
                completion_tokens=stats.completion_tokens,
                total_tokens=stats.total_tokens,
                cost_usd=stats.calculate_cost(),
                latency_ms=stats.latency_ms,
            )
        else:
            output = build_json_output(
                response_text=response_text,
                model=stats.model,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                cost_usd=None,
                latency_ms=None,
            )
        if not suppress_print:
            print(output)
    elif not suppress_print:
        print(response_text)

    if show_stats and not json_output and not suppress_print:
        stats.report(to_stderr=True)

    if json_output and output is not None:
        return output
    return response_text
