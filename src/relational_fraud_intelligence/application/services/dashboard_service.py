from __future__ import annotations

from datetime import UTC, datetime

from relational_fraud_intelligence.application.dto.dashboard import (
    GetDashboardStatsQuery,
    GetDashboardStatsResult,
)
from relational_fraud_intelligence.application.dto.investigation import ListScenariosQuery
from relational_fraud_intelligence.application.ports.repositories import (
    AlertRepository,
    CaseRepository,
    DatasetStore,
    ScenarioRepository,
)
from relational_fraud_intelligence.domain.models import (
    ActivityEvent,
    AnalysisResult,
    DashboardStats,
    Dataset,
    WorkflowStageSnapshot,
)


class DashboardService:
    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        case_repository: CaseRepository,
        alert_repository: AlertRepository,
        dataset_store: DatasetStore | None = None,
    ) -> None:
        self._scenario_repo = scenario_repository
        self._case_repo = case_repository
        self._alert_repo = alert_repository
        self._dataset_store = dataset_store

    async def get_stats(self, query: GetDashboardStatsQuery) -> GetDashboardStatsResult:
        _ = query
        scenarios = await self._scenario_repo.list_scenarios(ListScenariosQuery())
        cases_by_status = await self._case_repo.count_by_status()
        critical_cases = await self._case_repo.count_critical()
        alerts_by_severity = await self._alert_repo.count_by_severity()
        unacknowledged = await self._alert_repo.count_unacknowledged()

        total_cases = sum(cases_by_status.values())
        open_cases = cases_by_status.get("open", 0) + cases_by_status.get("investigating", 0)
        total_alerts = sum(alerts_by_severity.values())

        # Dataset stats
        total_datasets = 0
        total_txns_analyzed = 0
        total_anomalies_found = 0
        results: list[AnalysisResult] = []
        datasets: list[Dataset] = []
        if self._dataset_store is not None:
            datasets = await self._dataset_store.list_datasets()
            results = await self._dataset_store.list_results()
            total_datasets = len(datasets)
            total_txns_analyzed = await self._dataset_store.total_transactions()
            total_anomalies_found = await self._dataset_store.total_anomalies()
        completed_analyses = len(results)
        high_risk_analyses = sum(1 for result in results if result.risk_score >= 35)
        pending_analysis = sum(1 for dataset in datasets if dataset.status == "uploaded")

        recent_cases, _ = await self._case_repo.list_cases(page=1, page_size=25)
        recent_alerts, _ = await self._alert_repo.list_alerts(page=1, page_size=25)

        risk_distribution: dict[str, int] = {}
        risk_values: list[int] = []
        for case in recent_cases:
            risk_distribution[case.risk_level] = risk_distribution.get(case.risk_level, 0) + 1
            risk_values.append(case.risk_score)
        for result in results:
            risk_distribution[result.risk_level] = risk_distribution.get(result.risk_level, 0) + 1
            risk_values.append(result.risk_score)

        avg_risk = round(sum(risk_values) / len(risk_values), 1) if risk_values else 0.0

        activity: list[ActivityEvent] = []
        for case in recent_cases[:5]:
            activity.append(
                ActivityEvent(
                    event_type="case-opened",
                    description=f"{case.title} is {case.status}.",
                    actor=case.assigned_analyst_name,
                    occurred_at=_as_utc(case.updated_at),
                    resource_id=case.case_id,
                )
            )
        for alert in recent_alerts[:5]:
            activity.append(
                ActivityEvent(
                    event_type="alert-generated",
                    description=(
                        f"{alert.title} is {alert.status} for {alert.source_type} "
                        f"{alert.source_id}."
                    ),
                    actor=alert.assigned_analyst_name,
                    occurred_at=_as_utc(alert.created_at),
                    resource_id=alert.alert_id,
                )
            )
        for dataset in datasets[:5]:
            activity.append(
                ActivityEvent(
                    event_type="dataset-uploaded",
                    description=(f"{dataset.name} uploaded with {dataset.row_count} transactions."),
                    occurred_at=_as_utc(dataset.uploaded_at),
                    resource_id=dataset.dataset_id,
                )
            )
        for result in results[:5]:
            activity.append(
                ActivityEvent(
                    event_type="dataset-analyzed",
                    description=(
                        f"Analysis completed with {result.total_anomalies} anomalies "
                        f"and risk score {result.risk_score}/100."
                    ),
                    occurred_at=_as_utc(result.completed_at),
                    resource_id=result.dataset_id,
                )
            )

        activity.sort(key=lambda event: event.occurred_at, reverse=True)
        workflow_stages = [
            WorkflowStageSnapshot(
                stage_id="upload",
                title="Upload",
                description="Datasets waiting to enter the scoring workflow.",
                total_count=total_datasets,
                highlighted_count=pending_analysis,
                highlighted_label="waiting for analysis",
            ),
            WorkflowStageSnapshot(
                stage_id="analyze",
                title="Analyze",
                description=(
                    "Completed statistical and behavioral analyses over uploaded transaction data."
                ),
                total_count=completed_analyses,
                highlighted_count=high_risk_analyses,
                highlighted_label="high-risk analyses",
            ),
            WorkflowStageSnapshot(
                stage_id="alert",
                title="Alert",
                description="Alerts created from scored findings and triage thresholds.",
                total_count=total_alerts,
                highlighted_count=unacknowledged,
                highlighted_label="new alerts",
            ),
            WorkflowStageSnapshot(
                stage_id="case",
                title="Case",
                description="Persistent investigations opened from alerts or dataset reviews.",
                total_count=total_cases,
                highlighted_count=open_cases,
                highlighted_label="open cases",
            ),
        ]

        return GetDashboardStatsResult(
            stats=DashboardStats(
                total_scenarios=len(scenarios.scenarios),
                total_cases=total_cases,
                open_cases=open_cases,
                critical_cases=critical_cases,
                total_alerts=total_alerts,
                unacknowledged_alerts=unacknowledged,
                avg_risk_score=round(avg_risk, 1),
                cases_by_status=cases_by_status,
                alerts_by_severity=alerts_by_severity,
                recent_activity=activity[:10],
                risk_distribution=risk_distribution,
                total_datasets=total_datasets,
                total_transactions_analyzed=total_txns_analyzed,
                total_anomalies_found=total_anomalies_found,
                completed_analyses=completed_analyses,
                high_risk_analyses=high_risk_analyses,
                workflow_stages=workflow_stages,
                next_recommended_action=_next_recommended_action(
                    pending_analysis=pending_analysis,
                    high_risk_analyses=high_risk_analyses,
                    unacknowledged_alerts=unacknowledged,
                    open_cases=open_cases,
                ),
            )
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _next_recommended_action(
    *,
    pending_analysis: int,
    high_risk_analyses: int,
    unacknowledged_alerts: int,
    open_cases: int,
) -> str:
    if pending_analysis:
        return "Run analysis on newly uploaded datasets before the queue ages."
    if unacknowledged_alerts:
        return "Triage the new alert queue and link the highest-risk findings to cases."
    if high_risk_analyses and not open_cases:
        return (
            "Create a case from the highest-risk dataset analysis so the review stays persistent."
        )
    if open_cases:
        return "Advance open cases with comments, dispositions, or resolution notes."
    return "Upload a dataset to start the primary workflow."
