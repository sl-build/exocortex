# ExoBrain CLI v0.2.5 — Reasoning Engine

> **Agents:** see [`llms.txt`](llms.txt) for machine-readable setup instructions.

[![PyPI version](https://img.shields.io/pypi/v/exobrain-cli.svg?v=1)](https://pypi.org/project/exobrain-cli/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

ExoBrain gives your agent a clean context window to think — a dedicated reasoning sidekick that runs a focused prompt without the noise of the main conversation.

---

## Install

```bash
# Recommended (uv — fast, isolated)
uv tool install exobrain-cli

# Or via pipx (also isolated)
pipx install exobrain-cli

# Or via pip (system-wide, not isolated)
pip install exobrain-cli

# Or from source
git clone https://github.com/sl-build/exobrain.git
cd exobrain
uv pip install -e .
```

Verify: `exobrain --version` should print `exobrain 0.2.x`.

### Quick start for agents

The fastest way to give your agent a reasoning engine:

1. Install: `uv tool install exobrain-cli`
2. Set your API key: `exobrain init`
3. Add to your agent's `SOUL.md` (or system prompt):

```markdown
You have an external reasoning engine. Use `exobrain think "..."` for complex reasoning,
planning, and analysis.
```

That's it. The agent will call `exobrain think` when it needs deeper reasoning.

For more control, see the [ExoBrain skill](skills/exobrain.md) (optional, recommended).

### Get an API key

You need at least one provider key. The default is **OpenRouter** (one key gives access to 300+ models).

- **OpenRouter**: https://openrouter.ai/keys — format `sk-or-v1-...`
- **Any OpenAI-compatible or Anthropic-compatible endpoint** — your own

### Run the setup wizard

```bash
exobrain init
```

This walks you through provider choice, key entry, default model, and tests the connection.

**Or do it manually** (non-interactive):

```bash
# 1. Save key to your .env file
export OPENROUTER_API_KEY="sk-or-v1-..."

# 2. Optional: set default model and timeout
exobrain config-set model openai/gpt-4o
exobrain config-set timeout 300   # seconds, default 180

# 3. Verify
exobrain status
exobrain providers
exobrain think "Reply with OK" --raw
```

### Use it

```bash
exobrain think "How does async/await work in Python?"
exobrain think "Explain this code" --context-file main.py
cat error.log | exobrain think "Why did this fail?" --stdin-context
```

---

## CLI Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `exobrain` | Quickstart / help |
| `exobrain init` | Interactive first-time setup wizard |
| `exobrain status` | Show config + key source + provider health |
| `exobrain providers` | List all configured providers |
| `exobrain config` | Show current config |
| `exobrain config-set <key> <value>` | Set `provider`, `model`, or `timeout` |
| `exobrain think <prompt>` | Send prompt to the reasoning engine |
| `exobrain plan` / `exobrain plan done` / `exobrain plan block` | Manage structured plans |
| `exobrain key` | Show API key location |
| `exobrain key-set <key>` | Save API key |
| `exobrain profiles` | List reasoning profiles |
| `exobrain profile-add` / `profile-remove` / `profile-show` | Manage profiles |

### `think` Flags

| Flag | Description |
|------|-------------|
| `--provider`, `-P` | Provider name (`openrouter` or custom) |
| `--model`, `-m` | Model ID (scoped to provider) |
| `--profile`, `-p` | Reasoning profile (see `exobrain profiles`) |
| `--depth`, `-d` | `quick` / `normal` / `deep` / `exhaustive` |
| `--context`, `-c` | Inline context |
| `--context-file`, `-f` | Context from file |
| `--stdin-context`, `-s` | Context from stdin |
| `--max-tokens`, `-t` | Override max output tokens |
| `--temperature` | Override temperature |
| `--raw`, `-r` | Skip system prompt (faster, no reasoning profile) |
| `--json`, `-j` | Strip code fences, output clean JSON |
| `--stats` | Show token usage + cost on stderr |
| `--plan` | Create a structured plan |
| `--session-id` | Isolate plan state per session |

---

## Configuration

Config file: `~/.config/exobrain/config.toml`

```toml
[defaults]
provider = "openrouter"          # built-in default
model = "openai/gpt-4o"          # optional; falls back to provider default
timeout = 180                    # seconds (default: 180)

[providers.opencode_go]
type = "anthropic-compatible"    # or "openai-compatible"
base_url = "https://opencode.ai/zen/go/v1"
api_key_env = "OPENCODE_GO_API_KEY"  # env var that holds the key
models = ["qwen3.7-max", "qwen3.6-plus"]
default_model = "qwen3.7-max"
```

The `api_key_env` value is just a **variable name**, not the key itself. The key must be set in the environment (or in `~/.hermes/profiles/<profile>/.env` if using the exobrain wrapper).

### Built-in vs Custom

- **`openrouter`** is the only built-in provider. Always available.
- **Everything else is custom.** Add a `[providers.<name>]` block to `config.toml` and the CLI will route to it.

### Adapter Type

| `type` value | Adapter | API format |
|---|---|---|
| `openai-compatible` | `oa_compat.py` | OpenAI `/chat/completions` |
| `anthropic-compatible` | `reasoning.py` | Anthropic `/messages` (uses `anthropic` SDK) |

The CLI picks the adapter automatically based on `type`.

### Depth Presets

| Preset | max_tokens | reasoning_effort | Use case |
|---|---|---|---|
| `quick` | 4 096 | low | Fast answers |
| `normal` (default) | 8 192 | medium | Balanced |
| `deep` | 16 384 | high | Deep reasoning |
| `exhaustive` | 32 768 | high | Max reasoning |

---

## API Key Resolution Order

When looking up the key for provider `P`, the CLI checks in this order:

1. Env var `<api_key_env>` (e.g. `OPENROUTER_API_KEY`)
2. `EXOBRAIN_API_KEY` (generic fallback)
3. `~/.hermes/profiles/<active>/.env` file (parsed)
4. `~/.hermes/.env` file (parsed)
5. Interactive prompt (saves to profile `.env`)

For OpenRouter specifically, the key `OPENROUTER_API_KEY` is also accepted at step 1.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `OPENROUTER_API_KEY not found` | Set the env var, or run `exobrain init` |
| `Connection timeout` | Increase timeout: `exobrain config-set timeout 300` |
| `Model not supported for format` | Wrong adapter type — set `type = "anthropic-compatible"` or `"openai-compatible"` correctly |
| Custom provider not in list | Re-run `exobrain providers`; check `[providers.<name>]` in `~/.config/exobrain/config.toml` |
| `exobrain` not found after install | `uv tool install` puts it in `~/.local/bin/` — add to `PATH` or use full path |
| Exobrain wrapper (`exobrain` script) doesn't load key | Make sure `~/.hermes/profiles/<active>/.env` contains `export <KEY>=...` lines |

---

## Requirements

- Python 3.11+
- At least one LLM provider API key
- `openai` and `anthropic` (installed automatically)

---

## License

MIT
