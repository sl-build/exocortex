"""Brain CLI v2 — API key management with multi-provider support."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import InputError

# ── config ──────────────────────────────────────────────────────
PROFILE_ENV = Path.home() / ".hermes" / "profiles" / "goose" / ".env"
GLOBAL_ENV = Path.home() / ".hermes" / ".env"

# ── provider definitions ────────────────────────────────────────
PROVIDERS: dict[str, dict] = {
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-5.5",
        "key_url": "https://openrouter.ai/keys",
        "label": "OpenRouter",
    },
    "opencode_go": {
        "env_var": "OPENCODE_GO_API_KEY",
        "base_url": "https://opencode.ai/zen/go/v1",
        "default_model": "qwen-3.7-max",
        "key_url": "https://opencode.ai/auth",
        "label": "OpenCode Go",
    },
}

VALID_PROVIDERS = list(PROVIDERS.keys())


def _find_var_in_file(path: Path, var_name: str) -> str | None:
    """Extract var_name=value from a .env file, skipping comments and blanks."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if line.startswith(f"{var_name}="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                return val
    return None


def _save_var_to_file(path: Path, var_name: str, value: str) -> None:
    """Ensure var_name=value exists in .env file, creating if needed."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{var_name}={value}\n")
        return

    lines = path.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{var_name}=") and not stripped.startswith("#") or stripped.startswith(f"#{var_name}="):
            new_lines.append(f"{var_name}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{var_name}={value}")

    path.write_text("\n".join(new_lines) + "\n")


# ── backward-compatible v1 functions ────────────────────────────
KEY_NAME = "OPENROUTER_API_KEY"


def _find_key_in_file(path: Path) -> str | None:
    """Extract OPENROUTER_API_KEY from a .env file (v1 compat)."""
    return _find_var_in_file(path, KEY_NAME)


def _save_key_to_file(path: Path, key: str) -> None:
    """Save OPENROUTER_API_KEY to a .env file (v1 compat)."""
    _save_var_to_file(path, KEY_NAME, key)


# ── multi-provider key resolution ───────────────────────────────

def get_api_key(provider: str = "openrouter") -> str:
    """Get API key for a provider.

    Lookup order: explicit env var → BRAIN_API_KEY → .env files → fallback env var.
    """
    prov = PROVIDERS.get(provider)
    if not prov:
        raise InputError(f"Unknown provider: {provider}. Valid: {', '.join(VALID_PROVIDERS)}")

    env_var = prov["env_var"]

    # 1. Provider-specific env var
    key = os.environ.get(env_var, "").strip()
    if key:
        return key

    # 2. Generic BRAIN_API_KEY
    key = os.environ.get("BRAIN_API_KEY", "").strip()
    if key:
        return key

    # 3. Profile .env (provider-specific var)
    key = _find_var_in_file(PROFILE_ENV, env_var)
    if key:
        return key

    # 4. Global .env (provider-specific var)
    key = _find_var_in_file(GLOBAL_ENV, env_var)
    if key:
        return key

    # 5. OpenRouter fallback (v1 compat)
    if provider != "openrouter":
        key = _find_var_in_file(PROFILE_ENV, "OPENROUTER_API_KEY")
        if key:
            return key
        key = _find_var_in_file(GLOBAL_ENV, "OPENROUTER_API_KEY")
        if key:
            return key
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if key:
            return key

    # 6. Interactive prompt
    print(f"{env_var} not found in .env files or environment.", file=sys.stderr)
    print(f"Get your key at: {prov['key_url']}", file=sys.stderr)
    try:
        key = input(f"Enter {env_var}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)

    if not key:
        print("Empty key provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Save to profile .env
    _save_var_to_file(PROFILE_ENV, env_var, key)
    print(f"Key saved to {PROFILE_ENV}", file=sys.stderr)
    return key


def set_api_key(key: str, provider: str = "openrouter") -> Path:
    """Save API key for a provider to profile .env."""
    key = key.strip()
    if not key:
        raise InputError("Empty key. Aborting.")

    env_var = PROVIDERS[provider]["env_var"]
    _save_var_to_file(PROFILE_ENV, env_var, key)
    return PROFILE_ENV


def find_key_source(provider: str = "openrouter") -> tuple[str, Path | None] | None:
    """Return (key_value, source_path_or_None) if found, else None."""
    prov = PROVIDERS[provider]
    env_var = prov["env_var"]

    # Check .env files
    for path in [PROFILE_ENV, GLOBAL_ENV]:
        key = _find_var_in_file(path, env_var)
        if key:
            return key, path

    # Check env var
    env_key = os.environ.get(env_var, "").strip()
    if env_key:
        return env_key, None

    return None


def get_base_url(provider: str) -> str:
    """Get default base URL for a provider."""
    prov = PROVIDERS.get(provider)
    if not prov:
        raise InputError(f"Unknown provider: {provider}. Valid: {', '.join(VALID_PROVIDERS)}")

    # Allow env var override
    env_url = os.environ.get(f"{provider.upper()}_BASE_URL", "").strip()
    if env_url:
        return env_url
    return prov["base_url"]


def get_default_model(provider: str) -> str:
    """Get default model for a provider."""
    prov = PROVIDERS.get(provider)
    if not prov:
        return PROVIDERS["openrouter"]["default_model"]
    return prov["default_model"]