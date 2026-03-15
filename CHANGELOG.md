# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Structured error codes (`ErrorCode` enum) and error response envelope on all API errors.
- Rate-limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) on every authenticated response.
- `GET /readyz` lightweight readiness probe for orchestrators.
- Pagination on `GET /datasets` endpoint (`page`, `page_size`, `total`).
- Global exception handlers for `RequestValidationError`, `HTTPException`, and unhandled exceptions.
- Security audit CI job (`pip-audit` + `npm audit`).
- On-demand load-testing CI job (Locust).
- Frontend test coverage enforcement via `@vitest/coverage-v8` (60% threshold).
- Ruff security rules (`S` / flake8-bandit) in lint config.
- Multi-stage backend Dockerfile (builder → runtime) for smaller images.
- `SECURITY.md` vulnerability reporting policy.
- `.env.example` with all configuration variables documented.
- `py.typed` PEP 561 marker for downstream type consumers.

### Changed
- Version source of truth consolidated to `__init__.__version__` (was mismatched).
- `.dockerignore` expanded to exclude tests, docs, and build artifacts.
- Backend Dockerfile converted from single-stage to multi-stage.
- Pre-commit config now includes `detect-secrets` hook.

### Fixed
- `__init__.py` version mismatch (was `0.1.0`, now `1.0.0` matching `pyproject.toml`).

## [1.0.0] — 2026-03-15

### Added
- Full async FastAPI backend with SQLAlchemy AsyncSession and asyncpg.
- Hexagonal architecture: domain models, application services (ports/adapters), infrastructure layer.
- Domain model split into 12 aggregate modules with business invariants.
- JWT authentication with RBAC (analyst, admin roles).
- Rate limiting (memory + Redis backends) with configurable windows.
- Audit trail with retention pruning.
- 25 REST API endpoints across 7 route groups (health, auth, investigations, cases, alerts, dashboard, datasets).
- Reference scenario catalog with 5 pre-seeded fraud scenarios.
- Investigation engine with graph analysis (NetworkX), text signal extraction (keyword + HuggingFace), and multi-provider risk reasoning (local rules + RelationalAI).
- Dataset upload (CSV/JSON), Benford's Law analysis, statistical outlier detection, velocity spike detection, round-amount structuring, and behavioral relationship inference.
- Persistent fraud cases with lifecycle management (OPEN → INVESTIGATING → ESCALATED → RESOLVED → CLOSED).
- Persistent fraud alerts with status tracking and case linkage.
- Analyst dashboard with aggregate metrics and activity feed.
- Analysis explanations (deterministic + HuggingFace providers) with audience targeting.
- OpenTelemetry tracing + Prometheus metrics (opt-in).
- Structured logging.
- Alembic database migrations (4 versions).
- Next.js frontend with TypeScript, dark/light theme, CSS design tokens, accessibility attributes.
- Generated TypeScript contracts from OpenAPI schema.
- 141+ backend unit tests (92% coverage, 85% threshold enforced).
- Postgres integration test suite (marker-gated).
- 19 Vitest frontend unit tests.
- Playwright E2E test suite with API mock fixtures.
- Locust load-testing script.
- 7-job CI pipeline (lint, mypy, tests, Postgres integration, OpenAPI drift, frontend quality, Docker build).
- Docker Compose stack (Postgres 17, Redis 7, backend, frontend) with health checks.
- Comprehensive README (850+ lines) with architecture docs, workflow guides, and API versioning strategy.
- Pre-commit hooks (ruff, mypy, pytest, frontend typecheck).
- Makefile with 20 developer-experience targets.

[Unreleased]: https://github.com/your-org/relational-AI/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/relational-AI/releases/tag/v1.0.0

