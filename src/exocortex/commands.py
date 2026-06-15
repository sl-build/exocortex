"""Exocortex CLI — Command handlers (think, plan, key)."""

from __future__ import annotations

import json

from .client import call_and_print
from .config import get_default_model as get_config_model
from .config import get_max_iterations
from .config import get_default_provider, load_config, save_config, save_provider_config
from .context import build_context_block
from .depth import VALID_DEPTHS
from .errors import InputError
from .keys import (
    BUILTIN_PROVIDERS,
    PROFILE_ENV,
    VALID_PROVIDERS,
    find_key_source,
    get_all_providers,
    get_custom_providers,
    set_api_key,
)
from .profiles import (
    PROFILE_PROMPTS,
    add_profile,
    get_all_profiles,
    get_profile_details,
    get_valid_profile_names,
    remove_profile,
)
from .state import create_plan, delete_plan, load_plan, mark_blocked, mark_done, save_plan


def _parse_plan_json(raw_response: str) -> list[str]:
    stripped = raw_response.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        raise InputError(
            f"Planner did not return valid JSON. Raw response:\n{raw_response[:500]}"
        ) from None
    if not isinstance(data, dict) or "steps" not in data:
        raise InputError(f'Planner JSON missing "steps" key. Got: {json.dumps(data)[:200]}')
    steps = data["steps"]
    if not isinstance(steps, list) or len(steps) == 0:
        raise InputError("Planner returned empty steps array")
    return [s["title"] for s in steps]


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
    raw_model: bool = False,
    plan_mode: bool = False,
    force: bool = False,
    session_id: str = "",
    max_iterations: int | None = None,
) -> str:
    """Handle the 'think' subcommand."""
    if plan_mode and force:
        raise InputError("Cannot use both --plan and --force together")

    valid_profiles = get_valid_profile_names()
    if profile and profile not in valid_profiles:
        raise InputError(f"Unknown profile: {profile}. Valid: {', '.join(valid_profiles)}")

    if depth and depth not in VALID_DEPTHS:
        raise InputError(f"Unknown depth: {depth}. Valid: {', '.join(VALID_DEPTHS)}")

    provider = provider or get_default_provider()
    if model is None:
        model = get_config_model()

    context_block = build_context_block(
        context=context,
        context_file=context_file,
        stdin_context=stdin_context,
        metadata=metadata,
    )

    effective_profile = profile
    effective_json = json_output
    if plan_mode:
        effective_profile = "planner"
        effective_json = True
    response = call_and_print(
        prompt=prompt,
        model=model,
        provider=provider,
        context_block=context_block,
        depth=depth,
        max_tokens=max_tokens,
        temperature=temperature,
        profile=effective_profile,
        raw=raw,
        json_output=effective_json,
        show_stats=show_stats,
        raw_model=raw_model,
        suppress_print=plan_mode,
    )

    if plan_mode:
        try:
            outer = json.loads(response)
            if isinstance(outer, dict) and "response" in outer:
                response = outer["response"]
        except json.JSONDecodeError:
            pass
        steps = _parse_plan_json(response)
        plan = create_plan(prompt, steps, session_id)
        save_plan(plan)
        print("\n--- Plan saved ---")
        _print_plan(plan)
    elif force:
        delete_plan(session_id)
        plan = create_plan(prompt, [response.strip()], session_id)
        save_plan(plan)
        print("\n--- Plan overwritten (force) ---")
        _print_plan(plan)

    return response


def _print_plan(plan) -> None:
    status_icons = {"pending": "○", "in_progress": "●", "done": "✔", "blocked": "✗"}
    print(f"\nPlan: {plan.prompt}")
    for i, step in enumerate(plan.steps):
        icon = status_icons.get(step.status, "?")
        marker = " ←" if i == plan.current_step else ""
        print(f"  {icon} {step.title}{marker}")
    if plan.current_step >= len(plan.steps):
        print("  ✓ All steps complete")


def cmd_plan(session_id: str = "") -> str:
    plan = load_plan(session_id)
    if plan is None:
        print("No active plan.")
        return "No active plan."
    _print_plan(plan)
    return ""


def cmd_plan_done(session_id: str = "") -> str:
    plan = mark_done(session_id)
    if plan is None:
        print("No active plan to mark done.")
        return "No active plan."
    if plan.current_step >= len(plan.steps):
        print("All steps complete.")
        delete_plan(session_id)
    else:
        next_step = plan.steps[plan.current_step]
        print(f"Step done. Next: {next_step.title}")
    return ""


def cmd_plan_block(reason: str | None = None, session_id: str = "") -> str:
    plan = mark_blocked(reason or "", session_id)
    if plan is None:
        print("No active plan to block.")
        return "No active plan."
    step = plan.steps[plan.current_step]
    print(f"Blocked: {step.title}")
    return ""


def cmd_key() -> None:
    """Handle the 'key' subcommand — show key location and masked value."""
    config = load_config()
    source = find_key_source(config["provider"])
    if source is None:
        print("No key found. Use: exocortex key-set <key_value>")
        print('Or set interactively: exocortex think "hello"')
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
    print(f"timeout: {config.get('timeout', 180)}")

