# Rooze Ziba / ALIMJ — Commercial Source Package (V58 Pro Enterprise Final)

Complete proprietary source and deployment assets for production operation.

## Contents
- Full application source (`bot/`)
- Full regression/contract test suite (`tests/`)
- Docker + docker-compose
- Render blueprint
- `.env.example`
- Architecture, security, release and changelog documentation
- CI workflow and Makefile

## Key capabilities
- Multi-provider AI routing with key rotation
- Tool calling and bounded autonomous agents
- Long-term memory + local knowledge/RAG
- Market, weather, prayer, religious tools, fonts and utilities
- Opt-in daily automation digest
- Plugin enable/disable
- Admin diagnostics, metrics and backup/restore
- Mandatory channel membership with `/start` protection

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env → set BOT_TOKEN, ADMIN_IDS, CHANNEL_ID and CHANNEL_LINK
python -m bot.main
```

Docker:
```bash
cp .env.example .env
docker compose up --build
```

## License / ownership
Unless otherwise agreed in the sales contract, this package is proprietary source for the buyer's use under the terms of the purchase agreement.

## Support window
As defined in the sales agreement.
