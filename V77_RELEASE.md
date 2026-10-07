# ALIMJ3 V77.0.0 — Ultimate Final Release

Version: `77.0.0`

## Scope
V77 is the consolidated final platform expansion built on V76. It keeps the bot free for all users and supports Persian, English and Arabic only. Automatic long-conversation summarization is intentionally excluded.

## Included
- Agent 5.0 with dependency-aware planning, bounded retries, verification and execution budgets.
- Unified safe bridge to the existing tool runtime.
- Knowledge Graph with persistent nodes, relations and neighborhood queries.
- Backup/DR 4.0: SQLite online backup, integrity verification, fingerprints, restore candidate ranking and rotation.
- Provider Mesh 2.0 with health, reliability, latency and cost-aware selection.
- Market Intelligence 3.0: EMA, RSI, momentum, volatility, regime, volume trend and correlation.
- News Fusion: deduplication, sentiment, impact and confidence.
- Economic surprise scoring.
- Adaptive LRU cache and performance telemetry.
- Regression/release gate and artifact hygiene checks.
- Smart Alerts 3.0 with persistent alert storage.
- Security 3.0: prompt-injection detection, secret redaction, DNS-aware SSRF checks, path/archive traversal protection, rate limiting and circuit breakers.
- Document Intelligence 2.0 for PDF/DOCX/TXT/MD/CSV extraction and table capture.
- Trusted plugin registry with explicit permissions; untrusted code is never executed.
- Structured conversation state with bounded turns; no automatic summarization.
- Report Studio for JSON/CSV/XLSX/DOCX/PDF.
- Web research source ranking and evidence checks.
- Admin health/self-healing snapshots.
- Event-driven and workflow safety primitives.
- Existing V61-V76 features remain preserved.

## Operator commands
- `/v77test` — full V77 self-test (admin only).
- `/v77status` — safe V77 operational status (admin only).

## Validation
The release package is generated only after source compilation, regression tests, artifact sanitization, ZIP integrity verification and hash generation. Runtime Telegram/Render integration still depends on the deployment environment and its configured secrets/services.
