"""Tests for OACompatAdapter — OpenAI SDK wrapper."""

from unittest.mock import patch

import pytest


class TestOACompatAdapter:
    """Test OACompatAdapter with mocked OpenAI SDK."""

    def test_complete_success(self):
        mock_response = type(
            "MockChoice",
            (),
            {
                "message": type("MockMsg", (), {"content": "Hello world!"})(),
            },
        )()
        mock_completion = type(
            "MockCompletion",
            (),
            {
                "choices": [mock_response],
                "model": "gpt-4o",
                "usage": type(
                    "MockUsage", (), {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
                )(),
            },
        )()

        def fake_create(self, **kwargs):
            return mock_completion

        mock_openai = type(
            "MockOpenAI",
            (),
            {
                "chat": type(
                    "MockChat",
                    (),
                    {
                        "completions": type("MockCompletions", (), {"create": fake_create})(),
                    },
                )(),
                "api_key": "test-key",
                "base_url": "https://test.url",
            },
        )

        with patch("openai.OpenAI", return_value=mock_openai):
            from exocortex.provider.oa_compat import OACompatAdapter

            adapter = OACompatAdapter(base_url="https://test.url", api_key="test-key")
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
            )
            assert text == "Hello world!"
            assert stats.model == "gpt-4o"
            assert stats.prompt_tokens == 5
            assert stats.completion_tokens == 3

    def test_empty_response_raises(self):
        mock_response = type(
            "MockChoice",
            (),
            {
                "message": type("MockMsg", (), {"content": ""})(),
            },
        )()
        mock_completion = type(
            "MockCompletion",
            (),
            {
                "choices": [mock_response],
                "model": "gpt-4o",
                "usage": type(
                    "MockUsage", (), {"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1}
                )(),
            },
        )()

        def fake_create(self, **kwargs):
            return mock_completion

        mock_openai = type(
            "MockOpenAI",
            (),
            {
                "chat": type(
                    "MockChat",
                    (),
                    {
                        "completions": type("MockCompletions", (), {"create": fake_create})(),
                    },
                )(),
                "api_key": "test-key",
                "base_url": "https://test.url",
            },
        )

        with patch("openai.OpenAI", return_value=mock_openai):
            from exocortex.errors import BadResponseError
            from exocortex.provider.oa_compat import OACompatAdapter

            adapter = OACompatAdapter(base_url="https://test.url", api_key="test-key")
            with pytest.raises(BadResponseError, match="Empty response"):
                adapter.complete(
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o",
                )

    def test_supports_model_always_true(self):
        from exocortex.provider.oa_compat import OACompatAdapter

        adapter = OACompatAdapter(base_url="https://test.url", api_key="test-key")
        assert adapter.supports_model("anything")
        assert adapter.supports_model("")

    def test_default_timeout_enforced(self):
        """Regression: timeout=None must not fall through to OpenAI SDK 60s default."""
        captured = {}

        def fake_openai_init(*args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            # Return a minimal mock that won't be used
            return type(
                "MockOpenAI",
                (),
                {
                    "chat": type(
                        "MockChat",
                        (),
                        {
                            "completions": type(
                                "MockCompletions",
                                (),
                                {
                                    "create": lambda self, **kw: type(
                                        "MockResponse",
                                        (),
                                        {
                                            "choices": [
                                                type(
                                                    "Choice",
                                                    (),
                                                    {
                                                        "message": type(
                                                            "Msg", (), {"content": "ok"}
                                                        )()
                                                    },
                                                )()
                                            ],
                                            "model": "gpt-4o",
                                            "usage": type(
                                                "Usage",
                                                (),
                                                {
                                                    "prompt_tokens": 1,
                                                    "completion_tokens": 1,
                                                    "total_tokens": 2,
                                                },
                                            )(),
                                        },
                                    )()
                                },
                            )()
                        },
                    )()
                },
            )()

        with patch("openai.OpenAI", side_effect=fake_openai_init):
            from exocortex.provider.oa_compat import OACompatAdapter

            adapter = OACompatAdapter(base_url="https://test.url", api_key="test-key")
            assert adapter._timeout == 180.0
            adapter.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
            )
            assert captured["timeout"] == 180.0

    def test_connection_error_retries(self):
        """openai.APIConnectionError should raise RetryableError and be retried."""
        import openai
        from exocortex.provider.oa_compat import OACompatAdapter

        call_count = 0

        mock_response = type(
            "MockChoice",
            (),
            {
                "message": type("MockMsg", (), {"content": "ok after retry"})(),
            },
        )()
        mock_completion = type(
            "MockCompletion",
            (),
            {
                "choices": [mock_response],
                "model": "gpt-4o",
                "usage": type(
                    "MockUsage", (), {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
                )(),
            },
        )()

        def fake_create(self, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise openai.APIConnectionError(request=type("Req", (), {})())
            return mock_completion

        mock_openai = type(
            "MockOpenAI",
            (),
            {
                "chat": type(
                    "MockChat",
                    (),
                    {
                        "completions": type("MockCompletions", (), {"create": fake_create})(),
                    },
                )(),
                "api_key": "test-key",
                "base_url": "https://test.url",
            },
        )()

        with patch("openai.OpenAI", return_value=mock_openai):
            adapter = OACompatAdapter(base_url="https://test.url", api_key="test-key")
            text, stats = adapter.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
                retries=2,
            )
            assert text == "ok after retry"
            assert call_count == 2
