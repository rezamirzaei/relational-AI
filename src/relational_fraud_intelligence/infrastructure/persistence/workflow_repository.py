from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AnalysisResult,
    CaseComment,
    CasePriority,
    CaseStatus,
    Dataset,
    FraudAlert,
    FraudCase,
    RiskLevel,
    UploadedTransaction,
    WorkflowSourceType,
)
from relational_fraud_intelligence.infrastructure.persistence.mappers import (
    to_alert_record,
    to_case_record,
    to_dataset_record,
    to_domain_alert,
    to_domain_analysis,
    to_domain_case,
    to_domain_comments,
    to_domain_dataset,
    to_domain_transactions,
    to_json_analysis,
    to_json_transactions,
)
from relational_fraud_intelligence.infrastructure.persistence.models import (
    DatasetRecord,
    FraudAlertRecord,
    FraudCaseRecord,
)


class SqlAlchemyCaseRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_case(self, case: FraudCase) -> None:
        with self._session_factory.begin() as session:
            session.add(to_case_record(case, comments=[]))

    def get_case(self, case_id: str) -> FraudCase | None:
        with self._session_factory() as session:
            record = session.get(FraudCaseRecord, case_id)
            return to_domain_case(record) if record is not None else None

    def update_case(self, case: FraudCase) -> None:
        with self._session_factory.begin() as session:
            record = session.get(FraudCaseRecord, case.case_id)
            comments = to_domain_comments(record) if record is not None else []
            if record is None:
                session.add(to_case_record(case, comments))
                return

            updated = to_case_record(case, comments)
            _copy_case_record(record, updated)

    def list_cases(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        assigned_analyst_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudCase], int]:
        with self._session_factory() as session:
            query = self._base_query()
            if status is not None:
                query = query.where(FraudCaseRecord.status == status)
            if priority is not None:
                query = query.where(FraudCaseRecord.priority == priority)
            if assigned_analyst_id is not None:
                query = query.where(FraudCaseRecord.assigned_analyst_id == assigned_analyst_id)

            # Count via SQL instead of loading all rows into Python
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            offset = (page - 1) * page_size
            records = session.scalars(
                query.order_by(FraudCaseRecord.updated_at.desc())
                .offset(offset)
                .limit(page_size)
            ).all()

        return [to_domain_case(record) for record in records], total

    def add_comment(self, comment: CaseComment) -> None:
        with self._session_factory.begin() as session:
            record = session.get(FraudCaseRecord, comment.case_id)
            if record is None:
                raise LookupError(f"Case '{comment.case_id}' not found.")
            comments = list(record.comments)
            comments.append(comment.model_dump(mode="json"))
            record.comments = comments

    def list_comments(self, case_id: str) -> list[CaseComment]:
        with self._session_factory() as session:
            record = session.get(FraudCaseRecord, case_id)
            if record is None:
                return []
            return sorted(
                to_domain_comments(record),
                key=lambda comment: comment.created_at,
                reverse=True,
            )

    def count_by_status(self) -> dict[str, int]:
        with self._session_factory() as session:
            rows = session.execute(
                select(FraudCaseRecord.status, func.count())
                .group_by(FraudCaseRecord.status)
            ).all()
        return {status: count for status, count in rows}

    def count_critical(self) -> int:
        with self._session_factory() as session:
            return session.scalar(
                select(func.count())
                .select_from(FraudCaseRecord)
                .where(FraudCaseRecord.priority == CasePriority.CRITICAL)
                .where(FraudCaseRecord.status.not_in([CaseStatus.RESOLVED, CaseStatus.CLOSED]))
            ) or 0

    @staticmethod
    def _base_query() -> Select[tuple[FraudCaseRecord]]:
        return select(FraudCaseRecord)


class SqlAlchemyAlertRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_alert(self, alert: FraudAlert) -> None:
        with self._session_factory.begin() as session:
            session.add(to_alert_record(alert))

    def get_alert(self, alert_id: str) -> FraudAlert | None:
        with self._session_factory() as session:
            record = session.get(FraudAlertRecord, alert_id)
            return to_domain_alert(record) if record is not None else None

    def update_alert(self, alert: FraudAlert) -> None:
        with self._session_factory.begin() as session:
            record = session.get(FraudAlertRecord, alert.alert_id)
            if record is None:
                session.add(to_alert_record(alert))
                return
            updated = to_alert_record(alert)
            _copy_alert_record(record, updated)

    def list_alerts(
        self,
        *,
        status: AlertStatus | None = None,
        severity: RiskLevel | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudAlert], int]:
        with self._session_factory() as session:
            query = self._base_query()
            if status is not None:
                query = query.where(FraudAlertRecord.status == status)
            if severity is not None:
                query = query.where(FraudAlertRecord.severity == severity)

            # Count via SQL instead of loading all rows into Python
            count_query = select(func.count()).select_from(query.subquery())
            total = session.scalar(count_query) or 0

            offset = (page - 1) * page_size
            records = session.scalars(
                query.order_by(FraudAlertRecord.created_at.desc())
                .offset(offset)
                .limit(page_size)
            ).all()

        return [to_domain_alert(record) for record in records], total

    def list_alerts_for_source(
        self,
        *,
        source_type: WorkflowSourceType,
        source_id: str,
    ) -> list[FraudAlert]:
        with self._session_factory() as session:
            records = session.scalars(
                self._base_query()
                .where(FraudAlertRecord.source_type == source_type)
                .where(FraudAlertRecord.source_id == source_id)
                .order_by(FraudAlertRecord.created_at.desc())
            ).all()
        return [to_domain_alert(record) for record in records]

    def count_unacknowledged(self) -> int:
        with self._session_factory() as session:
            return session.scalar(
                select(func.count())
                .select_from(FraudAlertRecord)
                .where(FraudAlertRecord.status == AlertStatus.NEW)
            ) or 0

    def count_by_severity(self) -> dict[str, int]:
        with self._session_factory() as session:
            rows = session.execute(
                select(FraudAlertRecord.severity, func.count())
                .group_by(FraudAlertRecord.severity)
            ).all()
        return {severity: count for severity, count in rows}

    @staticmethod
    def _base_query() -> Select[tuple[FraudAlertRecord]]:
        return select(FraudAlertRecord)


class SqlAlchemyDatasetStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_dataset(self, dataset: Dataset) -> None:
        with self._session_factory.begin() as session:
            record = session.get(DatasetRecord, dataset.dataset_id)
            if record is None:
                session.add(to_dataset_record(dataset))
                return

            record.name = dataset.name
            record.uploaded_at = dataset.uploaded_at
            record.row_count = dataset.row_count
            record.status = dataset.status
            record.error_message = dataset.error_message

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        with self._session_factory() as session:
            record = session.get(DatasetRecord, dataset_id)
            return to_domain_dataset(record) if record is not None else None

    def list_datasets(self) -> list[Dataset]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DatasetRecord).order_by(DatasetRecord.uploaded_at.desc())
            ).all()
        return [to_domain_dataset(record) for record in records]

    def save_transactions(self, dataset_id: str, txns: list[UploadedTransaction]) -> None:
        with self._session_factory.begin() as session:
            record = session.get(DatasetRecord, dataset_id)
            if record is None:
                raise LookupError(f"Dataset '{dataset_id}' not found.")
            record.transactions = to_json_transactions(txns)

    def get_transactions(self, dataset_id: str) -> list[UploadedTransaction]:
        with self._session_factory() as session:
            record = session.get(DatasetRecord, dataset_id)
            if record is None:
                return []
            return to_domain_transactions(record.transactions)

    def save_result(self, result: AnalysisResult) -> None:
        with self._session_factory.begin() as session:
            record = session.get(DatasetRecord, result.dataset_id)
            if record is None:
                raise LookupError(f"Dataset '{result.dataset_id}' not found.")
            record.analysis = to_json_analysis(result)
            record.status = "completed"
            record.error_message = None

    def get_result(self, dataset_id: str) -> AnalysisResult | None:
        with self._session_factory() as session:
            record = session.get(DatasetRecord, dataset_id)
            if record is None:
                return None
            return to_domain_analysis(record.analysis)

    def list_results(self) -> list[AnalysisResult]:
        with self._session_factory() as session:
            records = session.scalars(
                select(DatasetRecord)
                .where(DatasetRecord.analysis.is_not(None))
                .order_by(DatasetRecord.uploaded_at.desc())
            ).all()
        results: list[AnalysisResult] = []
        for record in records:
            result = to_domain_analysis(record.analysis)
            if result is not None:
                results.append(result)
        return results

    def total_transactions(self) -> int:
        with self._session_factory() as session:
            return session.scalar(
                select(func.coalesce(func.sum(DatasetRecord.row_count), 0))
            ) or 0

    def total_anomalies(self) -> int:
        return sum(result.total_anomalies for result in self.list_results())


def _copy_case_record(target: FraudCaseRecord, source: FraudCaseRecord) -> None:
    target.source_type = source.source_type
    target.source_id = source.source_id
    target.scenario_id = source.scenario_id
    target.title = source.title
    target.status = source.status
    target.priority = source.priority
    target.assigned_analyst_id = source.assigned_analyst_id
    target.assigned_analyst_name = source.assigned_analyst_name
    target.risk_score = source.risk_score
    target.risk_level = source.risk_level
    target.summary = source.summary
    target.disposition = source.disposition
    target.resolution_notes = source.resolution_notes
    target.created_at = source.created_at
    target.updated_at = source.updated_at
    target.resolved_at = source.resolved_at
    target.sla_deadline = source.sla_deadline
    target.comment_count = source.comment_count
    target.alert_count = source.alert_count


def _copy_alert_record(target: FraudAlertRecord, source: FraudAlertRecord) -> None:
    target.source_type = source.source_type
    target.source_id = source.source_id
    target.scenario_id = source.scenario_id
    target.rule_code = source.rule_code
    target.title = source.title
    target.severity = source.severity
    target.status = source.status
    target.narrative = source.narrative
    target.assigned_analyst_id = source.assigned_analyst_id
    target.assigned_analyst_name = source.assigned_analyst_name
    target.linked_case_id = source.linked_case_id
    target.created_at = source.created_at
    target.acknowledged_at = source.acknowledged_at
    target.resolved_at = source.resolved_at
