# Architecture

This document explains how Relational Fraud Intelligence is wired: which layers exist, how requests move through them, what gets persisted, and how the runtime degrades safely when optional dependencies fail.

For operator-facing flows and lifecycle diagrams, read [workflows.md](workflows.md).

## System context

```mermaid
graph TB
    Browser[Browser]

    subgraph Frontend["Next.js workspace"]
        Overview[Overview and dashboard]
        DatasetsUI[Dataset analysis workspace]
        AlertsUI[Alert queue]
        CasesUI[Case management]
        ScenariosUI[Reference investigations]
    end

    subgraph API["FastAPI boundary"]
        Auth[Auth and RBAC]
        Routes[Typed REST routes]
        Middleware[Request context, security headers, audit]
    end

    subgraph Services["Application services"]
        DatasetService[DatasetService]
        InvestigationService[InvestigationService]
        AlertService[AlertService]
        CaseService[CaseService]
        DashboardService[DashboardService]
        AuthService[AuthService]
        AuditService[AuditService]
        GuideService[WorkspaceGuideService]
    end

    subgraph Analysis["Analysis and provider layer"]
        Statistical[Benford, outliers, velocity, round amounts]
        Behavioral[Behavioral pattern analysis]
        Graph[Graph analyzer]
        Reasoner[Local or RelationalAI reasoner]
        TextSignals[Keyword or Hugging Face text signals]
        Explainers[Deterministic or Hugging Face explanations]
    end

    subgraph Persistence["Persistence and infrastructure"]
        WorkflowRepo[Workflow repositories]
        ScenarioRepo[Scenario repository]
        SecurityRepo[Security repositories]
        DB[(Postgres or SQLite)]
        Redis[(Redis rate limiter)]
    end

    Browser --> Frontend
    Frontend --> API
    API --> Services
    DatasetService --> Statistical
    DatasetService --> Behavioral
    InvestigationService --> Reasoner
    InvestigationService --> TextSignals
    InvestigationService --> Graph
    AlertService --> WorkflowRepo
    CaseService --> WorkflowRepo
    DashboardService --> WorkflowRepo
    GuideService --> WorkflowRepo
    AuthService --> SecurityRepo
    AuditService --> SecurityRepo
    WorkflowRepo --> DB
    ScenarioRepo --> DB
    SecurityRepo --> DB
    API --> Redis
    Services --> Explainers
```

## Architectural intent

- The main workflow starts from uploaded transaction data, not canned scenarios.
- Reference scenarios are persistent seed data used for validation and controlled investigations.
- Scoring logic is deterministic by default and remains the source of truth.
- Optional AI integrations sit behind stable ports and fall back instead of taking the platform down.
- Alerts and cases are durable workflow state, not transient derived views.
- Cases persist an immutable evidence snapshot so historical investigations stay stable.

## Layer responsibilities

| Layer | Responsibility | Notes |
|------|----------------|-------|
| Next.js frontend | Operator workspace | Dashboard, dataset review, alerts, cases, reference investigations |
| FastAPI routes + middleware | HTTP contract | Auth, request context, security headers, audit logging |
| Application services | Workflow orchestration | Dataset analysis, investigations, alerts, cases, dashboard, auth |
| Infrastructure analysis | Scoring engines | Benford, outliers, velocity, round amounts, behavioral analysis, graph analysis |
| Provider adapters | Optional enrichment | Hugging Face text and explanations, RelationalAI reasoning |
| Repositories | Persistence boundary | SQLAlchemy-backed datasets, alerts, cases, audit, operators, scenarios |
| External services | Shared operational dependencies | Postgres/SQLite, Redis, optional Hugging Face, optional RelationalAI |

## Deployment topology

```mermaid
graph LR
    User[Operator browser]
    Frontend[Next.js container or dev server]
    Backend[FastAPI container or process]
    Postgres[(Postgres)]
    SQLite[(SQLite)]
    Redis[(Redis)]
    HF[Hugging Face API]
    RAI[RelationalAI adapter]

    User --> Frontend
    Frontend -->|REST /api/v1| Backend
    Backend --> Postgres
    Backend -. local/test fallback .-> SQLite
    Backend --> Redis
    Backend -. optional .-> HF
    Backend -. optional .-> RAI
```

The normal local container baseline uses Postgres and Redis. Tests and lightweight runs can use SQLite and in-memory rate limiting.

## Startup model

```mermaid
sequenceDiagram
    participant App as FastAPI lifespan
    participant Container as build_container
    participant DB as Database layer
    participant Security as Security bootstrap
    participant Providers as Provider selection

    App->>Container: build_container(settings)
    Container->>DB: build engine and session factory
    Container->>DB: initialize seed data and optional schema creation
    Container->>Security: bootstrap admin and analyst operators
    Container->>DB: prune expired audit events
    Container->>Providers: choose text, reasoning, explanation providers
    Providers-->>Container: active providers + startup notes
    Container-->>App: assembled services and runtime state
```

Important runtime properties:

- migrations are applied explicitly through `rfi-manage migrate`
- scenario seeding can happen at startup if enabled
- Redis rate limiting falls back to memory if Redis is unavailable
- Hugging Face and RelationalAI integrations degrade gracefully through fallback wrappers
- `/health` reports the resulting runtime posture

## Request and scoring model

