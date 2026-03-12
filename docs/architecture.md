# Architecture

## Core principles

- All application boundaries use Pydantic objects.
- Domain logic is separated from vendor integrations and transport concerns.
- Data is persisted through SQLAlchemy repositories and migrated through Alembic.
- Provider failures are explicit and surfaced to the UI through runtime notes.
- The UI consumes one stable investigation contract regardless of active providers.

## Main patterns

- Repository pattern: `ScenarioRepository` backed by `SqlAlchemyScenarioRepository`
- Strategy pattern: text-signal and risk-reasoner providers
- Fallback/decorator pattern: provider wrappers for graceful degradation
- Assembler pattern: `InvestigationCaseAssembler`
- Rule object pattern: the local risk engine composes individual fraud rules
- Ports and adapters: application owns contracts, infrastructure owns implementations

## Backend flow

1. FastAPI starts through a lifespan hook and builds the application container.
2. The container creates the SQLAlchemy engine and session factory.
3. Local startup can auto-create the schema and seed realistic scenarios.
4. The UI posts an `InvestigateScenarioCommand`.
5. `InvestigationService` loads a `FraudScenario` from the repository.
6. `TextSignalService` enriches notes and merchant descriptions.
7. `RiskReasoner` evaluates rule-based relational fraud patterns.
8. `InvestigationCaseAssembler` builds the product-facing `InvestigationCase`.
9. The API returns one stable response shape to the frontend.

## Persistence model

The seeded case data is stored relationally:

- `scenarios`
- `customers`
- `accounts`
- `devices`
- `device_customer_links`
- `merchants`
- `transactions`
- `investigator_notes`

The repository maps ORM records into domain models so the application layer remains persistence-agnostic.

## Operational model

- Alembic owns schema evolution.
- `rfi-manage migrate` is the supported migration entry point.
- `rfi-manage seed` inserts realistic cases when the database is empty.
- GitHub Actions runs lint, type checks, backend tests, frontend tests, frontend build, and Docker builds.
- Pre-commit hooks mirror the same checks locally.

## RelationalAI integration shape

`RelationalAIRiskReasoner` stays isolated in the infrastructure layer. It currently:

- Builds a semantic projection from scenario data.
- Uses the RelationalAI SDK with a local DuckDB-backed config by default.
- Can switch to an external `raiconfig.yaml` when enabled.
- Preserves the same `ReasonAboutRiskResult` contract as the local rule engine.

This keeps the project runnable offline while preserving a clean seam for deeper semantic modeling.
