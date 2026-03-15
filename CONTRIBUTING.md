# Contributing

Thanks for considering a contribution to Relational Fraud Intelligence. This guide covers everything you need to get up and running.

## Prerequisites

- Python 3.11+
- Node.js 22+
- Docker & Docker Compose (for the full container stack)

## Quick setup

```bash
# Clone the repository
git clone <repo-url> && cd relational-AI

# Copy the env template
cp .env.example .env

# Install backend (with dev extras) and frontend
make install

# Install pre-commit hooks
make precommit-install
```

## Running locally

Start the backend and frontend in separate terminals:

```bash
# Terminal 1 — backend
rfi-api

# Terminal 2 — frontend
npm --prefix frontend run dev
```

Or bring up the full stack with Docker:

```bash
docker compose up --build
```

## Quality gates

Every pull request must pass:

```bash
make quality          # runs all checks below in sequence
```

Individual checks:

| Command | What it does |
|---------|--------------|
| `make lint` | Ruff lint on backend source, tests, and migrations |
| `make format` | Ruff auto-format |
| `make mypy` | Strict type checking for the backend |
| `make test` | Backend pytest suite with coverage enforcement (≥ 85%) |
| `make typecheck` | Frontend TypeScript type checking |
| `make frontend-test` | Frontend Vitest component tests |
| `make frontend-build` | Production Next.js build |
| `pre-commit run --all-files` | Full pre-commit hook sweep |

## Project structure

```text
src/relational_fraud_intelligence/
  api/             → FastAPI routes, middleware, dependencies
  application/     → DTOs, ports, and application services
  domain/          → Pydantic domain models
  infrastructure/  → Persistence, analysis, security, providers
frontend/          → Next.js dashboard application
tests/             → Backend unit and integration tests
alembic/           → Database migrations
docs/              → Architecture and workflow documentation
```

For the full system design, see [docs/architecture.md](docs/architecture.md).
For operator workflow details, see [docs/workflows.md](docs/workflows.md).

## Writing a pull request

1. Create a feature branch from `main`.
2. Keep commits focused — one logical change per commit.
3. Write or update tests for any new behavior.
4. Run `make quality` before pushing.
5. Open a PR with a clear title and description of _what_ changed and _why_.

## Adding a database migration

```bash
# After changing domain models or table definitions:
rfi-manage migrate   # applies existing migrations
# Then create a new Alembic revision manually in alembic/versions/
```

Follow the existing naming convention: `YYYYMMDD_NNNN_description.py`.

## Code style

- **Backend**: enforced by [Ruff](https://docs.astral.sh/ruff/) (line length 100, Python 3.11 target). Import order and formatting are automatic.
- **Frontend**: TypeScript strict mode. Prefer explicit types over `any`.
- **Commits**: use imperative mood ("Add feature" not "Added feature").

## Security

If you discover a security vulnerability, **do not open a public issue**. See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

## License

By contributing you agree that your contributions will be licensed under the [MIT License](LICENSE).

