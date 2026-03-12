from __future__ import annotations

from decimal import Decimal

from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    FraudScenario,
    InvestigatorNote,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)
from relational_fraud_intelligence.infrastructure.persistence.models import (
    AccountRecord,
    CustomerRecord,
    DeviceRecord,
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
    for account in scenario.accounts:
        customer_record = customer_records[account.customer_id]
        account_records.append(
            AccountRecord(
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
        )
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
