# Rooze Ziba / ALIMJ — V58 Pro Enterprise Final

Version: `58.0.0`

## Summary
V58 combines the V56 Enterprise packaging/operations baseline with the V57 Pro hardening line. It is the consolidated production release.

## Included hardening
- Force-join is enforced for `/start` and every user-facing update.
- Force-join fails closed when membership lookup fails or required channel configuration is missing.
- Telegram `restricted + is_member=true` is treated as a valid membership.
- Safe AST calculator; no arbitrary `eval` execution.
- Bounded tool runtime, cache and concurrency controls.
- Database backup/restore validation and schema safety.
- Non-root Docker image, healthcheck and startup self-check.
- Enterprise CI, Makefile, architecture, security and proprietary licensing assets.
- Professional rotating application logging.

## Compatibility
Existing providers, handlers, tools, market/weather fallbacks, backup/restore flows and feature data are preserved. `requirements.txt` is intentionally unchanged. `jokes_data.json` remains immutable and excluded from knowledge indexes.

## Deployment checklist
1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN` and `ADMIN_IDS`.
3. Keep `FORCE_JOIN_ENABLED=true` for mandatory membership.
4. Set both `CHANNEL_ID` and `CHANNEL_LINK` for force-join.
5. Set `RELEASE_VERSION=58.0.0`.
6. Set a strong random `METRICS_TOKEN` if `/metrics` is exposed.
7. Put `DB_PATH` / `BACKUP_DIR` on persistent storage when available.
8. Run `python -m unittest discover -s tests -v`.
9. Run `python scripts/run_quality.py`.
10. Start with `python -m bot.main` or Docker / `render.yaml`.

## Release acceptance
- Python source compilation: required to pass.
- Archive integrity: required to pass.
- Unit/regression tests: pass when project dependencies from `requirements.txt` are installed; dependency-only skips in a stripped test container are environmental, not release defects.
