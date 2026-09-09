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
