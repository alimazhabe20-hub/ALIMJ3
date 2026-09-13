# ALIMJ3 V78.0.0 — Update Center

V78 is based on V77 and adds a production-safe Update Center.

## What it does
- Shows current and latest release versions.
- Distinguishes: up-to-date / update available / update required / unknown.
- Supports critical/security/required release severity.
- Checks local Python runtime, required dependencies and database schema.
- Caches the last result to reduce repeated network traffic.
- Supports Persian, English and Arabic user-facing summaries.
- Adds `/update` and `/updates` commands.
- Adds `🔄 بررسی بروزرسانی` under `➕ بیشتر`.
- Adds protected `/admin/v78/updates` and `/admin/v78/updates/json` endpoints.
- Accepts only HTTPS release manifests and does not follow redirects.
- Never executes, downloads, replaces or installs remote code automatically.

## Manifest
Set `UPDATE_MANIFEST_URL` to an HTTPS URL returning JSON, for example:

```json
{
  "version": "78.1.0",
  "severity": "normal",
  "release_date": "2026-10-01",
  "title": "Maintenance release",
  "notes": "Bug fixes and compatibility improvements.",
  "min_supported_version": "78.0.0",
  "package_url": "https://example.com/ALIMJ3.zip",
  "sha256": "...",
  "changelog_url": "https://example.com/changelog"
}
```

`package_url` and `changelog_url` are displayed only when they are valid HTTPS URLs. The bot does not auto-install them.

## Verification
Use `/update` from Telegram or the protected admin endpoint. If `UPDATE_MANIFEST_URL` is empty, the center honestly reports that remote release discovery is not configured; local health checks still run.
