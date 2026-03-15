"""Scenario catalog and investigation endpoints."""

from fastapi import APIRouter, HTTPException, Request

from relational_fraud_intelligence.api._helpers import (
    AnalystDep,
    ContainerDep,
    build_case_command_from_investigation,
    build_scenario_case_snapshot,
    create_case_with_source_links,
    findings_from_investigation,
    validate_case_source,
)
from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    InvestigateScenarioCommand,
    InvestigateScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.application.dto.routes import (
    CreateCaseFromInvestigationResult,
)

router = APIRouter()


@router.get(
    "/scenarios",
    response_model=ListScenariosResult,
    tags=["Investigations"],
    summary="List fraud scenarios",
    description="Returns all seeded fraud scenarios with baseline risk assessment.",
)
def list_scenarios(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> ListScenariosResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-scenarios"
    request.state.audit_resource_type = "fraud-scenario"
    return container.scenario_catalog_service.list_scenarios(ListScenariosQuery())


@router.get(
    "/scenarios/{scenario_id}",
    response_model=GetScenarioResult,
    tags=["Investigations"],
    summary="Get scenario details",
    description=(
        "Returns full scenario data including customers, accounts, devices, "
        "merchants, and transactions."
    ),
)
def get_scenario(
    scenario_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> GetScenarioResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-scenario"
    request.state.audit_resource_type = "fraud-scenario"
    request.state.audit_resource_id = scenario_id
    try:
        return container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/investigations",
    response_model=InvestigateScenarioResult,
    tags=["Investigations"],
    summary="Run fraud investigation",
    description=(
        "Executes a full fraud investigation on a reference scenario: text "
        "signal extraction, rule-based risk reasoning, graph analysis, and "
        "case assembly."
    ),
)
def investigate_scenario(
    command: InvestigateScenarioCommand,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> InvestigateScenarioResult:
    request.state.current_principal = principal
    request.state.audit_action = "investigate-scenario"
    request.state.audit_resource_type = "fraud-scenario"
    request.state.audit_resource_id = command.scenario_id
    try:
        result = container.investigation_service.execute(command)

        # Auto-generate alerts from high-risk investigations
        if result.investigation.total_risk_score >= 35:
            container.alert_service.generate_alerts_from_investigation(
                scenario_id=command.scenario_id,
                risk_score=result.investigation.total_risk_score,
                rule_hits=findings_from_investigation(result.investigation),
            )

        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/investigations/{scenario_id}/case",
    response_model=CreateCaseFromInvestigationResult,
    tags=["Investigations"],
    summary="Create a case from a scenario investigation",
    description=(
        "Runs the scenario investigation, creates a persistent fraud case from the "
        "highest-signal scenario leads, and links any open scenario alerts to that case."
    ),
)
def create_case_from_investigation(
    scenario_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> CreateCaseFromInvestigationResult:
    request.state.current_principal = principal
    request.state.audit_action = "create-case-from-investigation"
    request.state.audit_resource_type = "fraud-scenario"
    request.state.audit_resource_id = scenario_id
    try:
        result = container.investigation_service.execute(
            InvestigateScenarioCommand(scenario_id=scenario_id)
        )
        scenario = container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        ).scenario
        related_alerts = container.alert_service.generate_alerts_from_investigation(
            scenario_id=scenario_id,
            risk_score=result.investigation.total_risk_score,
            rule_hits=findings_from_investigation(result.investigation),
        )
        evidence_snapshot = build_scenario_case_snapshot(
            investigation=result.investigation,
            scenario_transactions=scenario.transactions,
            investigator_notes=scenario.investigator_notes,
        )
        case_command = build_case_command_from_investigation(result.investigation)
        validate_case_source(case_command, container)
        created_case, linked_alerts = create_case_with_source_links(
            command=case_command,
            container=container,
            evidence_snapshot=evidence_snapshot,
            related_alerts=related_alerts,
        )

        return CreateCaseFromInvestigationResult(
            investigation=result.investigation,
            case=created_case,
            linked_alerts=linked_alerts,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

