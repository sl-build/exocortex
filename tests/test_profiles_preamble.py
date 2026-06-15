"""Exocortex CLI — Tests for external brain preamble and iteration limit."""

from __future__ import annotations

from exocortex.profiles import (
    EXTERNAL_BRAIN_PREAMBLE,
    MAX_BRAIN_ITERATIONS,
    PROFILE_PROMPTS,
)


def test_preamble_defines_external_brain_identity():
    """Preamble explicitly identifies the brain as external and called by a main agent."""
    assert "EXTERNAL REASONING BRAIN" in EXTERNAL_BRAIN_PREAMBLE
    assert "brain" in EXTERNAL_BRAIN_PREAMBLE
    assert "MAIN AGENT" in EXTERNAL_BRAIN_PREAMBLE


def test_preamble_has_ask_protocol():
    """Preamble documents the [ASK:] protocol for requesting missing info."""
    assert "[ASK:" in EXTERNAL_BRAIN_PREAMBLE


def test_preamble_has_iteration_limit():
    """Preamble contains a hard iteration limit with anti-loop instructions."""
    assert "AT MOST" in EXTERNAL_BRAIN_PREAMBLE
    assert "TIMES" in EXTERNAL_BRAIN_PREAMBLE
    assert "final iteration" in EXTERNAL_BRAIN_PREAMBLE


def test_preamble_has_no_tool_use_constraint():
    """Preamble forbids the brain from trying to use tools."""
    assert "tools" in EXTERNAL_BRAIN_PREAMBLE.lower()
    assert "Never attempt to call" in EXTERNAL_BRAIN_PREAMBLE or "you have none" in EXTERNAL_BRAIN_PREAMBLE


def test_max_iterations_default_is_3():
    """Default iteration limit is 3 (sane anti-loop default)."""
    assert MAX_BRAIN_ITERATIONS == 3
    assert MAX_BRAIN_ITERATIONS > 0
    assert isinstance(MAX_BRAIN_ITERATIONS, int)


def test_all_built_in_profiles_use_preamble():
    """Every built-in profile prepends the external brain preamble."""
    for name, profile in PROFILE_PROMPTS.items():
        prompt = profile["system_prompt"]
        assert prompt.startswith("You are the EXTERNAL REASONING BRAIN"), (
            f"Profile '{name}' does not start with the preamble. "
            f"Got: {prompt[:80]!r}"
        )


def test_all_built_in_profiles_have_ask_protocol():
    """Every profile can request missing info via [ASK:]."""
    for name, profile in PROFILE_PROMPTS.items():
        assert "[ASK:" in profile["system_prompt"], (
            f"Profile '{name}' missing [ASK:] protocol"
        )


def test_all_built_in_profiles_have_iteration_limit():
    """Every profile knows the iteration limit."""
    for name, profile in PROFILE_PROMPTS.items():
        prompt = profile["system_prompt"]
        assert "AT MOST 3 TIMES" in prompt, (
            f"Profile '{name}' missing iteration limit"
        )


def test_all_built_in_profiles_have_role_section():
    """Every profile has a # Your specific role section appended after the preamble."""
    for name, profile in PROFILE_PROMPTS.items():
        assert "# Your specific role" in profile["system_prompt"], (
            f"Profile '{name}' missing role section"
        )


def test_no_queue_profile():
    """The 'queue' profile (added by OMP, rejected by user) must not exist."""
    assert "queue" not in PROFILE_PROMPTS, (
        "Profile 'queue' should have been removed — the user asked for the "
        "preamble to apply to ALL profiles, not be a separate profile."
    )


def test_six_built_in_profiles():
    """Exactly 6 built-in profiles."""
    assert len(PROFILE_PROMPTS) == 6
    expected = {"reasoning", "critic", "planner", "judge", "extractor", "writer"}
    assert set(PROFILE_PROMPTS.keys()) == expected


def test_preamble_format_with_max_iterations():
    """EXTERNAL_BRAIN_PREAMBLE formats with max_iterations kwarg."""
    formatted = EXTERNAL_BRAIN_PREAMBLE.format(max_iterations=5)
    assert "AT MOST 5 TIMES" in formatted
