"""Brain CLI v2 — Structured JSON output handling."""

from __future__ import annotations

import json


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences from model output.

    Handles ```json ... ``` and ``` ... ``` patterns.
    """
    t = text.strip()
    if t.startswith("```json") and t.endswith("```"):
        t = t[7:-3].strip()
    elif t.startswith("```") and t.endswith("```"):
        t = t[3:-3].strip()
    return t


def build_json_output(
    response_text: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    cost_usd: float | None,
    latency_ms: float | None,
) -> str:
    """Build a JSON output dict for --json mode.

    Always includes 'response'. Includes 'usage' if stats available.
    """
    result: dict = {
        "response": strip_code_fences(response_text),
    }

    usage: dict = {}
    if model:
        usage["model"] = model
    if prompt_tokens is not None:
        usage["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        usage["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        usage["total_tokens"] = total_tokens
    if cost_usd is not None:
        usage["cost_usd"] = round(cost_usd, 6)
    if latency_ms is not None:
        usage["latency_ms"] = round(latency_ms, 1)

    if usage:
        result["usage"] = usage

    return json.dumps(result, indent=2, ensure_ascii=False)


def validate_json_output(text: str) -> str:
    """Validate that text is valid JSON. Returns cleaned text.

    Raises ValueError if not valid JSON.
    """
    cleaned = strip_code_fences(text)
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError as e:
        raise ValueError(f"Model output is not valid JSON: {e}") from e