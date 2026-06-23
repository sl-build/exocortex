"""Tests for ReasoningAdapter — anthropic SDK wrapper."""

from unittest.mock import MagicMock, patch

import pytest


def _make_text_block(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_thinking_block(thinking: str = "Let me think..."):
    block = MagicMock()
    block.type = "thinking"
    block.thinking = thinking
    return block


def _make_response(content_blocks: list, model: str = "qwen3.7-max", input_tokens: int = 10, output_tokens: int = 20):
    msg = MagicMock()
    msg.content = content_blocks
    msg.model = model
    msg.usage = MagicMock()
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


class TestReasoningAdapter:
    """Test ReasoningAdapter with mocked anthropic SDK."""

    def test_complete_success(self):
        msg = _make_response([_make_text_block("Reasoned answer")])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.provider.reasoning import ReasoningAdapter

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
        msg = _make_response([])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.errors import BadResponseError
            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            with pytest.raises(BadResponseError, match="Empty response"):
                adapter.complete(
                    messages=[{"role": "user", "content": "think"}],
                    model="qwen3.7-max",
                )

    def test_server_error_retries_then_raises(self):
        import anthropic

        mock_response = MagicMock()
        mock_response.status_code = 503
        api_error = anthropic.APIStatusError(
            "Service Unavailable", response=mock_response, body=None
        )

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.side_effect = api_error

            from exobrain.errors import APIError
            from exobrain.provider.reasoning import ReasoningAdapter

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
        from exobrain.provider.reasoning import ReasoningAdapter

        adapter = ReasoningAdapter(
            base_url="https://opencode.ai/zen/go/v1",
            api_key="test-key",
        )
        assert adapter.supports_model("qwen3.7-max")
        assert not adapter.supports_model("gpt-4o")

    def test_default_timeout_enforced(self):
        """Regression: ReasoningAdapter must default to 180s timeout."""
        msg = _make_response([_make_text_block("ok")])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            assert adapter._timeout == 350.0
            adapter.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="qwen3.7-max",
            )
            mock_client_cls.assert_called_once()
            passed_timeout = mock_client_cls.call_args.kwargs.get("timeout")
            assert passed_timeout == 350.0, f"expected 350.0, got {passed_timeout}"

    def test_connection_error_retries(self):
        """anthropic.APIConnectionError should raise RetryableError and be retried."""
        import anthropic

        call_count = 0
        success_msg = _make_response([_make_text_block("ok after retry")])

        def create_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise anthropic.APIConnectionError(request=MagicMock())
            return success_msg

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.side_effect = create_side_effect

            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "think"}],
                model="qwen3.7-max",
                retries=2,
            )
            assert text == "ok after retry"
            assert call_count == 2

    def test_timeout_error_retries(self):
        """anthropic.APITimeoutError should raise RetryableError and be retried."""
        import anthropic

        call_count = 0
        success_msg = _make_response([_make_text_block("ok")])

        def create_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise anthropic.APITimeoutError(request=MagicMock())
            return success_msg

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.side_effect = create_side_effect

            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "think"}],
                model="qwen3.7-max",
                retries=2,
            )
            assert text == "ok"
            assert call_count == 2

    def test_thinking_block_with_text_extracts_text(self):
        """Response with thinking+text blocks should return text only."""
        msg = _make_response([
            _make_thinking_block("Let me reason about this..."),
            _make_text_block("The answer is 42."),
        ])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "think"}],
                model="qwen3.7-max",
            )
            assert text == "The answer is 42."

    def test_only_thinking_blocks_raises(self):
        """Response with only thinking blocks (no text) should raise BadResponseError."""
        msg = _make_response([_make_thinking_block("deep thought")])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.errors import BadResponseError
            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            with pytest.raises(BadResponseError, match="Empty response"):
                adapter.complete(
                    messages=[{"role": "user", "content": "think"}],
                    model="qwen3.7-max",
                )

    def test_multiple_text_blocks_concatenated(self):
        """Multiple text blocks should be concatenated."""
        msg = _make_response([
            _make_text_block("Part 1. "),
            _make_text_block("Part 2."),
        ])

        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.return_value = msg

            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "think"}],
                model="qwen3.7-max",
            )
            assert text == "Part 1. Part 2."

    def test_base_url_strips_v1_suffix(self):
        """anthropic SDK appends /v1/messages, so we strip /v1 from config URL."""
        with patch("anthropic.Anthropic") as mock_client_cls:
            from exobrain.provider.reasoning import ReasoningAdapter

            adapter = ReasoningAdapter(
                base_url="https://opencode.ai/zen/go/v1",
                api_key="test-key",
            )
            adapter._build_client(timeout=None)
            passed_base_url = mock_client_cls.call_args.kwargs.get("base_url")
            assert passed_base_url == "https://opencode.ai/zen/go"
