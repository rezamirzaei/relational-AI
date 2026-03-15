"""Dashboard and workspace guide endpoints."""

from fastapi import APIRouter, Request

from relational_fraud_intelligence.api._helpers import AnalystDep, ContainerDep
from relational_fraud_intelligence.application.dto.dashboard import (
    GetDashboardStatsQuery,
    GetDashboardStatsResult,
    GetWorkspaceGuideResult,
)

router = APIRouter()


@router.get(
    "/workspace/guide",
    response_model=GetWorkspaceGuideResult,
    tags=["Dashboard"],
    summary="Get the primary workflow guide",
    description=(
        "Returns the dataset-first workflow, role stories, scoring "
        "guarantees, and copilot positioning used by the frontend workspace."
    ),
)
async def get_workspace_guide(
    request: Request,
    container: ContainerDep,
) -> GetWorkspaceGuideResult:
    request.state.audit_action = "get-workspace-guide"
    request.state.audit_resource_type = "workspace-guide"
    return GetWorkspaceGuideResult(guide=container.workspace_guide_service.get_guide())


@router.get(
    "/dashboard/stats",
    response_model=GetDashboardStatsResult,
    tags=["Dashboard"],
    summary="Get dashboard statistics",
    description=(
        "Returns aggregate metrics for the analyst dashboard: case counts, "
        "alert counts, risk distribution, and recent activity."
    ),
)
async def get_dashboard_stats(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> GetDashboardStatsResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-dashboard-stats"
    request.state.audit_resource_type = "dashboard"
    return await container.dashboard_service.get_stats(GetDashboardStatsQuery())
