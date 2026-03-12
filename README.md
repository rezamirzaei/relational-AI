# Relational Fraud Intelligence

A production-grade fraud investigation platform with case lifecycle management, automated alert generation, graph-based entity analysis, rule-based risk reasoning, operator authentication, audit logging, and a multi-view Next.js command center.

## What it does

Relational Fraud Intelligence models a **real fraud operations workflow**:

1. **Investigate** — Analysts select fraud scenarios and the platform runs 10 deterministic fraud rules, text signal extraction, and graph relationship analysis to produce a scored investigation with evidence, rule hits, and recommended actions.

2. **Detect** — The rule engine identifies shared device clusters, rapid spend bursts, cross-border mismatches, velocity anomalies, round-amount structuring, dormant account activation, high-risk merchant concentration, and more.

3. **Alert** — When an investigation produces a risk score ≥ 35, alerts are auto-generated from the top rule hits and placed in the alert queue for analyst triage.

4. **Manage Cases** — Analysts create fraud cases from investigations, track them through a full lifecycle (open → investigating → escalated → resolved → closed), add comments, and record dispositions.

5. **Monitor** — A dashboard overview shows aggregate metrics: open cases, critical cases, pending alerts, risk distribution, and recent activity.

## Production capabilities

- **10 fraud detection rules** with weighted scoring, evidence linking, and narrative generation.
- **Graph analysis engine** that computes entity network density, hub detection, community count, and risk amplification factors.
- **Case lifecycle management** with status transitions, SLA deadlines, comments, and disposition tracking.
- **Automated alert pipeline** that generates and queues alerts from investigation results.
- **Dashboard statistics** with case/alert breakdowns, risk distribution, and activity feed.
- Postgres-first persistence with SQLAlchemy 2 and Alembic migrations.
- Redis-backed rate limiting with automatic in-memory fallback.
- JWT operator authentication, RBAC (analyst/admin), and structured request auditing.
- Automatic audit retention pruning at startup plus a manual `prune-audit` management command.
- 3 realistic seeded fraud scenarios covering synthetic identity, account takeover, and money mule flows.
- Optional Hugging Face and RelationalAI enrichment with graceful degradation.
- Pre-commit hooks, GitHub Actions CI/CD, Dependabot, Docker images, and compose orchestration.

## Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Postgres, Redis
- Frontend: Next.js 16, React 19, TypeScript 5, Vitest, Testing Library
- AI integrations: RelationalAI SDK, Hugging Face Hub
- Delivery: Docker, Docker Compose, GitHub Actions, GHCR publishing
- Quality: Ruff, mypy, pytest, coverage, pre-commit, frontend typecheck and tests

## API surface (16 endpoints)

| Category | Endpoints |
|----------|-----------|
| System | `GET /health` |
| Auth | `POST /auth/token`, `GET /auth/me` |
| Investigations | `GET /scenarios`, `GET /scenarios/{id}`, `POST /investigations` |
| Cases | `POST /cases`, `GET /cases`, `GET /cases/{id}`, `PATCH /cases/{id}/status`, `POST /cases/{id}/comments` |
| Alerts | `GET /alerts`, `PATCH /alerts/{id}` |
| Dashboard | `GET /dashboard/stats` |
| Admin | `GET /audit-events` |

Interactive docs at `http://localhost:8000/docs` (Swagger) and `http://localhost:8000/redoc` (ReDoc).

## Quick start

1. Copy `.env.example` to `.env`.
2. Rotate `RFI_JWT_SECRET` and the bootstrap operator passwords if the system will be reachable outside localhost.
3. Install dependencies:

```bash
python3 -m pip install -e ".[dev]"
npm --prefix frontend ci
```

4. Start the infrastructure services:

```bash
docker compose up -d postgres redis
```

5. Apply schema changes and seed the scenario catalog:

```bash
rfi-manage migrate
rfi-manage seed
```

6. Start the backend and frontend:

```bash
rfi-api
npm --prefix frontend run dev
```

7. Open `http://localhost:3001`.

Local demo operators from `.env.example`:

- `analyst / AnalystPassword123!`
- `admin / AdminPassword123!`

## Full compose stack

```bash
cp .env.example .env
docker compose up --build
```

The compose baseline starts Postgres, Redis, the FastAPI backend, and the Next.js frontend. The backend applies Alembic migrations at container start, bootstraps the configured operator accounts, seeds scenarios when enabled, and enforces request audit retention on startup.

## Security and operations

- `RFI_JWT_SECRET` must be at least 32 characters and must be overridden outside `local` and `test`.
- Bootstrap operator passwords must be at least 12 characters.
- Login and API traffic are rate-limited independently.
- Every request receives an `X-Request-ID` and is written to the audit trail with actor, action, path, and status code.
- Audit retention is controlled by `RFI_AUDIT_LOG_RETENTION_DAYS`.
- `rfi-manage create-operator` creates named operators for managed environments.
- `rfi-manage prune-audit` deletes expired audit events on demand.

## Runtime modes

### Default mode

- `RFI_TEXT_SIGNAL_PROVIDER=keyword`
- `RFI_REASONING_PROVIDER=local-rule-engine`

This is the deterministic, test-friendly default.

### Hugging Face mode

Set:

- `RFI_TEXT_SIGNAL_PROVIDER=huggingface`
- `RFI_HUGGINGFACE_API_TOKEN=...`

The backend tries zero-shot classification first and falls back to keyword heuristics if the provider fails.

### RelationalAI mode

Set:

- `RFI_REASONING_PROVIDER=relationalai`

By default the adapter uses a DuckDB-backed local semantic projection through the RelationalAI SDK. For external configuration, set:

- `RFI_RELATIONALAI_USE_EXTERNAL_CONFIG=true`

and provide a supported `raiconfig.yaml`.

## Developer workflow

Install git hooks:

```bash
make precommit-install
```

Run the full local quality suite:

```bash
make quality
```

Useful commands:

```bash
make lint
make mypy
make test
make typecheck
make frontend-test
make frontend-build
make db-upgrade
make db-seed
make audit-prune
make docker-up
```

## CI/CD

GitHub Actions enforces:

- pre-commit on the full repository
- backend lint, type checks, tests, and coverage
- frontend type checks, component tests, and production build
- Postgres + Redis smoke validation for migrations, auth, and runtime health
- Docker image builds on CI
- GHCR image publishing on `main` and version tags

## Project structure

```text
alembic/                               Database migrations
src/relational_fraud_intelligence/
  api/                                 FastAPI routes, middleware, and dependencies
  application/                         DTOs, ports, and services
  domain/                              Pydantic domain models
  infrastructure/logging.py            Structured JSON logging
  infrastructure/persistence/          SQLAlchemy models, repositories, and seeding
  infrastructure/rate_limit/           Memory and Redis rate limit adapters
  infrastructure/reasoners/            Rule-based and RelationalAI-ready risk reasoning
  infrastructure/security/             Password hashing, JWTs, operator bootstrap
  infrastructure/text/                 Keyword, Hugging Face, and fallback text services
frontend/
  app/                                 Next.js app router and global styles
  components/                          Authenticated investigation workspace and tests
  lib/                                 API client and typed frontend contracts
tests/                                 Backend API, security, audit, and rate-limit tests
.github/workflows/                     CI and CD automation
```

## Notes

- The default fraud logic is deterministic and explainable.
- Provider failures are surfaced to the UI through runtime notes instead of failing the whole investigation flow.
- The RelationalAI adapter remains isolated so deeper semantic modeling can replace or extend the local rules without changing API contracts.
