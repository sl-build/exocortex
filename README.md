# WARNING this project is extreme alpha version. Can break you Hermes because of hooks usage. 
# Brain CLI 

Exocortex reasoning engine for AI agents. Multi-provider LLM gateway with reasoning profiles, depth control, structured JSON output, and plan persistence with step progress injection for Hermes Agent Gate.

## Install

```bash
uv tool install git+https://github.com/sl-build/brain-cli.git
```

Or from source:

```bash
git clone https://github.com/sl-build/brain-cli.git
cd brain-cli
uv tool install --editable .
```

## Hermes Plugin

Copy the plugin from the repo to Hermes:

```bash
cp -r plugin/brain-tool ~/.hermes/plugins/brain-tool/
```

Enable in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - brain-tool
```

Restart Hermes. The plugin provides four tools (`brain_think`, `brain_plan_done`, `brain_plan_block`, `brain_plan_status`), a `pre_tool_call` gate that blocks action tools (terminal, edit, bash, task) until an active plan exists, and a `post_receive_message` hook that injects plan progress (e.g. `"🧠 2/3 → Fix parser"`) into every Hermes message.

Each tool accepts an optional `session_id` parameter for plan isolation across Hermes threads — passed automatically by Hermes from the session context. If not provided, defaults to `~/.brain/state/plan.json`.

Full setup: see `LLMS.md`.

## Plan Management

Brain persists plans in `~/.brain/state/`. Each session gets its own file — `plan.json` (default) or `plan-{session_id}.json`.

```bash
# Create a plan (uses planner profile, returns structured JSON)
brain think "Fix the auth bug" --plan

# Isolate plans per Hermes thread (session-id)
brain think "Refactor module" --plan --session-id "thread-42"

# Show current plan (default session)
brain plan

# Show plan for a specific session
brain plan --session-id "thread-42"

# Mark current step done → advances to next step
brain plan done

# Mark step done in isolated session
brain plan done --session-id "thread-42"

# Mark current step blocked
brain plan block "Missing API credentials"

# Bypass gate and overwrite plan
brain think "Emergency hotfix" --force
```

## Quick Start

```bash
# Set API key (interactive prompt if not set)
brain key-set sk-or-...

# Quick reasoning
brain think "Should we migrate from REST to gRPC?"

# Switch provider
brain config-set provider opencode_go
```

## Usage

```bash
# Basic reasoning
brain think "Explain quantum entanglement"

# With reasoning profile
brain think "Review this approach" --profile critic

# Depth control
brain think "Design a cache strategy" --depth deep

# JSON output (for agent pipelines)
brain think "Summarize this" --json

# Context injection
brain think "Is this a good deal?" --context "Price: $50, Budget: $100"
brain think "Summarize" --context-file notes.md
cat log.txt | brain think "Find errors" --stdin-context

# Raw mode — no system prompt, just your message
brain think "What is 2+2?" --raw

# Pass model name as-is, no provider prefix
brain think "Explain this" --model qwen-3.7-max --raw-model

# Show token usage on stderr
brain think "Analyze this" --stats

