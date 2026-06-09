"""Brain CLI v2 — Usage statistics and cost estimation."""

from __future__ import annotations

import sys
from dataclasses import dataclass

# Cost table per 1M tokens (input / output)
COST_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "openai/gpt-5.5": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "anthropic/claude-opus-4": {"input": 15.00, "output": 75.00},
    "deepseek/deepseek-v4": {"input": 0.14, "output": 0.28},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
}


@dataclass
class Stats:
    """Accumulate and report usage statistics."""

    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    retries_used: int = 0

    def update_from_response(self, response) -> None:
        """Extract usage from an OpenAI API response object."""
        if hasattr(response, "model"):
            self.model = response.model
        if hasattr(response, "usage") and response.usage:
            self.prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            self.completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0
            self.total_tokens = getattr(response.usage, "total_tokens", 0) or 0

    def calculate_cost(self) -> float | None:
        """Estimate cost in USD based on token usage and model pricing."""
        if not self.model:
            return None

        pricing = COST_PER_1M_TOKENS.get(self.model)
        if not pricing:
            # Try prefix match
            for key in COST_PER_1M_TOKENS:
                if self.model.startswith(key) or key.startswith(self.model):
                    pricing = COST_PER_1M_TOKENS[key]
                    break

        if not pricing:
            return None

        cost = (
            self.prompt_tokens * pricing["input"] / 1_000_000
            + self.completion_tokens * pricing["output"] / 1_000_000
        )
        return cost

    def report(self, to_stderr: bool = True) -> str:
        """Format and optionally print stats report."""
        lines = []
        lines.append(f"Model: {self.model or 'unknown'}")
        if self.prompt_tokens or self.completion_tokens:
            lines.append(
                f"Tokens: {self.prompt_tokens} prompt + {self.completion_tokens} completion = {self.total_tokens} total"
            )
        cost = self.calculate_cost()
        if cost is not None:
            lines.append(f"Cost: ${cost:.4f}")
        if self.latency_ms:
            lines.append(f"Latency: {self.latency_ms / 1000:.1f}s")
        if self.retries_used:
            lines.append(f"Retries: {self.retries_used}")

        report_text = "\n".join(lines)

        if to_stderr:
            print(report_text, file=sys.stderr)

        return report_text