def cmd_config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    if key not in ("provider", "model", "timeout"):
        raise InputError(f"Unknown config key: {key}. Valid: provider, model, timeout")

    if key == "provider" and value not in VALID_PROVIDERS:
        raise InputError(f"Unknown provider: {value}. Valid: {', '.join(VALID_PROVIDERS)}")

    save_config(key, value)
    print(f"Set {key} = {value if value else '(empty)'}")

def cmd_providers() -> None:
    """List all available providers (built-in + custom)."""
    all_providers = get_all_providers()
    custom = get_custom_providers()

    # Built-in section
    print("Built-in providers:")
    print(f"  {'Name':<15} {'Type':<20} {'Default model':<30} {'Base URL'}")
    print(f"  {'─'*15} {'─'*20} {'─'*30} {'─'*40}")
    for name, prov in BUILTIN_PROVIDERS.items():
        print(
            f"  {name:<15} {'openai-compatible':<20} "
            f"{prov['default_model']:<30} {prov['base_url']}"
        )

    # Custom section
    if custom:
        print()
        print("Custom providers:")
        print(f"  {'Name':<15} {'Type':<20} {'Default model':<30} {'Base URL'}")
        print(f"  {'─'*15} {'─'*20} {'─'*30} {'─'*40}")
        for name, prov in custom.items():
            prov_type = prov.get("type", "openai-compatible")
            print(
                f"  {name:<15} {prov_type:<20} "
                f"{prov['default_model']:<30} {prov['base_url']}"
            )
    else:
        print()
        print("No custom providers configured.")
        print("Use 'brain init' to add one.")


def cmd_status() -> None:
    """Show current config and health status."""
    config = load_config()
    provider = config["provider"]
    model = config.get("model", "")
    timeout = config.get("timeout", 180)

    print("Current configuration:")
    print(f"  provider: {provider}")
    print(f"  model:    {model if model else '(provider default)'}")
    print(f"  timeout:  {timeout}")

    # Key source
    key_info = find_key_source(provider)
    if key_info:
        _, source = key_info
        if source:
            print(f"  API key:  found in {source}")
        else:
            print(f"  API key:  found in environment")
    else:
        print(f"  API key:  NOT FOUND")

    # Provider summary
    all_providers = get_all_providers()
    print()
    print(f"Configured providers ({len(all_providers)}):")
    for name, prov in all_providers.items():
        marker = " (active)" if name == provider else ""
        print(f"  {name}: {prov['default_model']}{marker}")

    # Quick test offer
    print()
    try:
        answer = input("Send test ping to current provider? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if answer == "y":
        print("Sending test ping...")
        try:
            response = call_and_print(
                prompt="Reply with the word OK and nothing else.",
                provider=provider,
                model=model or None,
                max_tokens=10,
            )
            print(f"✓ Provider responded: {response.strip()[:50]}")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            print("  Check your API key with: brain key")


def cmd_init() -> None:
    """Interactive setup wizard for first-time users."""
    print("Exocortex CLI — First-time setup")
    print("================================")
    print()

    # Detect existing state
    config = load_config()
    existing_provider = config.get("provider", "")
    key_info = find_key_source(existing_provider) if existing_provider else None
    configured = existing_provider and key_info is not None

    if configured:
        try:
            answer = input("Already configured. Reconfigure? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if answer != "y":
            print("Keeping existing configuration.")
            return

    # Provider choice
    print("Choose default provider:")
    print("  1. openrouter (built-in, 300+ models)")
    print("  2. Custom provider (OpenAI-compatible or Anthropic-compatible)")
    print()
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if choice == "1":
        # OpenRouter setup
        print()
        try:
            api_key = input("Enter OpenRouter API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not api_key:
            print("Empty key. Aborting.")
            return

        set_api_key(api_key, "openrouter")
        print(f"Key saved to {PROFILE_ENV}")

        # Default model
        try:
            model = input("Default model [openai/gpt-5.5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not model:
            model = "openai/gpt-5.5"

        save_config("model", model)
        save_config("provider", "openrouter")
        chosen_provider = "openrouter"
        chosen_model = model

    elif choice == "2":
        # Custom provider setup
        print()
        try:
            name = input("Provider name (alphanumeric+underscore): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not name:
            print("Empty name. Aborting.")
            return

        print("Provider type:")
        print("  1. openai-compatible")
        print("  2. anthropic-compatible")
        try:
            type_choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

        provider_type = "openai-compatible" if type_choice == "1" else "anthropic-compatible"

        try:
            base_url = input("Base URL: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not base_url:
            print("Empty URL. Aborting.")
            return

        try:
            api_key_env = input(f"Env var name for API key [{name.upper()}_API_KEY]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not api_key_env:
            api_key_env = f"{name.upper()}_API_KEY"

        try:
            default_model = input("Default model: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not default_model:
            print("Empty model. Aborting.")
            return

        save_provider_config(name, provider_type, base_url, api_key_env, default_model)
        save_config("provider", name)
        save_config("model", default_model)
        chosen_provider = name
        chosen_model = default_model
        print(f"Provider '{name}' configured.")

    else:
        print("Invalid choice. Use 1 or 2.")
        return

    # Test connection
    print()
    print("Testing connection...")
    try:
        response = call_and_print(
            prompt="Reply with the word OK and nothing else.",
            provider=chosen_provider,
            model=chosen_model,
            max_tokens=10,
        )
        print(f"✓ Setup complete. Try: brain think \"hello\"")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        print("  Check your API key with: brain key")
