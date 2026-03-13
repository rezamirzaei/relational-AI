from __future__ import annotations

from decimal import Decimal

from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    AnalysisResult,
    CaseComment,
    CaseEvidenceSnapshot,
    CustomerProfile,
    Dataset,
    DeviceProfile,
    FraudAlert,
    FraudCase,
    FraudScenario,
    InvestigatorNote,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
    UploadedTransaction,
)
from relational_fraud_intelligence.infrastructure.persistence.models import (
    AccountRecord,
    CustomerRecord,
    DatasetRecord,
    DeviceRecord,
    FraudAlertRecord,
    FraudCaseRecord,
    InvestigatorNoteRecord,
    MerchantRecord,
    ScenarioRecord,
    TransactionRecordOrm,
)


def to_scenario_record(scenario: FraudScenario) -> ScenarioRecord:
    customer_records = {
        customer.customer_id: CustomerRecord(
            customer_id=customer.customer_id,
            scenario_id=scenario.scenario_id,
            full_name=customer.full_name,
            country_code=customer.country_code,
            segment=customer.segment,
            declared_income_band=customer.declared_income_band,
            watchlist_tags=list(customer.watchlist_tags),
        )
        for customer in scenario.customers
    }
    device_records = {
        device.device_id: DeviceRecord(
            device_id=device.device_id,
            scenario_id=scenario.scenario_id,
            fingerprint=device.fingerprint,
            ip_country_code=device.ip_country_code,
            trust_score=device.trust_score,
        )
        for device in scenario.devices
    }
    merchant_records = {
        merchant.merchant_id: MerchantRecord(
            merchant_id=merchant.merchant_id,
            scenario_id=scenario.scenario_id,
            display_name=merchant.display_name,
            country_code=merchant.country_code,
            category=merchant.category,
            description=merchant.description,
        )
        for merchant in scenario.merchants
    }

    scenario_record = ScenarioRecord(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        industry=scenario.industry,
        summary=scenario.summary,
        hypothesis=scenario.hypothesis,
        tags=[tag.value for tag in scenario.tags],
        customers=list(customer_records.values()),
        devices=list(device_records.values()),
        merchants=list(merchant_records.values()),
    )

    account_records: list[AccountRecord] = []
    account_records_by_id: dict[str, AccountRecord] = {}
    for account in scenario.accounts:
        customer_record = customer_records[account.customer_id]
        account_record = AccountRecord(
            account_id=account.account_id,
            scenario_id=scenario.scenario_id,
            customer_id=account.customer_id,
            opened_at=account.opened_at,
            current_balance=account.current_balance,
            average_monthly_inflow=account.average_monthly_inflow,
            chargeback_count=account.chargeback_count,
            manual_review_count=account.manual_review_count,
            customer=customer_record,
        )
        account_records.append(account_record)
        account_records_by_id[account.account_id] = account_record
    scenario_record.accounts = account_records

    transaction_records: list[TransactionRecordOrm] = []
    for transaction in scenario.transactions:
        transaction_records.append(
            TransactionRecordOrm(
                transaction_id=transaction.transaction_id,
                scenario_id=scenario.scenario_id,
                customer_id=transaction.customer_id,
                account_id=transaction.account_id,
                device_id=transaction.device_id,
                merchant_id=transaction.merchant_id,
                occurred_at=transaction.occurred_at,
                amount=transaction.amount,
                currency=transaction.currency,
                channel=transaction.channel.value,
                status=transaction.status.value,
                customer=customer_records[transaction.customer_id],
                account=account_records_by_id[transaction.account_id],
                device=device_records[transaction.device_id],
                merchant=merchant_records[transaction.merchant_id],
            )
        )
    scenario_record.transactions = transaction_records

    note_records: list[InvestigatorNoteRecord] = []
    for note in scenario.investigator_notes:
        note_records.append(
            InvestigatorNoteRecord(
                note_id=note.note_id,
                scenario_id=scenario.scenario_id,
                subject_customer_id=note.subject_customer_id,
                author=note.author,
                created_at=note.created_at,
                body=note.body,
                subject_customer=customer_records[note.subject_customer_id],
            )
        )
    scenario_record.investigator_notes = note_records

    for device in scenario.devices:
        device_record = device_records[device.device_id]
        device_record.linked_customers = [
            customer_records[customer_id] for customer_id in sorted(device.linked_customer_ids)
        ]

    return scenario_record


