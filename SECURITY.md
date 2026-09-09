# Security Notes — ALIMJ V58 Pro

## Built-in safeguards
- Secrets loaded from environment variables only
- `/metrics` protected with `METRICS_TOKEN` (HMAC compare, fail-closed when token set)
- Force-join is enabled by default (`FORCE_JOIN_ENABLED=true`), requires valid `CHANNEL_ID` and `CHANNEL_LINK`, applies to `/start` as well as other user-facing updates, and fails closed on membership API errors; set `FORCE_JOIN_ENABLED=false` only when intentionally disabling it.
- SQLite writes use allowlisted dynamic field names
- Restore size limited via `RESTORE_MAX_BYTES`
- Docker runs as non-root user
- Startup self-check validates critical handlers before polling
- Plugin loader only imports local registered modules

## Operator checklist
1. Never commit `.env`
2. Set a long random `METRICS_TOKEN`
3. Restrict admin IDs to trusted accounts
4. Use persistent disk for `DB_PATH` / `BACKUP_DIR`
5. Rotate AI provider keys periodically
6. Keep `PLUGINS_DISABLED` available for emergency feature shutdown

## Reporting
If you rediscover a vulnerability in a deployed copy, patch locally and rotate tokens immediately.
