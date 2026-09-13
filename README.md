## V78.0.0 — Ultimate Final Platform

Final consolidated ALIMJ3 platform release: Agent 5.0, Knowledge Graph, DR 4.0, Provider Mesh 2.0, Market Intelligence 3.0, News Fusion, Smart Alerts 3.0, Security 3.0, Document Intelligence 2.0, Report Studio, Web Research, Self-Healing, QA/Release Gate and deep platform integrations.

Free for all users · Persian / English / Arabic only · no automatic long-conversation summarization.

## Historical V76.0.0 — Adaptive Core & Automation Platform
All 12 requested reliability/intelligence layers are integrated and bounded.

# Rooze Ziba / ALIMJ V58 Pro — Enterprise Final

Production-grade Persian Telegram assistant with multi-provider AI, tool calling, memory, retrieval/RAG, bounded agents, automation, modular domain features, diagnostics and resilient persistence.

## Product capabilities

| Domain | Capabilities |
|---|---|
| **AI** | Multi-provider routing, key rotation, tool calling, media understanding |
| **Agents** | Bounded multi-step planning, repair attempts, reliability memory |
| **Knowledge** | Local RAG/knowledge retrieval with deterministic ranking |
| **Personalization** | Preferences, memory, response style |
| **Automation** | Opt-in daily digest |
| **Domain tools** | Market/crypto, weather, prayer times, religious utilities, safe calculator |
| **Operations** | Diagnostics, metrics, backups, restore, Docker, startup checks, plugins |
| **Access control** | Mandatory channel membership by default, including `/start` |

## Quick start

### Requirements
- Python **3.11+**
- Telegram bot token from BotFather

### Install
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

### Configure
At minimum:
```env
BOT_TOKEN=123456:ABCDEF...
ADMIN_IDS=123456789
FORCE_JOIN_ENABLED=true
CHANNEL_ID=-1001234567890
CHANNEL_LINK=https://t.me/your_channel
RELEASE_VERSION=58.0.0
```

When force-join is enabled, both `CHANNEL_ID` and `CHANNEL_LINK` must be configured. The membership check is enforced for `/start` and other user-facing updates, and membership API failures fail closed.

### Run
```bash
python -m bot.main
```

### Docker
```bash
docker compose up --build
```

## Operations

| Endpoint / Command | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /metrics` | Protected telemetry (`METRICS_TOKEN`) |
| `/diagnostics` | Admin operational snapshot |
| `/plugins` | Plugin status |
| `/agent` | Bounded autonomous execution |
| `/memory` | User memory controls |
| `/automation` | Daily digest opt-in |

## Testing & quality

```bash
python -m unittest discover -s tests -v
python scripts/run_quality.py
```

CI runs syntax checks and the unit suite on Python 3.11.

## Security

- Secrets are environment-driven only
- Metrics endpoint is token-protected
- Force-join is fail-closed and cannot be bypassed through `/start`
- Calculator uses an allowlisted AST evaluator
- Restore size/schema validation is bounded
- Container runs as non-root
- Startup self-check validates critical runtime contracts
- See `SECURITY.md`

## Project structure

```text
rooze-ziba/
├── bot/                 # Application source
├── tests/               # Regression & contract tests
├── docs/                # Architecture & engineering docs
├── scripts/             # Quality tooling
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── .github/workflows/ci.yml
├── .dockerignore
├── .gitignore
└── .env.example
```

See `docs/ARCHITECTURE.md` for the architecture overview.

## License

Proprietary software. See `LICENSE`.

## V65 platform
- Free forever architecture: subscriptions/payments are disabled.
- Supported languages: Persian (fa), English (en), Arabic (ar) only.
- AI intent routing, compact persistent memory, web/product links, watchlists and price alerts.
- Streaming AI, voice, image/video analysis, economic calendar, market tools, daily digest, backups, queue/rate-limit and protected health/admin endpoints.
- Bot commands: `/features`, `/watchlist`, `/alerts`, `/memory2`, `/v65health`.


## V70 Platform
AI agent/multi-agent scaffolding, fact/source intelligence, memory 2, RAG/document/code analysis, self-test, recovery, performance/security controls, workspace, optimizer, conversation branches, scheduled AI tasks, smart notifications, personalization and observability are available. The downloader uses yt-dlp for supported public media URLs and a safe direct HTTP fallback.


## V73.0.0 Production Hardening
- Downloader 2.0 with quality/audio choices, progress, cache, resume and bounded concurrency.
- Safer redirect/host validation and clear blocked/private/CAPTCHA handling.
- Workspace, conversation branches, scheduled AI tasks, personalization, observability and self-test.
- Only Persian, English and Arabic are supported as product languages.
- Automatic long-conversation summarization is not part of V71.

## V75 Intelligence & Automation
V75 adds bounded Agent 3.0, Multi-Agent orchestration, security center, web/RAG/market/news/calendar intelligence, workflow automation, smart alerts, memory/workspaces, backup integrity, performance/QA telemetry, and multi-format report generation. See `V75_RELEASE.md`.

## V77 operator surfaces
- Telegram: `/v77test`, `/v77status` (admin-only).
- Protected web dashboard: `/admin/v77` and `/admin/v77/json` using `ADMIN_PANEL_TOKEN` or `METRICS_TOKEN`.
