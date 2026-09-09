# ALIMJ V58 Pro — Patch & Hardening Summary

## 1) Exception hygiene (critical paths)
- Replaced dozens of silent `except: pass` blocks in critical modules with `logger.debug(...)`.
- Touched areas include: `database`, `main`, AI stack, handlers (`messages`, `callbacks`, `middleware`), `db_persist`.
- Expected SQLite "column exists" paths remain non-fatal.

## 2) Sales readiness
- Added `SALES_README.md`
- Rewrote root `README.md` for clean delivery
- Restored/updated `.env.example`
- Removed local log artifacts from package
- Added `.gitignore` for secrets/data/cache

## 3) Security hardening
- Force-join is enabled by default in V58 Pro; deployment must provide a valid `CHANNEL_ID` and `CHANNEL_LINK`.
- Membership check fails open only on API errors; disabled when no channel configured
- Added `SECURITY.md` operator checklist
- System prompt moved to a cleaner commercial default (still fully overridable via `AI_SYSTEM_PROMPT`)
- Version pins aligned to **58.0.0** across release/readme/render/compose

## 4) Quality gates
- Full AST syntax parse of all `bot/**/*.py` modules: clean
- Smoke import of config/plugins/knowledge/agent: clean
