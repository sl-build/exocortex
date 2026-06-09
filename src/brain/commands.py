"""Brain CLI v2 — Command handlers (think, key, key-set)."""

from __future__ import annotations

from .client import call_and_print
from .config import get_default_model as get_config_model
from .config import get_default_provider, load_config, save_config
from .context import build_context_block
from .depth import VALID_DEPTHS
from .errors import InputError
from .keys import PROFILE_ENV, VALID_PROVIDERS, find_key_source, set_api_key
from .profiles import (
    PROFILE_PROMPTS,
    add_profile,
    get_all_profiles,
    get_profile_details,
    get_valid_profile_names,
    remove_profile,
)


def cmd_think(
    prompt: str,
    *,
    model: str | None = None,
    provider: str | None = None,
    profile: str | None = None,
    context: str | None = None,
    context_file: str | None = None,
    stdin_context: bool = False,
    metadata: list[str] | None = None,
    depth: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    raw: bool = False,
    json_output: bool = False,
    show_stats: bool = False,
) -> str:
    """Handle the 'think' subcommand."""
    valid_profiles = get_valid_profile_names()
    if profile and profile not in valid_profiles:
        raise InputError(f"Unknown profile: {profile}. Valid: {', '.join(valid_profiles)}")

    if depth and depth not in VALID_DEPTHS:
        raise InputError(f"Unknown depth: {depth}. Valid: {', '.join(VALID_DEPTHS)}")

    # Resolve provider and model from config if not given
    provider = provider or get_default_provider()
    if model is None:
        model = get_config_model()

    context_block = build_context_block(
        context=context,
        context_file=context_file,
        stdin_context=stdin_context,
        metadata=metadata,
    )

    return call_and_print(
        prompt=prompt,
        model=model,
        provider=provider,
        context_block=context_block,
        depth=depth,
        max_tokens=max_tokens,
        temperature=temperature,
        profile=profile,
        raw=raw,
        json_output=json_output,
        show_stats=show_stats,
    )


def cmd_key() -> None:
    """Handle the 'key' subcommand — show key location and masked value."""
    config = load_config()
    source = find_key_source(config["provider"])
    if source is None:
        print("No key found. Use: brain key-set <key_value>")
        print('Or set interactively: brain think "hello"')
        print(f"Or edit: {PROFILE_ENV}")
        return

    key, path = source
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"

    if path:
        print(f"Found in {path}: {masked}")
    else:
        print(f"Found in env var: {masked}")


def cmd_key_set(key_value: str) -> None:
    """Handle the 'key-set' subcommand — save API key."""
    key_value = key_value.strip()
    if not key_value:
        raise InputError("Empty key. Aborting.")

    config = load_config()
    path = set_api_key(key_value, provider=config["provider"])
    print(f"Key saved to {path}")


def cmd_profiles() -> str:
    """List available reasoning profiles."""
    lines = ["Available reasoning profiles:", ""]
    for name, cfg in get_all_profiles().items():
        source = "built-in" if name in PROFILE_PROMPTS else "user"
        lines.append(
            f"  {name} ({source}): depth={cfg['default_depth']}, temp={cfg['default_temperature']}"
        )
        lines.append(f"    {cfg['system_prompt'][:80]}...")
    result = "\n".join(lines)
    print(result)
    return result


def cmd_profile_add(name: str, system_prompt: str, depth: str, temperature: float) -> None:
    """Add a user profile."""
    add_profile(name, system_prompt, depth, temperature)
    print(f"Added user profile '{name}'")


def cmd_profile_remove(name: str) -> None:
    """Remove a user profile."""
    remove_profile(name)
    print(f"Removed user profile '{name}'")


def cmd_profile_show(name: str) -> None:
    """Show profile details."""
    details = get_profile_details(name)
    if details is None:
        raise InputError(f"Unknown profile: {name}")
    print(f"Profile: {name}")
    print(f"Source: {details['source']}")
    print(f"Depth: {details['default_depth']}")
    print(f"Temperature: {details['default_temperature']}")
    print(f"System prompt:\n{details['system_prompt']}")


def cmd_config() -> None:
    """Show current configuration."""
    config = load_config()
    print(f"provider: {config['provider']}")
    model = config["model"]
    print(f"model: {model if model else '(provider default)'}")


def cmd_config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    if key not in ("provider", "model"):
        raise InputError(f"Unknown config key: {key}. Valid: provider, model")

    if key == "provider" and value not in VALID_PROVIDERS:
        raise InputError(f"Unknown provider: {value}. Valid: {', '.join(VALID_PROVIDERS)}")

    save_config(key, value)
    print(f"Set {key} = {value if value else '(empty)'}")
