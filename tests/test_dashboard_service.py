from __future__ import annotations

from relational_fraud_intelligence.application.dto.alerts import CreateAlertCommand
from relational_fraud_intelligence.application.dto.cases import CreateCaseCommand
from relational_fraud_intelligence.application.dto.dashboard import GetDashboardStatsQuery
from relational_fraud_intelligence.application.ports.repositories import (
    AlertRepository,
    CaseRepository,
    DatasetStore,
    ScenarioRepository,
)
from relational_fraud_intelligence.application.services.alert_service import AlertService
from relational_fraud_intelligence.application.services.case_service import CaseService
from relational_fraud_intelligence.application.services.dashboard_service import DashboardService
from relational_fraud_intelligence.application.services.dataset_service import DatasetService
from relational_fraud_intelligence.domain.models import RiskLevel, WorkflowSourceType


async def test_dashboard_stats_reflect_real_workflow_activity(
    scenario_repository: ScenarioRepository,
    case_repository: CaseRepository,
    alert_repository: AlertRepository,
    dataset_store: DatasetStore,
) -> None:
    case_service = CaseService(case_repository)
    alert_service = AlertService(alert_repository)
    dataset_service = DatasetService(dataset_store)

    dataset = await dataset_service.ingest_transactions(
        "triage.csv",
        [
            {
                "transaction_id": "T1",
                "account_id": "A1",
                "amount": 1000,
                "timestamp": "2026-03-01 10:00:00",
            },
            {
                "transaction_id": "T2",
                "account_id": "A1",
                "amount": 1000,
                "timestamp": "2026-03-01 10:05:00",
            },
            {
                "transaction_id": "T3",
                "account_id": "A1",
                "amount": 1000,
                "timestamp": "2026-03-01 10:10:00",
            },
            {
                "transaction_id": "T4",
                "account_id": "A1",
                "amount": 1000,
                "timestamp": "2026-03-01 10:12:00",
            },
        ],
    )
    analysis = await dataset_service.analyze(dataset.dataset_id)

    await case_service.create_case(
        CreateCaseCommand(
            source_type=WorkflowSourceType.DATASET,
            source_id=dataset.dataset_id,
            title="Dataset review",
            summary=analysis.summary,
            risk_score=analysis.risk_score,
            risk_level=analysis.risk_level,
        )
    )
    await alert_service.create_alert(
        CreateAlertCommand(
            source_type=WorkflowSourceType.DATASET,
            source_id=dataset.dataset_id,
            rule_code="velocity-spike",
            title="Velocity spike",
            severity=RiskLevel.HIGH,
            narrative="Windowed activity exceeded the normal baseline.",
        )
    )

    service = DashboardService(
        scenario_repository=scenario_repository,
        case_repository=case_repository,
        alert_repository=alert_repository,
        dataset_store=dataset_store,
    )

    result = await service.get_stats(GetDashboardStatsQuery())

    assert result.stats.total_scenarios == 3
    assert result.stats.total_datasets == 1
    assert result.stats.total_cases == 1
    assert result.stats.total_alerts == 1
    assert result.stats.total_transactions_analyzed == 4
    assert result.stats.completed_analyses == 1
    assert result.stats.high_risk_analyses == int(analysis.risk_score >= 35)
    assert result.stats.avg_risk_score > 0
    assert result.stats.recent_activity
    assert [stage.stage_id for stage in result.stats.workflow_stages] == [
        "upload",
        "analyze",
        "alert",
        "case",
    ]
    assert result.stats.next_recommended_action.startswith("Triage the new alert queue")
    assert any(event.event_type == "dataset-analyzed" for event in result.stats.recent_activity)
