"""Tests for the graph analysis engine."""

from __future__ import annotations

from datetime import datetime

import pytest

import relational_fraud_intelligence.infrastructure.graph.analyzer as analyzer
from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    FraudScenario,
    GraphAnalysisResult,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)
from relational_fraud_intelligence.infrastructure.graph.analyzer import (
    _analyze_basic,
    _analyze_with_networkx,
    analyze_scenario_graph,
)


def _build_scenario(
    customers: list[CustomerProfile] | None = None,
    accounts: list[AccountProfile] | None = None,
    devices: list[DeviceProfile] | None = None,
    merchants: list[MerchantProfile] | None = None,
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
        accounts=accounts
        or [
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
        merchants=merchants
        or [
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


def test_basic_graph_analysis_with_empty_scenario() -> None:
    scenario = _build_scenario(
        customers=[],
        accounts=[],
        devices=[],
        merchants=[],
        transactions=[],
    )

    result = _analyze_basic(scenario)

    assert result.connected_components == 0
    assert result.density == 0.0
    assert result.risk_amplification_factor == 1.0


def test_graph_analysis_falls_back_to_basic_when_networkx_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = _build_scenario()
    sentinel = GraphAnalysisResult(
        connected_components=99,
        density=0.5,
        risk_amplification_factor=1.5,
    )

    def fake_networkx(_scenario: FraudScenario) -> GraphAnalysisResult:
        raise ImportError("networkx not installed")

    monkeypatch.setattr(analyzer, "_analyze_with_networkx", fake_networkx)
    monkeypatch.setattr(analyzer, "_analyze_basic", lambda _scenario: sentinel)

    assert analyze_scenario_graph(scenario) == sentinel


def test_basic_graph_analysis_detects_disconnected_components() -> None:
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
                linked_account_ids=["acct_2"],
                linked_device_ids=["dev_2"],
            ),
        ],
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
            AccountProfile(
                account_id="acct_2",
                customer_id="cust_2",
                opened_at=datetime(2026, 1, 2),
                current_balance=500.0,
                average_monthly_inflow=1500.0,
                chargeback_count=0,
                manual_review_count=0,
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_1",
                fingerprint="fp-1",
                ip_country_code="US",
                linked_customer_ids=["cust_1"],
                trust_score=0.4,
            ),
            DeviceProfile(
                device_id="dev_2",
                fingerprint="fp-2",
                ip_country_code="US",
                linked_customer_ids=["cust_2"],
                trust_score=0.6,
            ),
        ],
        merchants=[
            MerchantProfile(
                merchant_id="merch_1",
                display_name="Merchant One",
                country_code="US",
                category="retail",
                description="First merchant.",
            ),
            MerchantProfile(
                merchant_id="merch_2",
                display_name="Merchant Two",
                country_code="US",
                category="travel",
                description="Second merchant.",
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
            TransactionRecord(
                transaction_id="txn_2",
                customer_id="cust_2",
                account_id="acct_2",
                device_id="dev_2",
                merchant_id="merch_2",
                occurred_at=datetime(2026, 3, 1, 11, 0),
                amount=900.0,
                currency="USD",
                channel=TransactionChannel.CARD_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
        ],
    )

    result = _analyze_basic(scenario)

    assert result.connected_components == 2
    assert result.community_count == 2
    assert result.highest_degree_entity is not None
    assert result.highest_degree_score >= 2
    assert result.risk_amplification_factor > 1.0


def test_networkx_graph_analysis_handles_missing_path_between_customers() -> None:
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
                linked_account_ids=["acct_2"],
                linked_device_ids=["dev_2"],
            ),
        ],
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
            AccountProfile(
                account_id="acct_2",
                customer_id="cust_2",
                opened_at=datetime(2026, 1, 2),
                current_balance=500.0,
                average_monthly_inflow=1500.0,
                chargeback_count=0,
                manual_review_count=0,
            ),
        ],
        devices=[
            DeviceProfile(
                device_id="dev_1",
                fingerprint="fp-1",
                ip_country_code="US",
                linked_customer_ids=["cust_1"],
                trust_score=0.4,
            ),
            DeviceProfile(
                device_id="dev_2",
                fingerprint="fp-2",
                ip_country_code="US",
                linked_customer_ids=["cust_2"],
                trust_score=0.6,
            ),
        ],
        merchants=[
            MerchantProfile(
                merchant_id="merch_1",
                display_name="Merchant One",
                country_code="US",
                category="retail",
                description="First merchant.",
            ),
            MerchantProfile(
                merchant_id="merch_2",
                display_name="Merchant Two",
                country_code="US",
                category="travel",
                description="Second merchant.",
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
            TransactionRecord(
                transaction_id="txn_2",
                customer_id="cust_2",
                account_id="acct_2",
                device_id="dev_2",
                merchant_id="merch_2",
                occurred_at=datetime(2026, 3, 1, 11, 0),
                amount=900.0,
                currency="USD",
                channel=TransactionChannel.CARD_PRESENT,
                status=TransactionStatus.APPROVED,
            ),
        ],
    )

    result = _analyze_with_networkx(scenario)

    assert result.connected_components == 2
    assert result.shortest_path_length is None


def test_networkx_graph_analysis_falls_back_when_advanced_algorithms_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import networkx as nx

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
            )
        ],
        devices=[
            DeviceProfile(
                device_id="dev_1",
                fingerprint="fp-1",
                ip_country_code="US",
                linked_customer_ids=["cust_1"],
                trust_score=0.4,
            )
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
            )
        ],
    )

    def fail_communities(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("community detection failed")

    def fail_betweenness(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("betweenness failed")

    def fail_cycles(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("cycle detection failed")

    monkeypatch.setattr(nx.community, "greedy_modularity_communities", fail_communities)
    monkeypatch.setattr(nx, "betweenness_centrality", fail_betweenness)
    monkeypatch.setattr(nx, "simple_cycles", fail_cycles)

    result = _analyze_with_networkx(scenario)

    assert result.community_count == result.connected_components
    assert result.hub_entities
    assert result.risk_amplification_factor >= 1.0