# Override tokens and temperature
brain think "Detail the plan" --max-tokens 4096 --temperature 0.1
```

## Commands

| Command | Description |
|---------|-------------|
| `think` | Send prompt to reasoning engine |
| `think --plan` | Create a structured plan (planner profile) |
| `think --plan --session-id <id>` | Create plan in isolated session |
| `think --force` | Bypass gate and overwrite plan |
| `plan` | Show current plan (default session) |
| `plan --session-id <id>` | Show plan for a specific session |
| `plan done` | Mark current step done, advance |
| `plan done --session-id <id>` | Mark step done in isolated session |
| `plan block [reason]` | Mark current step blocked |
| `plan block [reason] --session-id <id>` | Block step in isolated session |
| `key` | Show current API key location |
| `key-set <key>` | Save API key to profile .env |
| `profiles` | List available reasoning profiles |
| `profile-add <name> --prompt <text>` | Add a custom profile |
| `profile-remove <name>` | Remove a custom profile |
| `profile-show <name>` | Show profile details |
| `config` | Show current configuration |
| `config-set provider <name>` | Switch default provider |
| `config-set model <id>` | Set default model |

## Providers

Brain uses an **adapter layer** to route models to the right API backend:

| Adapter | Protocol | Description |
|---------|----------|-------------|
| `oa_compat` | OpenAI SDK | Standard chat completions (OpenRouter, generic) |
| `reasoning` | httpx | Raw HTTP for reasoning-optimized endpoints (OpenCode Go qwen) |

| Provider | Default Model | Adapter |
|----------|--------------|---------|
| OpenRouter | `openai/gpt-5.5` | `oa_compat` |
| OpenCode Go | `qwen-3.7-max` | `reasoning` |

Switch providers: `brain config-set provider <name>` or `--provider` flag.

### Model-to-adapter mapping

The `reasoning` adapter is used when model is in the provider's `model_map`. Built-in mapping for OpenCode Go:

| Model | Adapter |
|-------|---------|
| `qwen-3.7-max` | `reasoning` |
| `qwen-3.7-pro` | `reasoning` |
| any other | `oa_compat` (default) |

Override or extend via `config.toml` (see [Config](#config)).

## Reasoning Profiles

- **reasoning** — step-by-step analysis (default)
- **critic** — find flaws and weak points
- **planner** — structured action plans
- **judge** — balanced pros/cons evaluation
- **extractor** — pull key facts from noise
- **writer** — concise, narrative-driven prose

Manage profiles:

```bash
brain profiles                               # list all
brain profile-show critic                    # show details
brain profile-add myprof --prompt "You are..." --depth deep --temp 0.4
brain profile-remove myprof
```

Built-in profiles cannot be overridden or removed. User profiles are stored in `~/.config/brain/profiles.toml`.

## Depth Presets

| Depth | Max Tokens | Reasoning Effort |
|-------|-----------|------------------|
| `quick` | 4,096 | low |
| `normal` | 8,192 | medium |
| `deep` | 16,384 | high |
| `exhaustive` | 32,768 | high |

`reasoning_effort` is injected only for OpenAI o-series models (o1/o3/o4). Depth does not set temperature — reasoning models optimise it internally.

```bash
brain think "Quick check" --depth quick
brain think "Deep analysis" --depth deep
brain think "Full report" --depth exhaustive
```

Explicit `--max-tokens` and `--temperature` flags override depth defaults.

## API Key Management

Keys are stored in `~/.hermes/profiles/goose/.env` (shared across tools).

```bash
# Set a key
brain key-set sk-or-...

# Check current key location and value
brain key

# Provider-specific keys
brain key-set --provider opencode_go oc-...

# Environment variables also work
export OPENROUTER_API_KEY=sk-or-...
export OPENCODE_GO_API_KEY=oc-...
export BRAIN_API_KEY=sk-or-...          # generic fallback
```

Key lookup order: provider-specific env var → `BRAIN_API_KEY` → `~/.hermes/` .env files → interactive prompt.

## Config

Config stored at `~/.config/brain/config.toml`:

```toml
[defaults]
provider = "openrouter"
model = ""

# Provider-specific overrides
[provider.opencode_go]
# Custom model-to-adapter routing
[provider.opencode_go.model_map]
"my-custom-model" = "reasoning"
"another-model" = "oa_compat"
```

## Context Injection

```bash
# Inline context
brain think "Is this a good deal?" --context "Price: $50, Budget: $100"

# From file
brain think "Summarize" --context-file notes.md

# From stdin
cat log.txt | brain think "Find errors" --stdin-context

# Metadata tags (repeatable)
brain think "Analyze" --metadata "source=prod" --metadata "severity=high"

# Combine sources
brain think "Review" --context-file app.ts --metadata "author=alice"
```

## Structured Output

```bash
# JSON output (strips code fences)
brain think "List key dates" --json

# With usage stats in the JSON
brain think "Analyze" --json --stats
```

Output when `--stats` is used:

```json
{
  "response": "...",
  "usage": {
    "model": "openai/gpt-5.5",
    "prompt_tokens": 42,
    "completion_tokens": 128,
    "total_tokens": 170,
    "cost_usd": 0.0017,
    "latency_ms": 1200
  }
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | API failure / network error |
| 2 | Bad response from model |
| 3 | Input error (bad args, missing key) |

## License

MIT
