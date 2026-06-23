"""ExoBrain CLI — API key management with multi-provider support."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import InputError

# ── config ──────────────────────────────────────────────────────
PROFILE_ENV = Path.home() / ".hermes" / "profiles" / "goose" / ".env"
GLOBAL_ENV = Path.home() / ".hermes" / ".env"

# ── provider definitions ────────────────────────────────────────
BUILTIN_PROVIDERS: dict[str, dict] = {
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-5.5",
        "key_url": "https://openrouter.ai/keys",
        "label": "OpenRouter",
        "default_adapter": "oa_compat",
        "model_map": {},
    },
}


def get_custom_providers() -> dict[str, dict]:
    """Load custom providers from [providers] section in config.toml."""
    from .config import load_config

    config = load_config()
    custom = config.get("provider_config", {})
    result: dict[str, dict] = {}
    for name, cfg in custom.items():
        # Map type field to adapter name
        prov_type = cfg.get("type", "openai-compatible")
        default_adapter = "reasoning" if prov_type == "anthropic-compatible" else "oa_compat"
        result[name] = {
            "env_var": cfg.get("api_key_env", f"{name.upper()}_API_KEY"),
            "base_url": cfg.get("base_url", ""),
            "default_model": cfg.get("default_model", ""),
            "key_url": cfg.get("key_url", ""),
            "label": cfg.get("label", name),
            "type": prov_type,
            "default_adapter": cfg.get("default_adapter", default_adapter),
            "model_map": cfg.get("model_map", {}),
            "models": cfg.get("models", []),
        }
    return result


def get_all_providers() -> dict[str, dict]:
    """Return merged built-in + custom providers. Custom overrides built-in."""
    all_providers = dict(BUILTIN_PROVIDERS)
    all_providers.update(get_custom_providers())
    return all_providers


PROVIDERS = BUILTIN_PROVIDERS  # backward compat for direct imports

VALID_PROVIDERS = list(get_all_providers().keys())


def _find_var_in_file(path: Path, var_name: str) -> str | None:
    """Extract var_name=value from a .env file, skipping comments and blanks."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        # Accept both `VAR=value` and `export VAR=value` (the latter is common
        # in shell-sourced .env files like ~/.hermes/profiles/<active>/.env).
        if line.startswith(f"{var_name}=") or line.startswith(f"export {var_name}="):
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
        if (
            stripped.startswith(f"{var_name}=")
            and not stripped.startswith("#")
            or stripped.startswith(f"#{var_name}=")
        ):
            new_lines.append(f"{var_name}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{var_name}={value}")

    path.write_text("\n".join(new_lines) + "\n")

def get_api_key(provider: str = "openrouter") -> str:
    """Get API key for a provider.

    Lookup order: explicit env var → EXOBRAIN_API_KEY → .env files → fallback env var.
    """
    providers = get_all_providers()
    prov = providers.get(provider)
    if not prov:
        raise InputError(f"Unknown provider: {provider}. Valid: {', '.join(providers.keys())}")

    env_var = prov["env_var"]

    # 1. Provider-specific env var
    key = os.environ.get(env_var, "").strip()
    if key:
        return key

    # 2. Generic EXOBRAIN_API_KEY
    key = os.environ.get("EXOBRAIN_API_KEY", "").strip()
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

    providers = get_all_providers()
    env_var = providers[provider]["env_var"]
    _save_var_to_file(PROFILE_ENV, env_var, key)
    return PROFILE_ENV


def find_key_source(provider: str = "openrouter") -> tuple[str, Path | None] | None:
    """Return (key_value, source_path_or_None) if found, else None."""
    providers = get_all_providers()
    prov = providers[provider]
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
    providers = get_all_providers()
    prov = providers.get(provider)
    if not prov:
        raise InputError(f"Unknown provider: {provider}. Valid: {', '.join(providers.keys())}")

    # Allow env var override
    env_url = os.environ.get(f"{provider.upper()}_BASE_URL", "").strip()
    if env_url:
        return env_url
    return prov["base_url"]


def get_default_model(provider: str) -> str:
    """Get default model for a provider."""
    providers = get_all_providers()
    prov = providers.get(provider)
    if not prov:
        return providers["openrouter"]["default_model"]
    return prov["default_model"]


def get_adapter_name(provider: str, model: str) -> str:
    """Return adapter name for a model (from model_map or provider default)."""
    providers = get_all_providers()
    prov = providers.get(provider, {})
    model_map = prov.get("model_map", {})
    return model_map.get(model, prov.get("default_adapter", "oa_compat"))
