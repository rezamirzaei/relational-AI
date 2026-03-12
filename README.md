# Relational Fraud Intelligence

Relational Fraud Intelligence is a production-leaning fraud investigation platform built around relational case data, typed FastAPI contracts, a polished Next.js command center, and a deterministic rule engine with optional Hugging Face and RelationalAI enrichment.

## What is in this upgrade

- SQLAlchemy-backed persistence with Alembic migrations.
- Realistic seeded fraud scenarios loaded from a relational database.
- Lifecycle-managed FastAPI startup with runtime health reporting.
- A rule-object risk engine instead of one monolithic heuristic function.
- Pre-commit hooks, GitHub Actions CI/CD, and Dependabot automation.
- Frontend component tests, TypeScript checks, and production Next.js builds.
- Dockerized backend and standalone Next.js frontend images.

## Fraud situations modeled

- Synthetic identity gift card liquidation rings.
- Premium-account takeover with cross-border rapid spend.
- Payroll-style money mule funneling through transfer and crypto rails.

RelationalAI fits this domain because entities, devices, accounts, merchants, notes, and transactions all need explainable graph-style reasoning rather than isolated row scoring.

## Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, RelationalAI SDK, Hugging Face Hub
- Frontend: Next.js 16, React 19, TypeScript 5, Vitest, Testing Library
- Delivery: Docker, Docker Compose, GitHub Actions, GHCR publishing workflow
- Quality: Ruff, mypy, pytest, coverage, pre-commit, frontend typecheck and tests

## Quick start

1. Copy `.env.example` to `.env`.
2. Install backend dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

3. Install frontend dependencies:

```bash
npm --prefix frontend ci
```

4. Apply migrations and seed the local database:

```bash
rfi-manage migrate
rfi-manage seed
```

5. Start the backend:

```bash
rfi-api
```

6. Start the frontend:

```bash
npm --prefix frontend run dev
```

7. Open `http://localhost:3001` when using the example environment file.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The compose stack persists SQLite data in the `rfi_data` volume, migrates the backend schema on startup, waits for backend health, and then serves the frontend.

## Database workflow

- `rfi-manage migrate` applies Alembic migrations to `RFI_DATABASE_URL`.
- `rfi-manage seed` inserts realistic scenarios if the database is empty.
- Local development defaults to `sqlite+pysqlite:///./data/rfi.db`.
- CI uses the same migration path before running tests.

## Runtime modes

### Default mode

- `RFI_TEXT_SIGNAL_PROVIDER=keyword`
- `RFI_REASONING_PROVIDER=local-rule-engine`

This is the deterministic, test-friendly mode used by default.

### Hugging Face mode

Set:

- `RFI_TEXT_SIGNAL_PROVIDER=huggingface`
- `RFI_HUGGINGFACE_API_TOKEN=...`

The backend will try zero-shot classification first and fall back to keyword heuristics if the provider fails.

### RelationalAI mode

Set:

- `RFI_REASONING_PROVIDER=relationalai`

By default the adapter uses a DuckDB-backed local semantic projection through the RelationalAI SDK. If you want to wire a real external RelationalAI config, set:

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
```

## Project structure

```text
alembic/                               Database migrations
src/relational_fraud_intelligence/
  api/                                 FastAPI routes and dependencies
  application/                         DTOs, ports, and services
  domain/                              Pydantic domain models
  infrastructure/persistence/          SQLAlchemy models, mapping, repository, seeding
  infrastructure/reasoners/            Rule-based and RelationalAI-ready risk reasoning
  infrastructure/seed/                 Realistic fraud scenario fixtures
  infrastructure/text/                 Keyword, Hugging Face, and fallback text services
frontend/
  app/                                 Next.js app router and global styles
  components/                          Product UI and tests
  lib/                                 API client and typed frontend contracts
tests/                                 Backend API, repository, and service tests
.github/workflows/                     CI and CD automation
```

## Quality gates

The repository is set up so local hooks and CI enforce the same standards:

- Ruff formatting and linting
- mypy strict type checking
- pytest with coverage threshold
- frontend TypeScript checks
- frontend Vitest component tests
- production Next.js build
- Docker image builds in CI

## Notes

- The default fraud logic is deterministic and explainable.
- Provider failures remain visible in the UI through fallback notes instead of taking the system down.
- The RelationalAI adapter stays isolated so deeper semantic modeling can replace or extend the local rules without changing API contracts.