def to_domain_scenario(scenario: ScenarioRecord) -> FraudScenario:
    customers = sorted(scenario.customers, key=lambda item: item.customer_id)
    accounts_by_customer = {
        customer.customer_id: sorted(customer.accounts, key=lambda item: item.account_id)
        for customer in customers
    }
    linked_devices_by_customer = {
        customer.customer_id: sorted(customer.linked_devices, key=lambda item: item.device_id)
        for customer in customers
    }

    return FraudScenario(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        industry=scenario.industry,
        summary=scenario.summary,
        hypothesis=scenario.hypothesis,
        tags=[ScenarioTag(tag) for tag in scenario.tags],
        customers=[
            CustomerProfile(
                customer_id=customer.customer_id,
                full_name=customer.full_name,
                country_code=customer.country_code,
                segment=customer.segment,
                declared_income_band=customer.declared_income_band,
                linked_account_ids=[
                    account.account_id for account in accounts_by_customer[customer.customer_id]
                ],
                linked_device_ids=[
                    device.device_id for device in linked_devices_by_customer[customer.customer_id]
                ],
                watchlist_tags=list(customer.watchlist_tags),
            )
            for customer in customers
        ],
        accounts=[
            AccountProfile(
                account_id=account.account_id,
                customer_id=account.customer_id,
                opened_at=account.opened_at,
                current_balance=_to_float(account.current_balance),
                average_monthly_inflow=_to_float(account.average_monthly_inflow),
                chargeback_count=account.chargeback_count,
                manual_review_count=account.manual_review_count,
            )
            for account in sorted(scenario.accounts, key=lambda item: item.account_id)
        ],
        devices=[
            DeviceProfile(
                device_id=device.device_id,
                fingerprint=device.fingerprint,
                ip_country_code=device.ip_country_code,
                linked_customer_ids=[
                    customer.customer_id
                    for customer in sorted(
                        device.linked_customers, key=lambda item: item.customer_id
                    )
                ],
                trust_score=device.trust_score,
            )
            for device in sorted(scenario.devices, key=lambda item: item.device_id)
        ],
        merchants=[
            MerchantProfile(
                merchant_id=merchant.merchant_id,
                display_name=merchant.display_name,
                country_code=merchant.country_code,
                category=merchant.category,
                description=merchant.description,
            )
            for merchant in sorted(scenario.merchants, key=lambda item: item.merchant_id)
        ],
        transactions=[
            TransactionRecord(
                transaction_id=transaction.transaction_id,
                customer_id=transaction.customer_id,
                account_id=transaction.account_id,
                device_id=transaction.device_id,
                merchant_id=transaction.merchant_id,
                occurred_at=transaction.occurred_at,
                amount=_to_float(transaction.amount),
                currency=transaction.currency,
                channel=TransactionChannel(transaction.channel),
                status=TransactionStatus(transaction.status),
            )
            for transaction in sorted(scenario.transactions, key=lambda item: item.occurred_at)
        ],
        investigator_notes=[
            InvestigatorNote(
                note_id=note.note_id,
                subject_customer_id=note.subject_customer_id,
                author=note.author,
                created_at=note.created_at,
                body=note.body,
            )
            for note in sorted(scenario.investigator_notes, key=lambda item: item.created_at)
        ],
    )


def _to_float(value: Decimal | float) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return value


def to_case_record(case: FraudCase, comments: list[CaseComment]) -> FraudCaseRecord:
    return FraudCaseRecord(
        case_id=case.case_id,
        source_type=case.source_type,
        source_id=case.source_id,
        scenario_id=case.scenario_id,
        title=case.title,
        status=case.status,
        priority=case.priority,
        assigned_analyst_id=case.assigned_analyst_id,
        assigned_analyst_name=case.assigned_analyst_name,
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        summary=case.summary,
        disposition=case.disposition,
        resolution_notes=case.resolution_notes,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        sla_deadline=case.sla_deadline,
        comment_count=case.comment_count,
        alert_count=case.alert_count,
        comments=[comment.model_dump(mode="json") for comment in comments],
        evidence_snapshot=to_json_case_snapshot(case.evidence_snapshot),
    )


