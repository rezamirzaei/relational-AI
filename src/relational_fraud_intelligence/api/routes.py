from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from relational_fraud_intelligence.api.dependencies import get_container
from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    InvestigateScenarioCommand,
    InvestigateScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.bootstrap import ApplicationContainer
from relational_fraud_intelligence.domain.models import AppModel

router = APIRouter()
ContainerDep = Annotated[ApplicationContainer, Depends(get_container)]


class HealthResponse(AppModel):
    status: str
    app_name: str
    environment: str
    database_status: str
    seeded_scenarios: int


@router.get("/health", response_model=HealthResponse)
def health(container: ContainerDep) -> HealthResponse:
    return HealthResponse(
        status="ok" if container.is_database_ready() else "degraded",
        app_name=container.settings.app_name,
        environment=container.settings.app_env,
        database_status="ready" if container.is_database_ready() else "unavailable",
        seeded_scenarios=container.seed_result.inserted_scenarios,
    )


@router.get("/scenarios", response_model=ListScenariosResult)
def list_scenarios(container: ContainerDep) -> ListScenariosResult:
    return container.scenario_catalog_service.list_scenarios(ListScenariosQuery())


@router.get("/scenarios/{scenario_id}", response_model=GetScenarioResult)
def get_scenario(
    scenario_id: str,
    container: ContainerDep,
) -> GetScenarioResult:
    try:
        return container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/investigations", response_model=InvestigateScenarioResult)
def investigate_scenario(
    command: InvestigateScenarioCommand,
    container: ContainerDep,
) -> InvestigateScenarioResult:
    try:
        return container.investigation_service.execute(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
