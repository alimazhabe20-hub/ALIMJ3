# Architecture Overview

Rooze Ziba is a modular Telegram bot platform designed for long-running production operation.

## High-level layout

```text
bot/
├── main.py                 # Application entrypoint, health, lifecycle
├── config.py               # Environment-backed configuration
├── database*.py            # Persistence, migrations, backups
├── handlers/               # Telegram presentation & routing
├── services/               # AI, retrieval, agents, workflows
├── features/               # Domain capabilities (market, weather, ...)
├── plugins/                # Optional capability registry
├── api/                    # External data adapters
└── utils/                  # Shared helpers and observability
```

## Core runtime flow

1. Process starts and loads environment configuration.
2. Optional startup self-check validates critical contracts.
3. Database schema is initialized/migrated.
4. Plugin registry starts enabled modules.
5. Telegram application registers handlers and begins polling.
6. Health/metrics endpoints expose operational status.

## AI stack

- `ai_service`: orchestration facade
- `ai_providers`: provider adapters
- `ai_runtime`: state, routing, history, health
- `ai_tools` / `tool_runtime`: tool registry and execution
- `ai_media`: vision/voice helpers
- `agent_engine` / `multi_agent`: bounded planning and execution
- `retrieval` / `knowledge_base` / `rag`: local knowledge layer

## Design principles

- Prefer bounded, explainable automation over unbounded agent loops
- Keep secrets outside source control
- Fail closed for sensitive telemetry, fail open only for non-critical membership API glitches
- Preserve feature compatibility across modular refactors
