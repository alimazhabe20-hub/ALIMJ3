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
└── .env.example
```

See `docs/ARCHITECTURE.md` for the architecture overview.

## License

Proprietary software. See `LICENSE`.
