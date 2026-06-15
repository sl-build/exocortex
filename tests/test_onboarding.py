"""Tests for onboarding commands: init, status, providers."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import patch
from exocortex.commands import cmd_init, cmd_providers, cmd_status
import pytest

from exocortex.commands import cmd_providers, cmd_status
from exocortex.cli import main


class TestProviders:
    """Tests for cmd_providers."""

    def test_providers_lists_builtin(self, capsys):
        """Built-in openrouter provider is listed."""
        cmd_providers()
        out = capsys.readouterr().out
        assert "openrouter" in out
        assert "Built-in" in out
        assert "openai/gpt-5.5" in out

    def test_providers_includes_custom(self, mock_config_dir, capsys):
        """Custom providers from config.toml are listed."""
        # Write a config with a custom provider
        (mock_config_dir / "config.toml").write_text(
            '[defaults]\nprovider = "openrouter"\nmodel = ""\ntimeout = 180\n'
            "\n"
            "[providers.my_server]\n"
            'type = "openai-compatible"\n'
            'base_url = "https://my.server.com/v1"\n'
            'api_key_env = "MY_SERVER_KEY"\n'
            'default_model = "my-model-1"\n'
        )
        cmd_providers()
        out = capsys.readouterr().out
        assert "Custom" in out
        assert "my_server" in out
        assert "my-model-1" in out

    def test_providers_no_custom(self, mock_config_dir, capsys):
        """When no custom providers, shows helpful message."""
        cmd_providers()
        out = capsys.readouterr().out
        assert "No custom providers configured" in out


class TestStatus:
    """Tests for cmd_status."""

    def test_status_prints_config(self, capsys):
        """Status shows provider, model, timeout."""
        with patch("builtins.input", return_value="n"):
            cmd_status()
        out = capsys.readouterr().out
        assert "Current configuration:" in out
        assert "provider:" in out
        assert "model:" in out
        assert "timeout:" in out

    def test_status_lists_providers(self, capsys):
        """Status shows configured providers."""
        with patch("builtins.input", return_value="n"):
            cmd_status()
        out = capsys.readouterr().out
        assert "Configured providers" in out
        assert "openrouter" in out

    def test_status_shows_key_source(self, mock_env_files, capsys):
        """Status shows API key source when key exists."""
        mock_env_files.write_text("OPENROUTER_API_KEY=sk-test-123\n")
        with patch("builtins.input", return_value="n"):
            cmd_status()
        out = capsys.readouterr().out
        assert "API key:" in out

    def test_status_shows_key_missing(self, mock_env_files, capsys):
        """Status shows NOT FOUND when no key exists."""
        with patch("builtins.input", return_value="n"):
            cmd_status()
        out = capsys.readouterr().out
        assert "NOT FOUND" in out

    def test_status_skips_ping_on_no(self, mock_env_files, capsys):
        """Status skips ping when user answers N."""
        with patch("builtins.input", return_value="n"):
            cmd_status()
        out = capsys.readouterr().out
        assert "Sending test ping" not in out


class TestInit:
    """Tests for cmd_init."""

    def test_init_shows_welcome(self, capsys):
        """Init shows welcome banner."""
        with patch("builtins.input", side_effect=EOFError):
            cmd_init()
        out = capsys.readouterr().out
        assert "First-time setup" in out
        assert "====" in out

    def test_init_provider_choice_openrouter(self, mock_config_dir, mock_env_files, capsys):
        """Init with openrouter choice (option 1)."""
        inputs = iter(["1", "sk-test-key-123", "openai/gpt-4o"])
        with patch("builtins.input", side_effect=lambda *a: next(inputs)):
            with patch("exocortex.commands.call_and_print", return_value="OK"):
                cmd_init()
        out = capsys.readouterr().out
        assert "Setup complete" in out
        # Verify key was saved
        assert mock_env_files.exists()
        content = mock_env_files.read_text()
        assert "OPENROUTER_API_KEY=sk-test-key-123" in content

    def test_init_cancelled_on_eof(self, capsys):
        """Init handles EOFError gracefully."""
        with patch("builtins.input", side_effect=EOFError):
            cmd_init()
        out = capsys.readouterr().out
        assert "Cancelled" in out

    def test_init_existing_config_asks_reconfigure(self, mock_config_dir, mock_env_files, capsys):
        """Init asks to reconfigure when already set up."""
        # Set up existing config + key
        (mock_config_dir / "config.toml").write_text(
            '[defaults]\nprovider = "openrouter"\nmodel = "gpt-4o"\ntimeout = 180\n'
        )
        mock_env_files.write_text("OPENROUTER_API_KEY=sk-existing\n")
        # User says "n" to reconfigure
        with patch("builtins.input", return_value="n"):
            cmd_init()
        out = capsys.readouterr().out
        assert "Keeping existing" in out

    def test_init_invalid_choice(self, mock_config_dir, capsys):
        """Init rejects invalid provider choice."""
        with patch("builtins.input", return_value="3"):
            cmd_init()
        out = capsys.readouterr().out
        assert "Invalid choice" in out
class TestNoArgQuickstart:
    """Tests for no-arg brain command."""

    def test_no_args_shows_quickstart(self, capsys):
        """brain with no args shows friendly quickstart."""
        ret = main([])
        out = capsys.readouterr().out
        assert ret == 0
        assert "brain init" in out
        assert "brain think" in out
        assert "Common commands" in out

    def test_no_args_returns_success(self):
        """brain with no args returns exit code 0."""
        ret = main([])
        assert ret == 0

    def test_version_flag(self, capsys):
        """brain --version shows version string."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "0.2.3" in out