### Dataset analysis path

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as FastAPI
    participant Dataset as DatasetService
    participant Engines as Analysis engines
    participant Alerts as AlertService

    UI->>API: POST /datasets/upload or /datasets/ingest
    API->>Dataset: persist dataset and transactions
    UI->>API: POST /datasets/{id}/analyze
    API->>Dataset: analyze(dataset_id)
    Dataset->>Engines: Benford + outliers + velocity + round amount + behavioral analysis
    Engines-->>Dataset: anomalies, graph analysis, leads, risk score
    Dataset-->>API: AnalysisResult
    API->>Alerts: auto-generate alerts when score >= 35
    API-->>UI: scored analysis payload
```

### Reference investigation path

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as FastAPI
    participant Investigation as InvestigationService
    participant Text as Text signal service
    participant Reasoner as Risk reasoner
    participant Graph as Graph analyzer
    participant Alerts as AlertService

    UI->>API: POST /investigations
    API->>Investigation: investigate(scenario_id)
    Investigation->>Text: score(scenario notes and merchant text)
    Investigation->>Reasoner: reason(scenario, text signals)
    Investigation->>Graph: analyze_scenario_graph(scenario)
    Investigation-->>API: InvestigationCase
    API->>Alerts: auto-generate alerts when score >= 35
    API-->>UI: investigation result
```

## Provider fallback model

```mermaid
flowchart TD
    Requested[Requested optional provider] --> Available{Can provider start or respond?}
    Available -->|yes| Active[Use requested provider]
    Available -->|no| Fallback[Switch to deterministic fallback]
    Fallback --> Notes[Attach startup or runtime notes]
    Active --> Result[Return result]
    Notes --> Result

    Result --> Guardrail[Risk thresholds, alert generation, and case creation rules stay unchanged]
```

This design is deliberate. Providers may improve text interpretation or analyst-facing language, but they do not own the core workflow state machine.

## Persistence model

```mermaid
erDiagram
    SCENARIOS ||--o{ CUSTOMERS : contains
    SCENARIOS ||--o{ ACCOUNTS : contains
    SCENARIOS ||--o{ DEVICES : contains
    SCENARIOS ||--o{ MERCHANTS : contains
    SCENARIOS ||--o{ TRANSACTIONS : contains
    SCENARIOS ||--o{ INVESTIGATOR_NOTES : contains

    CUSTOMERS ||--o{ ACCOUNTS : owns
    CUSTOMERS }o--o{ DEVICES : links_via_device_customer_links
    CUSTOMERS ||--o{ INVESTIGATOR_NOTES : subject_of

    DATASETS ||--o{ FRAUD_ALERTS : source_for
    DATASETS ||--o{ FRAUD_CASES : source_for
    SCENARIOS ||--o{ FRAUD_ALERTS : source_for
    SCENARIOS ||--o{ FRAUD_CASES : source_for

    FRAUD_CASES ||--o{ FRAUD_ALERTS : may_link
    OPERATOR_USERS ||--o{ AUDIT_EVENTS : generates
```

What is persisted:

- scenario catalog and all related entities
- operator users and audit events
- uploaded datasets, raw uploaded transactions, and completed analysis JSON
- fraud alerts
- fraud cases, comment count, alert count, and immutable `evidence_snapshot`

What is derived at read time:

- dashboard aggregates
- `/health` posture summaries
- workflow guidance content

## Durable evidence rule

Case detail is intentionally audit-stable:

- creating a case from a dataset stores the analysis-backed evidence snapshot
- creating a case from a scenario investigation stores the investigation-backed evidence snapshot
- later rule, provider, or seed-data changes do not rewrite that stored case evidence

That decision is one of the most important workflow guarantees in the project.

## API surface

| Method | Path | Category | Purpose |
|--------|------|----------|---------|
| GET | `/health` | System | Health and runtime posture |
| POST | `/auth/token` | Authentication | Operator login |
| GET | `/auth/me` | Authentication | Current operator |
| GET | `/workspace/guide` | Dashboard | Workflow guidance |
| GET | `/dashboard/stats` | Dashboard | Aggregated workflow metrics |
| GET | `/scenarios` | Investigations | List reference scenarios |
| GET | `/scenarios/{id}` | Investigations | Scenario detail |
| POST | `/investigations` | Investigations | Run reference investigation |
| POST | `/investigations/{id}/case` | Investigations | Open case from investigation |
| POST | `/datasets/upload` | Datasets | Upload CSV |
| POST | `/datasets/ingest` | Datasets | Ingest JSON transactions |
| GET | `/datasets` | Datasets | List datasets |
| POST | `/datasets/{id}/analyze` | Datasets | Run analysis |
| GET | `/datasets/{id}/analysis` | Datasets | Read analysis |
| GET | `/datasets/{id}/explanation` | Datasets | Read operator explanation |
| POST | `/datasets/{id}/case` | Datasets | Open case from analysis |
| GET | `/alerts` | Alerts | List alerts |
| PATCH | `/alerts/{id}` | Alerts | Update alert status or linkage |
| POST | `/alerts/{id}/case` | Alerts | Open case from alert source |
| POST | `/cases` | Cases | Create case |
| GET | `/cases` | Cases | List cases |
| GET | `/cases/{id}` | Cases | Case detail |
| PATCH | `/cases/{id}/status` | Cases | Update case lifecycle |
| POST | `/cases/{id}/comments` | Cases | Add comment |
| GET | `/audit-events` | Admin | Read audit trail |

## Design rules worth preserving

- Keep scoring deterministic and explainable by default.
- Keep optional providers behind explicit interfaces and fallbacks.
- Treat alerts and cases as workflow state, not cache.
- Preserve historical evidence with stored snapshots.
- Keep dataset analysis as the primary product flow.
