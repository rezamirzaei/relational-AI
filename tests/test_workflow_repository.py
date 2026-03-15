from __future__ import annotations

from datetime import UTC, datetime

from relational_fraud_intelligence.application.dto.alerts import CreateAlertCommand, ListAlertsQuery
from relational_fraud_intelligence.application.dto.cases import (
    AddCaseCommentCommand,
    CreateCaseCommand,
    GetCaseQuery,
    ListCasesQuery,
)
from relational_fraud_intelligence.application.ports.repositories import (
    AlertRepository,
    CaseRepository,
    DatasetStore,
)
from relational_fraud_intelligence.application.services.alert_service import AlertService
from relational_fraud_intelligence.application.services.case_service import CaseService
from relational_fraud_intelligence.application.services.dataset_service import DatasetService
from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    CaseEvidenceSnapshot,
    Dataset,
    DatasetStatus,
    RiskLevel,
    WorkflowSourceType,
)


async def test_sql_case_repository_persists_cases_and_comments(
    case_repository: CaseRepository,
) -> None:
    service = CaseService(case_repository)
    evidence_snapshot = CaseEvidenceSnapshot(
        dataset=Dataset(
            dataset_id="dataset-42",
            name="dataset-42.csv",
            uploaded_at=datetime.now(UTC),
            row_count=12,
            status=DatasetStatus.COMPLETED,
        )
    )
    created = await service.create_case(
        CreateCaseCommand(
            source_type=WorkflowSourceType.DATASET,
            source_id="dataset-42",
            title="Dataset case",
            summary="Round-amount activity needs review.",
            risk_score=70,
            risk_level=RiskLevel.HIGH,
        ),
        evidence_snapshot=evidence_snapshot,
    )

    await service.add_comment(
        AddCaseCommentCommand(case_id=created.case.case_id, body="Escalated for review."),
        author_id="analyst-1",
        author_name="Analyst One",
    )

    fetched = await service.get_case(GetCaseQuery(case_id=created.case.case_id))
    listed = await service.list_cases(ListCasesQuery())

    assert fetched.case.source_type == WorkflowSourceType.DATASET
    assert fetched.case.comment_count == 1
    assert fetched.case.evidence_snapshot is not None
    assert fetched.case.evidence_snapshot.dataset is not None
    assert fetched.case.evidence_snapshot.dataset.dataset_id == "dataset-42"
    assert listed.total_count == 1
    assert listed.cases[0].source_id == "dataset-42"


async def test_sql_alert_repository_filters_by_source(alert_repository: AlertRepository) -> None:
    service = AlertService(alert_repository)
    created = await service.create_alert(
        CreateAlertCommand(
            source_type=WorkflowSourceType.DATASET,
            source_id="dataset-42",
            rule_code="round-amount",
            title="Round amount pattern",
            severity=RiskLevel.MEDIUM,
            narrative="Exact-value transactions dominate the dataset.",
        )
    )

    listed = await service.list_alerts(ListAlertsQuery())

    assert listed.total_count == 1
    assert listed.alerts[0].status == AlertStatus.NEW
    assert listed.alerts[0].alert_id == created.alert.alert_id


async def test_sql_dataset_store_persists_analysis_results(dataset_store: DatasetStore) -> None:
    service = DatasetService(dataset_store)
    dataset = await service.ingest_transactions(
        "api-upload",
        [
            {
                "transaction_id": "T1",
                "account_id": "A1",
                "amount": 500,
                "timestamp": "2026-03-01 09:00:00",
            },
            {
                "transaction_id": "T2",
                "account_id": "A1",
                "amount": 500,
                "timestamp": "2026-03-01 09:05:00",
            },
            {
                "transaction_id": "T3",
                "account_id": "A1",
                "amount": 500,
                "timestamp": "2026-03-01 09:10:00",
            },
        ],
    )

    result = await service.analyze(dataset.dataset_id)

    assert (await service.get_dataset(dataset.dataset_id)).status == DatasetStatus.COMPLETED
    assert (await service.get_result(dataset.dataset_id)).analysis_id == result.analysis_id
    assert await dataset_store.list_results()
    assert await dataset_store.total_transactions() == 3