def to_domain_case(record: FraudCaseRecord) -> FraudCase:
    return FraudCase.model_validate(
        {
            "case_id": record.case_id,
            "source_type": record.source_type,
            "source_id": record.source_id,
            "scenario_id": record.scenario_id,
            "title": record.title,
            "status": record.status,
            "priority": record.priority,
            "assigned_analyst_id": record.assigned_analyst_id,
            "assigned_analyst_name": record.assigned_analyst_name,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "summary": record.summary,
            "disposition": record.disposition,
            "resolution_notes": record.resolution_notes,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "resolved_at": record.resolved_at,
            "sla_deadline": record.sla_deadline,
            "comment_count": record.comment_count,
            "alert_count": record.alert_count,
            "evidence_snapshot": to_domain_case_snapshot(record.evidence_snapshot),
        }
    )


def to_domain_comments(record: FraudCaseRecord) -> list[CaseComment]:
    return [CaseComment.model_validate(comment) for comment in record.comments]


def to_alert_record(alert: FraudAlert) -> FraudAlertRecord:
    return FraudAlertRecord(
        alert_id=alert.alert_id,
        source_type=alert.source_type,
        source_id=alert.source_id,
        scenario_id=alert.scenario_id,
        rule_code=alert.rule_code,
        title=alert.title,
        severity=alert.severity,
        status=alert.status,
        narrative=alert.narrative,
        assigned_analyst_id=alert.assigned_analyst_id,
        assigned_analyst_name=alert.assigned_analyst_name,
        linked_case_id=alert.linked_case_id,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
    )


def to_domain_alert(record: FraudAlertRecord) -> FraudAlert:
    return FraudAlert.model_validate(
        {
            "alert_id": record.alert_id,
            "source_type": record.source_type,
            "source_id": record.source_id,
            "scenario_id": record.scenario_id,
            "rule_code": record.rule_code,
            "title": record.title,
            "severity": record.severity,
            "status": record.status,
            "narrative": record.narrative,
            "assigned_analyst_id": record.assigned_analyst_id,
            "assigned_analyst_name": record.assigned_analyst_name,
            "linked_case_id": record.linked_case_id,
            "created_at": record.created_at,
            "acknowledged_at": record.acknowledged_at,
            "resolved_at": record.resolved_at,
        }
    )


def to_dataset_record(dataset: Dataset) -> DatasetRecord:
    return DatasetRecord(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        uploaded_at=dataset.uploaded_at,
        row_count=dataset.row_count,
        status=dataset.status,
        error_message=dataset.error_message,
        transactions=[],
        analysis=None,
    )


def to_domain_dataset(record: DatasetRecord) -> Dataset:
    return Dataset.model_validate(
        {
            "dataset_id": record.dataset_id,
            "name": record.name,
            "uploaded_at": record.uploaded_at,
            "row_count": record.row_count,
            "status": record.status,
            "error_message": record.error_message,
        }
    )


def to_json_transactions(transactions: list[UploadedTransaction]) -> list[dict[str, object]]:
    return [transaction.model_dump(mode="json") for transaction in transactions]


def to_domain_transactions(payload: list[dict[str, object]]) -> list[UploadedTransaction]:
    return [UploadedTransaction.model_validate(transaction) for transaction in payload]


def to_json_analysis(result: AnalysisResult) -> dict[str, object]:
    return result.model_dump(mode="json")


def to_domain_analysis(payload: dict[str, object] | None) -> AnalysisResult | None:
    if payload is None:
        return None
    return AnalysisResult.model_validate(payload)


def to_json_case_snapshot(snapshot: CaseEvidenceSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return snapshot.model_dump(mode="json")


def to_domain_case_snapshot(payload: dict[str, object] | None) -> CaseEvidenceSnapshot | None:
    if payload is None:
        return None
    return CaseEvidenceSnapshot.model_validate(payload)
