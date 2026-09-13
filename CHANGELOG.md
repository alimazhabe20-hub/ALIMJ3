## V78.0.0 — Update Center
- Safe remote release discovery with local runtime/dependency/schema checks.
- Added `/update`, `/updates`, and `🔄 بررسی بروزرسانی`.
- Added protected V78 admin update endpoints.
- Added Persian/English/Arabic update summaries.

## V77.0.0 — Ultimate Final Platform

- Agent 5.0, unified tool bridge and bounded verification/retry.
- Knowledge Graph, DR 4.0, Provider Mesh 2.0 and Market Intelligence 3.0.
- News Fusion, Smart Alerts 3.0 and Economic Surprise engine.
- Security 3.0, adaptive cache/performance and self-healing.
- Document Intelligence 2.0, trusted plugins and advanced conversation state.
- Report Studio, Web Research, Admin Center and Release/Regression Gate.
- Preserves free access and fa/en/ar language scope.
- Automatic long-conversation summarization remains excluded.

## V76.0.0 — Adaptive Core & Automation Platform
- Added Agent 4.0, Intent Engine, event/job primitives, plugin/provider mesh, safety gateway, advanced intelligence, adaptive cache, release gate, conversation state, and expanded operational controls.

## V75.0.0 — Reliability & Intelligence Core

- Added all 12 V75 production reliability/intelligence layers.
- Added protected `/admin/v74` observability dashboard and `/v74test`.
- Added bounded Agent 2.0, tool policies, security hardening, self-healing, performance, QA, web/RAG, persistence and provider/runtime health.

## V73.0.0
- Downloader 3.0 quality modes, progress persistence and resilient delivery.
- AI Router 2.0 deterministic quality/speed routing.
- Web Intelligence source deduplication, safe fetch and evidence checks.
- Document Intelligence for text/CSV/JSON/PDF/DOCX/XLSX with untrusted-data boundaries.
- Multi-timeframe Market Intelligence.
- QA pipeline with compileall and optional Ruff.
- UX localization helpers and improved downloader controls.
- No automatic conversation summarization.

# V71.0.0

- Downloader 2.0: probe/quality selection, bounded queue, per-user limits, progress, direct-file resume, cache and redirect validation.
- Production hardening: SSRF-aware redirect checks, safer URL handling, health/self-test, notification dedupe, personalization, workspace, branches and scheduled AI jobs.
- Security: no CAPTCHA/auth/DRM/site-ban bypass.
- Automatic conversation summarisation is explicitly not added.

# V70.0.0 — AI Platform + Professional Downloader

- Added all requested V66–V70 platform capabilities except the excluded self-improving option 20.
- Added defensive professional URL/file downloader with yt-dlp + direct-file fallback, size limits, retries and safe SSRF protections.
- Added «📥 دانلودر فایل» to More menu.
- Site blocks/CAPTCHA/private content are reported clearly and are not bypassed.

# V65.0.0 — AI Platform & Three-Language Professional Release

- V61: memory, intent routing, tool-aware context, adaptive AI runtime.
- V62: professional web/product link search and direct shopping routing.
- V63: watchlist and price-alert persistence.
- V64: health/metrics foundation, queue, rate limiting and recovery tooling.
- V65: unified free platform, Persian/English/Arabic only, privacy-safe errors, streaming, voice/image/video, calendar, market, backups and plugins.

# V60.0.2 — Link & Error Privacy Patch

- درخواست «لینکش بفرست» قبل از پاسخ عمومی AI شناسایی می‌شود و از پاسخ‌های نادرست درباره نداشتن دسترسی مستقیم به لینک جلوگیری می‌کند.
- عبارت جستجوی مرتبط از پاسخ قبلی استخراج و برای جستجوی وب استفاده می‌شود.
- خطاهای داخلی جستجوی وب، AI، تقویم، تحلیل تصویر و خلاصه‌سازی دیگر به کاربر نمایش داده نمی‌شوند و فقط در لاگ ثبت می‌شوند.
- تست‌های regression برای لینک و عدم نشت جزئیات خطا اضافه شد.

# Changelog

## V60.0.1 — Stability & Performance Professional Edition
- Hard per-provider AI timeout with automatic fallback.
- Correct single-probe HTTP circuit breaker recovery.
- Bounded per-host HTTP concurrency to prevent upstream overload.
- Short stale GET-cache fallback for read-only market/API data during transient outages.
- Bounded crypto analysis/chart execution with orphan-task cancellation.
- Safer user-facing market/tool error messages; detailed diagnostics remain in logs.
- Adaptive AI routing remains adaptive in streaming mode; successful automatic providers are not persisted as manual selections.
- Existing free/no-subscription product model preserved.


## 59.2.0 — Callback Stability & Hardening

- حذف مسیرهای تکراری callbackهای تقویم اقتصادی (`page`، `date`، `refresh` و `noop`).
- حذف import تکراری `fetch_speech_context`.
- جلوگیری از crash شدن callbackهای صفحه‌بندی با داده نامعتبر.
- اعتبارسنجی callbackهای زمان هشدار و منطقه زمانی قبل از ذخیره.
- اضافه شدن تست‌های regression برای مسیرهای callback.


## V59.1.0 — Free Professional Hardening

- Synced runtime, package, and deployment release version to `59.1.0`.
- Hardened read-only API responses with no-store and MIME-sniffing protection headers.
- Fixed API UTC timestamp generation without deprecated `datetime.utcnow()`.
- Added regression coverage for release-version synchronization and API security headers.

# V59 — Free Professional Edition

- All user-facing features are free for all users.
- No subscription, billing, or payment gate.
- Optional operator-only admin dashboard.
- Optional authenticated read-only API v1.
- Health/features endpoints and production diagnostics retained.
- Economic calendar Actual fallback improvements retained.

# Changelog

## [58.0.0] — 2026-09-09

### Added
- Enterprise packaging: LICENSE, CI, Makefile, architecture docs, professional logging
- `.dockerignore` for lean production images
- `FORCE_JOIN_ENABLED` switch with production-safe defaults

### Improved
- Safe AST calculator for tool expressions
- Tool runtime cache ceiling and execution bounds
- Database backup rotation path resolution
- Restore/schema validation strictness
- Membership enforcement (fail-closed when force-join is enabled)

### Security
- No secrets in source tree
- Metrics token protection
- Mandatory channel membership by default
- Non-root container user

## [55.0.0]
- Enterprise documentation and operational packaging baseline

## [40.0.0]
- Bounded deterministic RAG/knowledge pipeline

## [25.0.0]
- Core handler decomposition

## [20.0.0]
- Autonomous agent foundation

## [12.0.0]
- Production-channel baseline

## V75.0.0
- Added the complete Intelligence & Automation Platform (17 capability groups).
- Added bounded Agent 3.0 and Multi-Agent orchestration.
- Added Security Center, Web/RAG/Market/News/Calendar intelligence primitives.
- Added Workflow Builder, Smart Alerts, Memory 2.0, Workspaces and Report Generator.
- Added Backup integrity, performance telemetry and QA snapshot helpers.
- Added `/v75test` and `/memory4`.

## V78.0.0 — Update Center
- Added safe remote release discovery and local runtime/dependency/schema checks.
- Added `/update`, `/updates`, and `🔄 بررسی بروزرسانی`.
- Added protected V78 admin update endpoints.
- Added Persian/English/Arabic update summaries.
