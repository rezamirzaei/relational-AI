"""Tests for the graph analysis engine."""

from __future__ import annotations

from datetime import datetime

from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    FraudScenario,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)
from relational_fraud_intelligence.infrastructure.graph.analyzer import analyze_scenario_graph


def _build_scenario(
    customers: list[CustomerProfile] | None = None,
    devices: list[DeviceProfile] | None = None,
    transactions: list[TransactionRecord] | None = None,
) -> FraudScenario:
    return FraudScenario(
        scenario_id="test-graph",
        title="Graph test scenario",
        industry="Test",
        summary="Test",
        hypothesis="Test",
        tags=[ScenarioTag.FRAUD],
        customers=customers or [],
        accounts=[
            AccountProfile(
                account_id="acct_1",
                customer_id="cust_1",
                opened_at=datetime(2026, 1, 1),
                current_balance=1000.0,
                average_monthly_inflow=2000.0,
                chargeback_count=0,
                manual_review_count=0,
            ),
        ],
        devices=devices or [],
        merchants=[
            MerchantProfile(
                merchant_id="merch_1",
                display_name="Test Merchant",
                country_code="US",
                category="retail",
                description="A test merchant.",
            ),
        ],
        transactions=transactions or [],
        investigator_notes=[],
    )


def test_graph_analysis_with_shared_device_scenario() -> None:
    scenario = _build_scenario(
        customers=[
            CustomerProfile(
                customer_id="cust_1",
                full_name="Alice",
                country_code="US",
                segment="consumer",
                declared_income_band="$50k-$70k",
                linked_account_ids=["acct_1"],
                linked_device_ids=["dev_1"],
            ),
            CustomerProfile(
                customer_id="cust_2",
                full_name="Bob",
                country_code="US",
                segment="consumer",
                declared_income_band="$40k-$60k",
                linked_account_ids=[],
                linked_device_ids=["dev_1"],
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_1",
                fingerprint="fp-1",
                ip_country_code="US",
                linked_customer_ids=["cust_1", "cust_2"],
                trust_score=0.2,
            ),
        ],
        transactions=[
            TransactionRecord(
                transaction_id="txn_1",
                customer_id="cust_1",
                account_id="acct_1",
                device_id="dev_1",
                merchant_id="merch_1",
                occurred_at=datetime(2026, 3, 1, 10, 0),
                amount=1200.0,
                currency="USD",
                channel=TransactionChannel.CARD_NOT_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
        ],
    )

    result = analyze_scenario_graph(scenario)

    assert result.connected_components >= 1
    assert result.density > 0
    assert result.risk_amplification_factor >= 1.0
    assert len(result.hub_entities) >= 0


def test_graph_analysis_with_empty_scenario() -> None:
    scenario = _build_scenario(customers=[], devices=[], transactions=[])

    result = analyze_scenario_graph(scenario)

    assert result.connected_components == 0
    assert result.density == 0.0
    assert result.risk_amplification_factor == 1.0
