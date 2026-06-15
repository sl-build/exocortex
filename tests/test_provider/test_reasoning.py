"""Tests for ReasoningAdapter — httpx-based adapter."""

from unittest.mock import patch

import pytest


def _make_json_response(status_code: int, json_data: dict, text: str = ""):
    return type(
        "MockResponse",
        (),
        {
            "status_code": status_code,
            "text": text,
            "json": lambda self: json_data,
        },
    )()


class TestReasoningAdapter:
    """Test ReasoningAdapter with mocked httpx."""

    def test_complete_success(self):
        mock_json = {
            "content": [{"type": "text", "text": "Reasoned answer"}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "model": "qwen3.7-max",
        }
        mock_response = _make_json_response(200, mock_json)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = mock_response

            from exocortex.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "think"}],
                model="qwen3.7-max",
            )
            assert text == "Reasoned answer"
            assert stats.model == "qwen3.7-max"
            assert stats.total_tokens == 30

    def test_empty_choices_raises(self):
        mock_json = {
            "content": [],
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "model": "qwen3.7-max",
        }
        mock_response = _make_json_response(200, mock_json)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = mock_response

            from exocortex.errors import BadResponseError
            from exocortex.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            with pytest.raises(BadResponseError, match="Empty content"):
                adapter.complete(
                    messages=[{"role": "user", "content": "think"}],
                    model="qwen3.7-max",
                )

    def test_server_error_retries_then_raises(self):
        mock_response = _make_json_response(503, {}, "Service Unavailable")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = mock_response

            from exocortex.errors import APIError
            from exocortex.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            with pytest.raises(APIError, match="failed after"):
                adapter.complete(
                    messages=[{"role": "user", "content": "think"}],
                    model="qwen3.7-max",
                    retries=0,
                )

    def test_supports_model_checks_model_map(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-test")
        from exocortex.provider.reasoning import ReasoningAdapter

        adapter = ReasoningAdapter(
            base_url="https://opencode.ai/zen/go/v1",
            api_key="test-key",
        )
        # supports_model checks against all providers (built-in + custom)
        # qwen3.7-max is configured as custom opencode_go model in config.toml
        assert adapter.supports_model("qwen3.7-max")
        assert not adapter.supports_model("gpt-4o")

    def test_default_timeout_enforced(self):
        """Regression: ReasoningAdapter must default to CLI 180s timeout, not 120s."""
        mock_json = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "model": "qwen3.7-max",
        }
        mock_response = _make_json_response(200, mock_json)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = mock_response

            from exocortex.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            assert adapter._timeout == 180.0
            adapter.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="qwen3.7-max",
            )
            mock_client_cls.assert_called_once()
            passed_timeout = mock_client_cls.call_args.kwargs.get("timeout")
            assert passed_timeout == 180.0, f"expected 180.0, got {passed_timeout}"
