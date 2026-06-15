# Exocortex CLI v0.2.1 — Reasoning Engine for AI Agents

[![PyPI version](https://img.shields.io/pypi/v/exocortex)](https://pypi.org/project/exocortex/)

Exocortex CLI is an exocortex for AI agents. It sends prompts to reasoning models (OpenAI, Anthropic, Gemini, DeepSeek, Qwen) via OpenRouter or custom providers and returns the response. Can be used as an MCP tool or standalone.

## Quick Start

```bash
pip install exocortex
export OPENROUTER_API_KEY=***
exocortex think "How does async/await work in Python?"
```

> **Backward compat:** `brain` is a symlink to `exocortex`. Both work identically.

## Usage

- `exocortex think "prompt"` — basic
- `exocortex think "prompt" --model gpt-4o --depth deep` — with model and depth
- `exocortex think "prompt" --context "context"` — with context
- `exocortex think "prompt" --context-file file.txt` — from file
- `cat log.txt | exocortex think "why?" --stdin-context` — from stdin
- `exocortex think "prompt" --json` — JSON response
- `exocortex think "prompt" --stats` — with stats
- `exocortex think "prompt" --plan` — planning mode
- `exocortex think "prompt" --session-id my-session` — multi-session

## Plan Management

- `exocortex plan` — show plan
- `exocortex plan --mark-done` — mark step done
- `exocortex plan --block` — block step

## Config

```bash
exocortex config                        # show current config
exocortex config-set provider openrouter
exocortex config-set model gpt-4o
exocortex config-set timeout 300        # seconds (default: 180)
```

Config is stored in `~/.config/exocortex/config.toml`.

## Providers

**Built-in:** `openrouter` (default).

**Custom providers** are configured in `~/.config/exocortex/config.toml`:

```toml
[providers.opencode_go]
type = "anthropic-compatible"           # or "openai-compatible"
base_url = "https://opencode.ai/zen/go/v1"
api_key_env = "OPENCODE_GO_API_KEY"
models = ["qwen3.7-max", "qwen3.6-plus"]
default_model = "qwen3.7-max"
```

Then use: `exocortex think "..." --provider opencode_go --model qwen3.7-max`.

The `--model` value is scoped to the chosen provider — no global `provider/model` syntax.

## Depth Presets

- `quick` — fast, shallow (4096 tokens)
- `normal` (default) — balanced (8192 tokens)
- `deep` — deep reasoning (16384 tokens)
- `exhaustive` — max reasoning (32768 tokens)

## Profiles

Six built-in profiles: reasoning, writer, planner, critic, research, creative.

Custom profiles:

```bash
exocortex profile-add my-profile template=reasoning model=qwen-max-0125
exocortex profiles
exocortex profile-remove my-profile
```

## Hermes Plugin (optional, experimental)

Exocortex CLI can be connected to a Hermes agent. See plugin/README.md.

The plugin registers Hermes tool identifiers (`brain_think`, `brain_plan_done`, etc.) that remain unchanged for compatibility with existing agent configurations.

Note: not included in the pip package; installed separately.

## Install

```bash
pip install exocortex
```

For Hermes Agent: `pip install exocortex hermes` (plugin not included, see plugin/README.md)

## Requirements

Python 3.11+, API key from OpenRouter (openrouter.ai/keys)

## License

MIT
