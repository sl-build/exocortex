# Brain CLI v0.2.0 — Reasoning Engine for AI Agents

[![PyPI version](https://img.shields.io/pypi/v/brain)](https://pypi.org/project/brain/)

Brain CLI — экзокортекс для AI-агентов. Отправляет промпт на reasoning-модели (OpenAI, Anthropic, Gemini, DeepSeek, Qwen) через OpenRouter, возвращает ответ. Используется как MCP tool или standalone.

## Quick Start

```bash
pip install brain
export OPENROUTER_API_KEY=sk-or-...
brain think "Как работает async/await в Python?"
```

## Usage

- `brain think "prompt"` — базовый
- `brain think "prompt" --model gpt-4o --depth high` — с моделью и детализацией
- `brain think "prompt" --context "контекст"` — с контекстом
- `brain think "prompt" --context-file file.txt` — из файла
- `cat log.txt | brain think "why?" --stdin-context` — из stdin
- `brain think "prompt" --json` — JSON-ответ
- `brain think "prompt" --stats` — со статистикой
- `brain think "prompt" --plan` — режим планирования
- `brain think "prompt" --session-id my-session` — multi-session

## Plan Management

- `brain plan` — показать план
- `brain plan --mark-done` — отметить выполненным
- `brain plan --block` — заблокировать

## Provider

По умолчанию OpenRouter (бекает 300+ моделей). Можно переключить:

```bash
brain config-set --provider opencode_go
brain config-set --provider openrouter
```

## Profiles

Встроенные профили (6 шт): reasoning, writer, planner, critic, research, creative.

Свои:

```bash
brain profile-add my-profile template=reasoning model=qwen-max-0125
brain profiles
brain profile-remove my-profile
```

## Depth presets

- `low` — быстрый, поверхностный
- `medium` (default) — balanced
- `high` — deep reasoning

## Hermes Plugin (optional, experimental)

Brain CLI можно подключить к Hermes-агенту. См. plugin/README.md.

Внимание: не входит в pip-пакет, устанавливается отдельно.

## Install

```bash
pip install brain
```

Для Hermes Agent: `pip install brain hermes` (plugin не входит, см. plugin/README.md)

## Requirements

Python 3.11+, API ключ от OpenRouter (openrouter.ai/keys)

## License

MIT
