---
name: exobrain
description: "Use ExoBrain when the task needs deep reasoning, multi-step analysis, planning, coding design, or when internal reasoning feels insufficient. Routes your prompt to an external reasoning model and returns structured reasoning."
version: 1.0.0
author: SL
license: MIT
metadata:
  hermes:
    tags: [exobrain, brain, cli, reasoning, plan]
triggers:
  - exobrain
  - think harder
  - deep analysis
  - complex reasoning
  - step by step
  - plan
---

# ExoBrain CLI

External reasoning engine. Sends prompts to a powerful model, returns response — pure reasoning.

## When to Use

- Complex analysis, planning, structured thinking beyond your current model
- Code review, architecture decisions, debugging tricky issues
- Multi-step decomposition with a dedicated reasoning profile

**Don't use for:** simple questions (answer directly), task management (→ todo-manager).

## Quick Start

```bash
uv tool install exobrain-cli
exobrain init          # interactive: provider, key, test
```

Full docs: [llms.txt](https://github.com/sl-build/exobrain/blob/main/llms.txt)

## Commands

```bash
exobrain think "prompt"                    # basic reasoning
exobrain think "prompt" --profile critic   # with profile
exobrain think "prompt" --depth deep       # deep reasoning
exobrain think "prompt" --json --stats     # JSON output + token stats
cat file.py | exobrain think "find bugs" --stdin-context  # piped context
exobrain think "prompt" --provider my_api  # one-off provider override

exobrain config                            # show config
exobrain config-set provider my_api        # switch provider (persistent)
exobrain config-set timeout 300            # increase timeout
exobrain key                               # show key location
exobrain key-set sk-xxx                    # save key for current provider
exobrain profiles                          # list profiles
exobrain status                            # health check
```

## Profiles

| Profile | Depth | Use |
|---------|-------|-----|
| reasoning | normal | Step-by-step analysis (default) |
| critic | deep | Flaw finding, confidence rating |
| planner | deep | Strategic plans |
| judge | normal | A/B decisions |
| extractor | normal | Structured data extraction |
| writer | deep | Concise writing |

Custom: `exobrain profile-add NAME --prompt "..." --depth deep --temp 0.8`

## Custom Providers

Add any OpenAI-compatible API to `~/.config/exobrain/config.toml`:

```toml
[providers.my_api]
type = "openai-compatible"
base_url = "https://my-api.com/v1"
api_key_env = "MY_API_KEY"
models = ["model-a", "model-b"]
default_model = "model-a"
```

Then: `exobrain config-set provider my_api`

## Pitfalls

1. **Config is persistent.** `exobrain config-set provider X` affects all future calls. Use `--provider` for one-offs.
2. **Key must exist.** `exobrain key` to check. Missing → `exobrain init` or `exobrain key-set`.
3. **Timeout 180s default.** Deep models may need more: `exobrain config-set timeout 300`.
4. **`--raw` skips system prompt.** Faster, no profile applied.
# ExoBrain CLI
