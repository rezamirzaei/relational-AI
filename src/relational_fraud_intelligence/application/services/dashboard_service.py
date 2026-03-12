from __future__ import annotations

from datetime import UTC, datetime

from relational_fraud_intelligence.application.dto.dashboard import (
    GetDashboardStatsQuery,
    GetDashboardStatsResult,
)
from relational_fraud_intelligence.application.dto.investigation import ListScenariosQuery
from relational_fraud_intelligence.application.ports.repositories import ScenarioRepository
from relational_fraud_intelligence.application.services.alert_service import AlertRepository
from relational_fraud_intelligence.application.services.case_service import CaseRepository
from relational_fraud_intelligence.application.services.dataset_service import DatasetStore
from relational_fraud_intelligence.domain.models import (
    ActivityEvent,
    AnalysisResult,
    DashboardStats,
    Dataset,
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

    def get_stats(self, query: GetDashboardStatsQuery) -> GetDashboardStatsResult:
        _ = query
        scenarios = self._scenario_repo.list_scenarios(ListScenariosQuery())
        cases_by_status = self._case_repo.count_by_status()
        critical_cases = self._case_repo.count_critical()
        alerts_by_severity = self._alert_repo.count_by_severity()
        unacknowledged = self._alert_repo.count_unacknowledged()

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
            datasets = self._dataset_store.list_datasets()
            results = self._dataset_store.list_results()
            total_datasets = len(datasets)
            total_txns_analyzed = self._dataset_store.total_transactions()
            total_anomalies_found = self._dataset_store.total_anomalies()

        recent_cases, _ = self._case_repo.list_cases(page=1, page_size=25)
        recent_alerts, _ = self._alert_repo.list_alerts(page=1, page_size=25)

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
            )
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
