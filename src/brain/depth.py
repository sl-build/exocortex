"""Brain CLI v3 — Depth presets mapping to model parameters."""

from __future__ import annotations

DEPTH_PRESETS: dict[str, dict] = {
    "quick": {"max_tokens": 4096, "reasoning_effort": "low"},
    "normal": {"max_tokens": 8192, "reasoning_effort": "medium"},
    "deep": {"max_tokens": 16384, "reasoning_effort": "high"},
    "exhaustive": {"max_tokens": 32768, "reasoning_effort": "high"},
}

VALID_DEPTHS = list(DEPTH_PRESETS.keys())

DEFAULT_DEPTH = "normal"


def get_depth_config(depth: str) -> dict:
    """Return a copy of the preset for a depth level."""
    if depth not in DEPTH_PRESETS:
        raise ValueError(f"Unknown depth: {depth}. Valid: {VALID_DEPTHS}")
    return DEPTH_PRESETS[depth].copy()


def merge_depth_into_params(params: dict, depth: str) -> dict:
    """Merge depth preset max_tokens into API call params.

    temperature and reasoning_effort are handled at the provider layer.
    Explicit --max-tokens from CLI is applied in client.py after this call.
    """
    cfg = get_depth_config(depth)
    merged = params.copy()
    if "max_tokens" not in merged:
        merged["max_tokens"] = cfg["max_tokens"]
    return merged
