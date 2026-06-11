"""Tests for brain.context module — context injection and message assembly."""

import pytest

from brain.context import assemble_messages, build_context_block


class TestBuildContextBlock:
    """Context block must wrap content in <context> tags."""

    def test_inline_context(self):
        result = build_context_block(context="Price: $50")
        assert result is not None
        assert "<context>" in result
        assert "Price: $50" in result
        assert "</context>" in result

    def test_file_context(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("File content here")
        result = build_context_block(context_file=str(f))
        assert "File content here" in result

    def test_file_not_found(self):
        with pytest.raises(Exception, match="not found"):
            build_context_block(context_file="/nonexistent/path.txt")

    def test_stdin_context(self, monkeypatch):
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("piped data"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        result = build_context_block(stdin_context=True)
        assert "piped data" in result

    def test_stdin_tty_skipped(self, monkeypatch):
        """If stdin is a tty (no pipe), skip silently."""
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        result = build_context_block(stdin_context=True)
        assert result is None

    def test_no_context_returns_none(self):
        result = build_context_block()
        assert result is None

    def test_metadata_key_value(self):
        result = build_context_block(metadata=["env=prod", "version=2"])
        assert "env=prod" in result
        assert "version=2" in result

    def test_metadata_bad_format(self):
        with pytest.raises(Exception, match="KEY=VALUE"):
            build_context_block(metadata=["badformat"])

    def test_combined_sources(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("file data")
        result = build_context_block(context="inline", context_file=str(f))
        assert "inline" in result
        assert "file data" in result


class TestAssembleMessages:
    """Message assembly must produce correct OpenAI API format."""

    def test_basic_prompt(self):
        msgs = assemble_messages(prompt="What is 2+2?")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert "What is 2+2?" in msgs[0]["content"]

    def test_with_context(self):
        ctx = build_context_block(context="Budget: $100")
        msgs = assemble_messages(prompt="Is this a good deal?", context_block=ctx)
        user_content = msgs[0]["content"]
        assert "<context>" in user_content
        assert "Budget: $100" in user_content

    def test_raw_mode_no_system(self):
        """Raw mode should skip system prompt."""
        msgs = assemble_messages(
            prompt="test",
            system_prompt="You are helpful",
            raw=True,
        )
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_no_system_prompt(self):
        """Without system_prompt, only user message."""
        msgs = assemble_messages(prompt="test", system_prompt=None)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    def test_context_before_prompt(self):
        """Context should appear before the prompt in user message."""
        ctx = "<context>\nctx data\n</context>"
        msgs = assemble_messages(prompt="my question", context_block=ctx)
        user = msgs[0]["content"]
        idx_ctx = user.find("ctx data")
        idx_prompt = user.find("my question")
        assert idx_ctx < idx_prompt, "context should precede prompt"

    def test_article_comment_example_file(self, tmp_path):
        """Article comment: brain think "Critique this logic" --context-file src/app.ts --profile critic"""
        f = tmp_path / "app.ts"
        f.write_text("function foo() { return 1; }")
        ctx = build_context_block(context_file=str(f))
        msgs = assemble_messages(prompt="Critique this logic", context_block=ctx)
        assert "function foo()" in msgs[0]["content"]

    def test_article_comment_example_stdin(self, monkeypatch):
        """Article comment: cat error.log | brain think "Why did this fail?" --stdin-context --profile reasoning"""
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO("ERROR: connection refused"))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        ctx = build_context_block(stdin_context=True)
        msgs = assemble_messages(prompt="Why did this fail?", context_block=ctx)
        assert "connection refused" in msgs[0]["content"]
