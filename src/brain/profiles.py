"""Brain CLI v2 — Reasoning profiles for think command."""

from __future__ import annotations

import os

from .config import CONFIG_DIR

PROFILE_PROMPTS: dict[str, dict] = {
    "reasoning": {
        "system_prompt": (
            "You are a reasoning engine. You receive focused questions from an agent. "
            "Answer concisely and precisely. Do not ask clarifying questions — the agent "
            "has already gathered context. Do not suggest actions — the agent decides "
            "what to do. Return facts, analysis, and reasoning only."
        ),
        "default_depth": "normal",
        "default_temperature": 0.3,
    },
    "critic": {
        "system_prompt": (
            "You are a critical reviewer. Identify flaws, missing assumptions, and failure "
            "modes in the provided argument or plan. Be specific and constructive. Rate "
            "confidence 0-10."
        ),
        "default_depth": "deep",
        "default_temperature": 0.2,
    },
    "planner": {
        "system_prompt": (
            "You are a strategic planner. Given a goal, produce a step-by-step plan with "
            "dependencies, risks, and alternatives. Number each step. Include rollback options."
        ),
        "default_depth": "deep",
        "default_temperature": 0.3,
    },
    "judge": {
        "system_prompt": (
            "You are a decision judge. Given options A and B, evaluate each on: effectiveness, "
            "cost, risk, time. Produce a clear recommendation with confidence level."
        ),
        "default_depth": "normal",
        "default_temperature": 0.2,
    },
    "extractor": {
        "system_prompt": (
            "You are an information extractor. From the provided text, extract structured data: "
            "key facts, dates, quantities, relationships. Output in JSON format."
        ),
        "default_depth": "normal",
        "default_temperature": 0.1,
    },
    "writer": {
        "system_prompt": (
            "You are a writer. Be concise — every word earns its place. "
            "Cut fluff, filler, hedging, and repetition. Open strong: hook first, context second. "
            "Structure tightly: logical flow, no dead ends, memorable close. "
            "Build narrative — take the reader somewhere, each paragraph pulls forward. "
            "Expert tone without arrogance or hype. Write like you built it, not like you're selling it."
        ),
        "default_depth": "deep",
        "default_temperature": 0.5,
    },
}

PROFILES_FILE = CONFIG_DIR / "profiles.toml"


def _toml_string(val: str) -> str:
    """Return a TOML-safe quoted string."""
    if "\n" in val or '"' in val:
        escaped = val.replace("\\", "\\\\").replace('"""', '""""')
        return f'"""{escaped}"""'
    return f'"{val}"'


def load_user_profiles() -> dict[str, dict]:
    """Read user profiles from profiles.toml. Returns empty dict if file missing."""
    if not PROFILES_FILE.exists():
        return {}
    data = PROFILES_FILE.read_text(encoding="utf-8")
    import tomllib

    parsed = tomllib.loads(data)
    profiles = parsed.get("profiles", {})
    result: dict[str, dict] = {}
    for name, cfg in profiles.items():
        if not isinstance(cfg, dict):
            continue
        result[name] = {
            "system_prompt": cfg.get("system_prompt", ""),
            "default_depth": cfg.get("default_depth", "normal"),
            "default_temperature": cfg.get("default_temperature", 0.3),
        }
    return result


def save_user_profiles(profiles: dict) -> None:
    """Write user profiles to profiles.toml atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, cfg in profiles.items():
        lines.append(f"[profiles.{name}]")
        lines.append(f"system_prompt = {_toml_string(cfg['system_prompt'])}")
        lines.append(f"default_depth = {_toml_string(cfg['default_depth'])}")
        lines.append(f"default_temperature = {cfg['default_temperature']}")
        lines.append("")
    tmp = PROFILES_FILE.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, PROFILES_FILE)


def get_all_profiles() -> dict[str, dict]:
    """Return built-in profiles merged with user profiles. Built-ins win on collision."""
    all_profiles = dict(PROFILE_PROMPTS)
    for name, cfg in load_user_profiles().items():
        if name not in all_profiles:
            all_profiles[name] = cfg
    return all_profiles


def get_valid_profile_names() -> list[str]:
    """Return all valid profile names (built-in + user)."""
    return list(get_all_profiles().keys())


def add_profile(name: str, system_prompt: str, depth: str, temperature: float) -> None:
    """Add or update a user profile. Rejects built-in names."""
    if name in PROFILE_PROMPTS:
        raise ValueError(f"Cannot override built-in profile: {name}")
    profiles = load_user_profiles()
    profiles[name] = {
        "system_prompt": system_prompt,
        "default_depth": depth,
        "default_temperature": temperature,
    }
    save_user_profiles(profiles)


def remove_profile(name: str) -> None:
    """Remove a user profile. Rejects built-in names."""
    if name in PROFILE_PROMPTS:
        raise ValueError(f"Cannot remove built-in profile: {name}")
    profiles = load_user_profiles()
    if name not in profiles:
        raise KeyError(f"User profile not found: {name}")
    del profiles[name]
    save_user_profiles(profiles)


def get_profile_details(name: str) -> dict | None:
    """Return profile dict with 'source' key, or None if not found."""
    if name in PROFILE_PROMPTS:
        return {**PROFILE_PROMPTS[name], "source": "builtin"}
    user_profiles = load_user_profiles()
    if name in user_profiles:
        return {**user_profiles[name], "source": "user"}
    return None
