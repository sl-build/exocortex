# Brain Hermes Plugin (optional, experimental)

> **Версия:** соответствует brain-cli (сейчас v0.2.0)
> **Не входит в pip-пакет brain.** Устанавливается отдельно через Hermes Agent.

## Установка

```bash
Скопировать plugin.yaml в skills Hermes-агента
cp plugin/brain-tool/plugin.yaml ~/.hermes/skills/
```

## Инструменты плагина

| Инструмент | Назначение |
|-----------|------------|
| `brain_think` | Выполнить reasoning через Brain CLI |
| `brain_config` | Управление конфигурацией |
| `brain_plan` | Plan management (show/mark/block) |
| `brain_plan_status` | Статус Brain Gate |

## Brain Gate

Gate — защита от циклических вызовов. Блокирует brain think, если сам brain вызвал агента, который вызвал brain. См. `brain plan --block` / `--mark-done`.

## Зависимости

- brain CLI v0.2.0+ (`pip install brain`)
- Hermes Agent
