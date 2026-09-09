# ALIMJ V38 — Docker & Deployment Hardening

## Release

- Version: 38.0.0
- Focus: reproducible container runtime and deployment hardening

## Changes

- Added a Python 3.11 slim Docker image.
- Runs the application as a non-root user.
- Added container-level `/health` healthcheck.
- Added Docker Compose configuration with persistent data/log volumes.
- Added `init: true`, graceful stop period, and `no-new-privileges`.
- Added `.dockerignore` to keep secrets, caches, local databases, tests, and the immutable jokes corpus out of the image context.
- Render release pin updated to 38.0.0.

## Compatibility

- Existing application entrypoint remains `python -m bot.main`.
- `requirements.txt` is intentionally unchanged in this release.
- `jokes_data.json` is intentionally unchanged and excluded from Docker build context.
