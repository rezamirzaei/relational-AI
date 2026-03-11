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


class HealthResponse(AppModel):
    status: str
    app_name: str
    environment: str


@router.get("/health", response_model=HealthResponse)
def health(container: ApplicationContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=container.settings.app_name,
        environment=container.settings.app_env,
    )


@router.get("/scenarios", response_model=ListScenariosResult)
def list_scenarios(container: ApplicationContainer = Depends(get_container)) -> ListScenariosResult:
    return container.scenario_catalog_service.list_scenarios(ListScenariosQuery())


@router.get("/scenarios/{scenario_id}", response_model=GetScenarioResult)
def get_scenario(
    scenario_id: str,
    container: ApplicationContainer = Depends(get_container),
) -> GetScenarioResult:
    try:
        return container.scenario_catalog_service.get_scenario(GetScenarioQuery(scenario_id=scenario_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/investigations", response_model=InvestigateScenarioResult)
def investigate_scenario(
    command: InvestigateScenarioCommand,
    container: ApplicationContainer = Depends(get_container),
) -> InvestigateScenarioResult:
    try:
        return container.investigation_service.execute(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
