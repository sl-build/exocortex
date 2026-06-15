"""Exocortex CLI — Main entry point with argparse."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .commands import (
    cmd_config,
    cmd_config_set,
    cmd_init,
    cmd_key,
    cmd_key_set,
    cmd_plan,
    cmd_plan_block,
    cmd_plan_done,
    cmd_profile_add,
    cmd_profile_remove,
    cmd_profile_show,
    cmd_profiles,
    cmd_providers,
    cmd_status,
    cmd_think,
)
from .depth import VALID_DEPTHS
from .errors import (
    API_FAILURE,
    BAD_RESPONSE,
    INPUT_ERROR,
    SUCCESS,
    APIError,
    BadResponseError,
    BrainError,
    InputError,
)
from .keys import VALID_PROVIDERS
from .profiles import get_valid_profile_names

DEFAULT_MAX_TOKENS = 16384


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="exocortex",
        description="Exocortex CLI — Reasoning engine for agents",
    )
    parser.add_argument("--version", action="version", version=f"exocortex {__version__}")
    parser.add_argument("--session-id", default="", help="Session ID for plan isolation")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── think ──
    think_parser = subparsers.add_parser("think", help="Send a prompt to the reasoning engine")
    think_parser.add_argument("prompt", help="The prompt/question to think about")
    think_parser.add_argument("--session-id", default="", help="Session ID for plan isolation")
    think_parser.add_argument(
        "--provider", choices=VALID_PROVIDERS, help="Provider (default: openrouter)"
    )
    think_parser.add_argument(
        "--model", "-m", default=None, help="Model ID (default: from config or provider default)"
    )
    think_parser.add_argument(
        "--profile",
        "-p",
        choices=get_valid_profile_names(),
        help="Reasoning profile (see: brain profiles)",
    )
    think_parser.add_argument("--context", "-c", help="Inline context to include")
    think_parser.add_argument("--context-file", "-f", help="File with context to include")
    think_parser.add_argument(
        "--stdin-context", "-s", action="store_true", help="Read context from stdin"
    )
    think_parser.add_argument(
        "--metadata", "-M", action="append", help="Metadata key=value pairs (repeatable)"
    )
    think_parser.add_argument(
        "--depth", "-d", choices=VALID_DEPTHS, help="Reasoning depth: quick|normal|deep|exhaustive"
    )
    think_parser.add_argument(
        "--max-tokens",
        "-t",
        type=int,
        default=None,
        help=f"Max output tokens (default: {DEFAULT_MAX_TOKENS})",
    )
    think_parser.add_argument("--temperature", type=float, help="Override temperature")
    think_parser.add_argument(
        "--raw", "-r", action="store_true", help="Raw mode: no system prompt, just user message"
    )
    think_parser.add_argument(
        "--json", "-j", action="store_true", help="Strip code fences, output clean JSON"
    )
    think_parser.add_argument(
        "--stats", action="store_true", help="Show usage statistics on stderr"
    )
    think_parser.add_argument(
        "--raw-model",
        action="store_true",
        help="Use model name as-is, without provider prefix transformation",
    )
    think_parser.add_argument(
        "--plan",
        action="store_true",
        help="Create a structured plan using the planner profile",
    )
    think_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass gate and overwrite any existing plan",
    )
    think_parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Max agent-brain round-trips (default: 3 from config)",
    )

    # ── plan ──
    plan_parser = subparsers.add_parser("plan", help="Show current plan")
    plan_parser.add_argument("--session-id", default="", help="Session ID for plan isolation")
    plan_sub = plan_parser.add_subparsers(dest="plan_action")

    plan_sub.add_parser("done", help="Mark current step as done")
    plan_block_parser = plan_sub.add_parser("block", help="Mark current step as blocked")
    plan_block_parser.add_argument("reason", nargs="?", default=None, help="Reason for blocking")

    # ── key ──
    subparsers.add_parser("key", help="Show key location or set a new key")

    # ── key-set ──
    keyset_parser = subparsers.add_parser("key-set", help="Save API key to profile .env")
    keyset_parser.add_argument("key_value", help="The API key")

    # ── profiles ──
    subparsers.add_parser("profiles", help="List available reasoning profiles")

    # ── profile-add ──
    profile_add_parser = subparsers.add_parser("profile-add", help="Add a custom reasoning profile")
    profile_add_parser.add_argument("name", help="Profile name")
    profile_add_parser.add_argument("--prompt", required=True, help="System prompt")
    profile_add_parser.add_argument(
        "--depth", choices=VALID_DEPTHS, default="normal", help="Default depth (default: normal)"
    )
    profile_add_parser.add_argument(
        "--temp", type=float, default=0.3, help="Default temperature (default: 0.3)"
    )

    # ── profile-remove ──
    profile_remove_parser = subparsers.add_parser(
        "profile-remove", help="Remove a custom reasoning profile"
    )
    profile_remove_parser.add_argument("name", help="Profile name")

    # ── profile-show ──
    profile_show_parser = subparsers.add_parser("profile-show", help="Show profile details")
    profile_show_parser.add_argument("name", help="Profile name")

    # ── config ──
    subparsers.add_parser("config", help="Show current configuration")

    # ── config-set ──
    configset_parser = subparsers.add_parser("config-set", help="Set a config value")
    configset_parser.add_argument("key", help="Config key: provider|model|timeout")
    configset_parser.add_argument("value", help="Config value")

    # ── init ──
    subparsers.add_parser("init", help="Interactive setup wizard for first-time users")

    # ── status ──
    subparsers.add_parser("status", help="Show config and health status")

    # ── providers ──
    subparsers.add_parser("providers", help="List all available providers")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # No command given — friendly quickstart
    if not args.command:
        print("Exocortex CLI v" + __version__ + " — Reasoning engine for agents")
        print()
        print("First time? Run:  brain init")
        print()
        print("Common commands:")
        print('  brain think "your question"     ask the AI')
        print("  brain status                    show config + health")
        print("  brain providers                 list all providers")
        print("  brain config                    show current config")
        print("  brain key                       show API key location")
        print()
        print("Full help: brain --help")
        return SUCCESS

    try:
        if args.command == "think":
            cmd_think(
                prompt=args.prompt,
                model=args.model,
                provider=args.provider,
                profile=args.profile,
                context=args.context,
                context_file=args.context_file,
                stdin_context=args.stdin_context,
                metadata=args.metadata,
                depth=args.depth,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                raw=args.raw,
                json_output=args.json,
                show_stats=args.stats,
                raw_model=args.raw_model,
                plan_mode=args.plan,
                force=args.force,
                session_id=args.session_id,
                max_iterations=args.max_iterations,
            )
            return SUCCESS

        elif args.command == "plan":
            if args.plan_action == "done":
                cmd_plan_done(session_id=args.session_id)
            elif args.plan_action == "block":
                cmd_plan_block(args.reason, session_id=args.session_id)
            else:
                cmd_plan(session_id=args.session_id)
            return SUCCESS

        elif args.command == "key":
            cmd_key()
            return SUCCESS

        elif args.command == "key-set":
            cmd_key_set(args.key_value)
            return SUCCESS

        elif args.command == "profiles":
            cmd_profiles()
            return SUCCESS

        elif args.command == "profile-add":
            cmd_profile_add(
                name=args.name,
                system_prompt=args.prompt,
                depth=args.depth,
                temperature=args.temp,
            )
            return SUCCESS

        elif args.command == "profile-remove":
            cmd_profile_remove(args.name)
            return SUCCESS

        elif args.command == "profile-show":
            cmd_profile_show(args.name)
            return SUCCESS

        elif args.command == "config":
            cmd_config()
            return SUCCESS

        elif args.command == "config-set":
            cmd_config_set(args.key, args.value)
            return SUCCESS

        elif args.command == "init":
            cmd_init()
            return SUCCESS

        elif args.command == "status":
            cmd_status()
            return SUCCESS

        elif args.command == "providers":
            cmd_providers()
            return SUCCESS

        else:
            parser.print_help()
            return INPUT_ERROR

    except InputError as e:
        print(f"Error: {e}", file=sys.stderr)
        return INPUT_ERROR

    except APIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        return API_FAILURE

    except BadResponseError as e:
        print(f"Bad Response: {e}", file=sys.stderr)
        return BAD_RESPONSE

    except BrainError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


def cli_main():
    """Entry point for console_scripts."""
    sys.exit(main())


if __name__ == "__main__":
    cli_main()
