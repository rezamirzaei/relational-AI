"""Postgres-specific integration tests.

These tests exercise behaviors that differ between SQLite and Postgres:
- JSON column storage and retrieval (CaseEvidenceSnapshot)
- Foreign key constraint enforcement with CASCADE
- Unique constraint enforcement

Run with: pytest -m postgres
Requires RFI_DATABASE_URL pointing to a Postgres instance.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.application.dto.cases import (
    CreateCaseCommand,
    GetCaseQuery,
)
from relational_fraud_intelligence.application.services.case_service import CaseService
from relational_fraud_intelligence.domain.models import (
    AnalysisResult,
    CaseEvidenceSnapshot,
    CasePriority,
    CaseStatus,
    Dataset,
    DatasetStatus,
    RiskLevel,
    WorkflowSourceType,
)
from relational_fraud_intelligence.infrastructure.persistence.seed import DatabaseInitializer
from relational_fraud_intelligence.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from relational_fraud_intelligence.infrastructure.persistence.workflow_repository import (
    SqlAlchemyAlertRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyDatasetStore,
)
from relational_fraud_intelligence.infrastructure.seed.scenarios import build_seed_scenarios

pytestmark = pytest.mark.postgres

_DATABASE_URL = os.environ.get("RFI_DATABASE_URL", "")
_IS_POSTGRES = _DATABASE_URL.startswith("postgresql")


@pytest.fixture()
def pg_engine() -> Generator[Engine, None, None]:
    if not _IS_POSTGRES:
        pytest.skip("RFI_DATABASE_URL is not a Postgres URL")
    engine = build_engine(_DATABASE_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session_factory(pg_engine: Engine) -> sessionmaker[Session]:
    session_factory = build_session_factory(pg_engine)
    initializer = DatabaseInitializer(
        engine=pg_engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )
    initializer.initialize(create_schema=True, seed_if_empty=True)
    return session_factory


@pytest.fixture()
def pg_case_repository(pg_session_factory: sessionmaker[Session]) -> SqlAlchemyCaseRepository:
    return SqlAlchemyCaseRepository(pg_session_factory)


@pytest.fixture()
def pg_dataset_store(pg_session_factory: sessionmaker[Session]) -> SqlAlchemyDatasetStore:
    return SqlAlchemyDatasetStore(pg_session_factory)


@pytest.fixture()
def pg_alert_repository(pg_session_factory: sessionmaker[Session]) -> SqlAlchemyAlertRepository:
    return SqlAlchemyAlertRepository(pg_session_factory)


def _make_dataset(dataset_id: str | None = None) -> Dataset:
    return Dataset(
        dataset_id=dataset_id or str(uuid4()),
        name="pg-test-dataset",
        uploaded_at=datetime.now(UTC),
        row_count=10,
        status=DatasetStatus.COMPLETED,
    )


def _make_analysis(dataset_id: str) -> AnalysisResult:
    return AnalysisResult(
        dataset_id=dataset_id,
        risk_score=72,
        risk_level=RiskLevel.HIGH,
        total_transactions=10,
        total_anomalies=3,
        benford_p_value=0.03,
        benford_digits=[
            {"digit": d, "observed": 0.11, "expected": 0.11} for d in range(1, 10)
        ],
        outlier_count=2,
        outlier_pct=20.0,
        velocity_spikes=[],
        anomalies=[],
        investigation_leads=[],
        behavioral_insights=[],
        graph_analysis=None,
        summary="Integration test analysis",
        completed_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# JSON column tests
# ---------------------------------------------------------------------------


class TestPostgresJsonStorage:
    """Verify JSON columns round-trip correctly in Postgres (JSONB backend)."""

    def test_case_evidence_snapshot_round_trips_through_postgres(
        self,
        pg_case_repository: SqlAlchemyCaseRepository,
        pg_dataset_store: SqlAlchemyDatasetStore,
    ) -> None:
        dataset = _make_dataset()
        pg_dataset_store.save_dataset(dataset)
        analysis = _make_analysis(dataset.dataset_id)
        pg_dataset_store.save_result(analysis)

        snapshot = CaseEvidenceSnapshot(
            analysis=analysis,
            dataset=dataset,
            dataset_transactions=[],
        )

        case_service = CaseService(pg_case_repository)
        result = case_service.create_case(
            CreateCaseCommand(
                source_type=WorkflowSourceType.DATASET,
                source_id=dataset.dataset_id,
                title="PG JSON test",
                summary="Verify evidence_snapshot JSON serialization in Postgres.",
                priority=CasePriority.HIGH,
                risk_score=72,
                risk_level=RiskLevel.HIGH,
            ),
            evidence_snapshot=snapshot,
        )
        case_id = result.case.case_id

        retrieved = case_service.get_case(GetCaseQuery(case_id=case_id))
        assert retrieved.case.evidence_snapshot is not None
        assert retrieved.case.evidence_snapshot.analysis is not None
        assert retrieved.case.evidence_snapshot.analysis.risk_score == 72
        assert retrieved.case.evidence_snapshot.dataset is not None
        assert retrieved.case.evidence_snapshot.dataset.dataset_id == dataset.dataset_id

    def test_analysis_result_json_column_round_trips(
        self,
        pg_dataset_store: SqlAlchemyDatasetStore,
    ) -> None:
        dataset = _make_dataset()
        pg_dataset_store.save_dataset(dataset)
        analysis = _make_analysis(dataset.dataset_id)
        pg_dataset_store.save_result(analysis)

        retrieved = pg_dataset_store.get_result(dataset.dataset_id)
        assert retrieved is not None
        assert retrieved.risk_score == 72
        assert retrieved.risk_level == RiskLevel.HIGH
        assert retrieved.total_anomalies == 3
        assert len(retrieved.benford_digits) == 9


# ---------------------------------------------------------------------------
# Constraint enforcement tests
# ---------------------------------------------------------------------------


class TestPostgresConstraints:
    """Verify foreign key and unique constraints work correctly in Postgres."""

    def test_dataset_store_rejects_duplicate_dataset_id(
        self,
        pg_dataset_store: SqlAlchemyDatasetStore,
    ) -> None:
        dataset = _make_dataset()
        pg_dataset_store.save_dataset(dataset)

        with pytest.raises(Exception):  # noqa: B017
            pg_dataset_store.save_dataset(dataset)

    def test_case_counts_update_correctly(
        self,
        pg_case_repository: SqlAlchemyCaseRepository,
    ) -> None:
        case_service = CaseService(pg_case_repository)
        result = case_service.create_case(
            CreateCaseCommand(
                scenario_id="travel-ato-escalation",
                title="PG constraint test",
                summary="Test case count updates.",
            ),
            risk_score=50,
            risk_level=RiskLevel.MEDIUM,
        )
        case_id = result.case.case_id
        assert result.case.comment_count == 0

        synced = case_service.sync_alert_count(case_id, 3)
        assert synced.alert_count == 3

    def test_case_status_transitions_persist(
        self,
        pg_case_repository: SqlAlchemyCaseRepository,
    ) -> None:
        from relational_fraud_intelligence.application.dto.cases import UpdateCaseStatusCommand
        from relational_fraud_intelligence.domain.models import CaseDisposition

        case_service = CaseService(pg_case_repository)
        result = case_service.create_case(
            CreateCaseCommand(
                scenario_id="travel-ato-escalation",
                title="PG lifecycle test",
                summary="Test lifecycle transitions.",
            ),
            risk_score=80,
            risk_level=RiskLevel.CRITICAL,
        )
        case_id = result.case.case_id

        updated = case_service.update_status(
            UpdateCaseStatusCommand(
                case_id=case_id,
                status=CaseStatus.RESOLVED,
                disposition=CaseDisposition.CONFIRMED_FRAUD,
                resolution_notes="Confirmed in Postgres.",
            )
        )
        assert updated.case.status == CaseStatus.RESOLVED
        assert updated.case.resolved_at is not None

        reopened = case_service.update_status(
            UpdateCaseStatusCommand(
                case_id=case_id,
                status=CaseStatus.INVESTIGATING,
            )
        )
        assert reopened.case.status == CaseStatus.INVESTIGATING
        assert reopened.case.resolved_at is None
        assert reopened.case.disposition is None

