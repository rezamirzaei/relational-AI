# Relational Fraud Intelligence

Relational Fraud Intelligence is a production-style reference project for a real-world RelationalAI use case: fraud and risk investigation. The stack combines a FastAPI backend, strict Pydantic contracts, a Next.js dashboard, Docker delivery, optional Hugging Face enrichment, and a RelationalAI-ready reasoning adapter.

## What this project optimizes for

- Clean architecture with explicit ports and adapters.
- Object input and object output across the application layer.
- Pydantic-first validation at API and service boundaries.
- A deterministic demo mode that runs without cloud credentials.
- An optional RelationalAI path and optional Hugging Face path behind the same interfaces.
- Testability, documentation, and operational hygiene.

## Current use case

The reference domain is fraud detection. Seeded scenarios model:

- Synthetic identity and gift card liquidation rings.
- Account takeover with cross-border rapid spend.

RelationalAI is a strong fit here because the core problem is relational: customers, accounts, devices, merchants, notes, and transactions need graph-style reasoning and explainable rule hits rather than isolated row scoring.

## Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, RelationalAI SDK `1.0.3`, Hugging Face Hub `1.6.0`
- Frontend: Next.js `16.1.6`, React `19.2.4`, TypeScript `5.9.3`
- Delivery: Docker, Docker Compose
- Tests: Pytest

## Quick start

1. Copy `.env.example` to `.env`.
2. Install backend dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

3. Install frontend dependencies:

```bash
npm --prefix frontend install
```

4. Run backend:

```bash
rfi-api
```

5. Run frontend:

```bash
npm --prefix frontend run dev
```

6. Open `http://localhost:3000`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The backend is exposed at `http://localhost:8000`, and the UI is exposed at `http://localhost:3000`.

## Runtime modes

### Default mode

- `RFI_TEXT_SIGNAL_PROVIDER=keyword`
- `RFI_REASONING_PROVIDER=local-rule-engine`

This is the deterministic, test-friendly mode used by the project out of the box.

### Hugging Face mode

Set:

- `RFI_TEXT_SIGNAL_PROVIDER=huggingface`
- `RFI_HUGGINGFACE_API_TOKEN=...`

The backend will try Hugging Face zero-shot classification first and fall back to keyword heuristics if the provider fails.

### RelationalAI mode

Set:

- `RFI_REASONING_PROVIDER=relationalai`

By default the adapter uses a DuckDB-backed local semantic projection through the current RelationalAI SDK for an offline-compatible reference flow. If you want to wire a real external RelationalAI config, set:

- `RFI_RELATIONALAI_USE_EXTERNAL_CONFIG=true`

and provide a current `raiconfig.yaml` supported by the RelationalAI SDK.

## Project structure

```text
src/relational_fraud_intelligence/
  api/                FastAPI routes and dependencies
  application/        DTOs, ports, and use-case services
  domain/             Pydantic domain models
  infrastructure/     Demo data, providers, repositories, and reasoners
frontend/
  app/                Next.js app router
  components/         Dashboard UI
  lib/                API client and typed frontend contracts
tests/                Backend unit and API tests
```

## Quality checks

```bash
python3 -m pytest -q
python3 -m compileall src tests
npm --prefix frontend run typecheck
```

## Notes

- The default fraud logic is deterministic and explainable.
- The project uses fallback wrappers so provider failures remain visible without taking the whole system down.
- The RelationalAI adapter is intentionally isolated so deeper semantic modeling can replace or extend the local rules without changing API contracts.
