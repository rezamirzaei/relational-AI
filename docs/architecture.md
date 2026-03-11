# Architecture

## Core principles

- All application boundaries use Pydantic objects.
- Domain logic is separated from provider integrations.
- Providers are hidden behind ports so demo, Hugging Face, and RelationalAI implementations can be swapped without changing the use case.
- Fallback behavior is explicit and surfaced to the UI through provider notes.

## Main patterns

- Repository pattern: `ScenarioRepository`
- Strategy pattern: text signal and risk reasoner providers
- Fallback/decorator pattern: provider wrappers for graceful degradation
- Assembler pattern: investigation response assembly
- Ports and adapters: application ports own the contract, infrastructure owns vendor integration

## Request flow

1. The UI posts an `InvestigateScenarioCommand`.
2. `InvestigationService` loads a `FraudScenario`.
3. `TextSignalService` enriches notes and merchant descriptions.
4. `RiskReasoner` evaluates relational fraud patterns.
5. `InvestigationCaseAssembler` builds the product-facing `InvestigationCase`.
6. The API returns one stable response shape to the UI.

## RelationalAI integration shape

The `RelationalAIRiskReasoner` is isolated in the infrastructure layer. It currently:

- Builds a RelationalAI semantic projection from the scenario data.
- Uses the current SDK with a local DuckDB-backed config by default.
- Can switch to an external `raiconfig.yaml` path when enabled.
- Preserves the same `ReasonAboutRiskResult` contract, so the application layer is unaffected.

This lets the project stay runnable locally while keeping the vendor integration where it belongs.
