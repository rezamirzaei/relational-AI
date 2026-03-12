# Architecture

## Core principles

- All application boundaries use Pydantic objects.
- Domain logic is separated from vendor integrations and transport concerns.
- Data is persisted through SQLAlchemy repositories, migrated through Alembic, and run primarily on Postgres.
- Provider failures are explicit and surfaced to the UI through runtime notes.
- The UI consumes one stable investigation contract regardless of active providers.
- Authentication, rate limiting, and audit logging are treated as first-class application concerns.

## Main patterns

- Repository pattern: `ScenarioRepository` backed by `SqlAlchemyScenarioRepository`
- Repository pattern: `OperatorRepository` and `AuditLogRepository` backed by SQLAlchemy
- Strategy pattern: text-signal and risk-reasoner providers
- Fallback/decorator pattern: provider wrappers for graceful degradation
- Assembler pattern: `InvestigationCaseAssembler`
- Rule object pattern: the local risk engine composes individual fraud rules
- Ports and adapters: application owns contracts, infrastructure owns implementations
- Service layer: authentication and audit behavior stay outside route handlers

## Backend flow

1. FastAPI starts through a lifespan hook and builds the application container.
2. The container creates the SQLAlchemy engine, session factory, audit service, auth service, and rate limiter.
3. Startup can apply local schema creation, seed realistic scenarios, bootstrap operator accounts, and prune expired audit events.
4. Request middleware adds a request ID, security headers, and audit capture.
5. The UI authenticates through `LoginCommand` and receives a JWT access token.
6. Protected routes resolve the current operator, apply RBAC, and enforce per-operator rate limits.
7. The UI posts an `InvestigateScenarioCommand`.
8. `InvestigationService` loads a `FraudScenario` from the repository.
9. `TextSignalService` enriches notes and merchant descriptions.
10. `RiskReasoner` evaluates rule-based relational fraud patterns.
11. `InvestigationCaseAssembler` builds the product-facing `InvestigationCase`.
12. The API returns one stable response shape to the frontend.

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
- `operator_users`
- `audit_events`

The repository layer maps ORM records into domain models so the application layer remains persistence-agnostic while still supporting operational tables for authentication and audit retention.

## Operational model

- Alembic owns schema evolution.
- `rfi-manage migrate` is the supported migration entry point.
- `rfi-manage seed` inserts realistic cases when the database is empty.
- `rfi-manage create-operator` provisions named operators.
- `rfi-manage prune-audit` removes expired audit events on demand.
- Redis-backed rate limiting protects authentication and API traffic.
- Every request is logged with JSON formatting plus request-level audit metadata.
- GitHub Actions runs lint, type checks, backend tests, frontend tests, frontend build, Postgres + Redis smoke validation, and Docker builds.
- Pre-commit hooks mirror the same checks locally.

## RelationalAI integration shape

`RelationalAIRiskReasoner` stays isolated in the infrastructure layer. It currently:

- Builds a semantic projection from scenario data.
- Uses the RelationalAI SDK with a local DuckDB-backed config by default.
- Can switch to an external `raiconfig.yaml` when enabled.
- Preserves the same `ReasonAboutRiskResult` contract as the local rule engine.

This keeps the project runnable offline while preserving a clean seam for deeper semantic modeling.
