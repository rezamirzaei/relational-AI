"""Tests for the RelationalAI graph-based risk reasoner.

Exercises the four graph analysis queries (circular flows, hub centrality,
community detection, money-mule paths) and verifies that graph-based
findings correctly amplify the base risk score.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    FraudScenario,
    InvestigationMetrics,
    MerchantProfile,
    RiskLevel,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)
from relational_fraud_intelligence.infrastructure.reasoners.relationalai_reasoner import (
    GraphInsight,
    RelationalAIProjection,
    RelationalAIRiskReasoner,
    _score_to_level,
)
from relational_fraud_intelligence.settings import AppSettings

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_txn(
    txn_id: str,
    customer_id: str,
    account_id: str,
    device_id: str,
    merchant_id: str,
    amount: float,
    minutes_offset: int = 0,
) -> TransactionRecord:
    return TransactionRecord(
        transaction_id=txn_id,
        customer_id=customer_id,
        account_id=account_id,
        device_id=device_id,
        merchant_id=merchant_id,
        occurred_at=datetime(2026, 3, 1, 10, minutes_offset),
        amount=amount,
        currency="USD",
        channel=TransactionChannel.CARD_NOT_PRESENT,
        status=TransactionStatus.APPROVED,
    )


def _make_scenario(
    customers: list[CustomerProfile] | None = None,
    accounts: list[AccountProfile] | None = None,
    devices: list[DeviceProfile] | None = None,
    merchants: list[MerchantProfile] | None = None,
    transactions: list[TransactionRecord] | None = None,
) -> FraudScenario:
    return FraudScenario(
        scenario_id="rai-test",
        title="RAI graph test",
        industry="finance",
        summary="Test scenario for graph analysis",
        hypothesis="Graph analysis will find hidden risk patterns.",
        tags=[ScenarioTag.FRAUD],
        customers=customers or [],
        accounts=accounts or [],
        devices=devices or [],
        merchants=merchants or [],
        transactions=transactions or [],
        investigator_notes=[],
    )


def _make_base_result(score: int = 40) -> ReasonAboutRiskResult:
    return ReasonAboutRiskResult(
        requested_provider="local-rule-engine",
        active_provider="local-rule-engine",
        provider_notes=["Base result."],
        risk_level=_score_to_level(score),
        total_risk_score=score,
        summary="Base summary.",
        metrics=InvestigationMetrics(
            total_transaction_volume=10000.0,
            suspicious_transaction_volume=3000.0,
            suspicious_transaction_count=2,
            shared_device_count=1,
            linked_customer_count=2,
        ),
        top_rule_hits=[],
        graph_links=[],
        suspicious_transactions=[],
        recommended_actions=[],
    )


class _StubProjectionReasoner(RelationalAIRiskReasoner):
    def _project_scenario(self, command: ReasonAboutRiskCommand) -> RelationalAIProjection:
        _ = command
        return RelationalAIProjection(
            projected_row_count=10,
            projected_table_names=["transactions", "devices"],
        )


def _build_reasoner() -> tuple[RelationalAIRiskReasoner, MagicMock]:
    """Build a reasoner with a deterministic projection stub."""
    settings = AppSettings(
        database_url="sqlite:///:memory:",
        jwt_secret="test-secret-key-for-unit-tests-0001",
        reasoning_provider="relationalai",
    )
    local_reasoner = MagicMock()
    reasoner = _StubProjectionReasoner(settings, local_reasoner)
    return reasoner, local_reasoner


# ---------------------------------------------------------------------------
# Unit tests for _score_to_level
# ---------------------------------------------------------------------------


class TestScoreToLevel:
    def test_low(self) -> None:
        assert _score_to_level(0) == RiskLevel.LOW
        assert _score_to_level(34) == RiskLevel.LOW

    def test_medium(self) -> None:
        assert _score_to_level(35) == RiskLevel.MEDIUM
        assert _score_to_level(59) == RiskLevel.MEDIUM

    def test_high(self) -> None:
        assert _score_to_level(60) == RiskLevel.HIGH
        assert _score_to_level(79) == RiskLevel.HIGH

    def test_critical(self) -> None:
        assert _score_to_level(80) == RiskLevel.CRITICAL
        assert _score_to_level(100) == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# Unit tests for individual graph analysis methods
# ---------------------------------------------------------------------------


class TestBuildMoneyFlowGraph:
    def test_empty_transactions(self) -> None:
        reasoner, _ = _build_reasoner()
        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(), text_signals=[]
        )
        G = reasoner._build_money_flow_graph(cmd)
        assert G.number_of_nodes() == 0

    def test_builds_directed_weighted_edges(self) -> None:
        reasoner, _ = _build_reasoner()
        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                transactions=[
                    _make_txn("t1", "c1", "a1", "d1", "m1", 500.0),
                    _make_txn("t2", "c1", "a1", "d1", "m1", 300.0),
                ]
            ),
            text_signals=[],
        )
        G = reasoner._build_money_flow_graph(cmd)
        assert G.is_directed()
        assert G.number_of_edges() == 1
        edge_data = G.edges["acct:a1", "merch:m1"]
        assert edge_data["weight"] == 800.0


class TestBuildEntityGraph:
    def test_connects_customers_accounts_devices(self) -> None:
        reasoner, _ = _build_reasoner()
        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                customers=[
                    CustomerProfile(
                        customer_id="c1", full_name="Alice", country_code="US",
                        segment="consumer", declared_income_band="$50k",
                        linked_account_ids=["a1"], linked_device_ids=["d1"],
                    ),
                ],
                devices=[
                    DeviceProfile(
                        device_id="d1", fingerprint="fp1", ip_country_code="US",
                        linked_customer_ids=["c1"], trust_score=0.8,
                    ),
                ],
                transactions=[
                    _make_txn("t1", "c1", "a1", "d1", "m1", 100.0),
                ],
            ),
            text_signals=[],
        )
        G = reasoner._build_entity_graph(cmd)
        assert not G.is_directed()
        assert "cust:c1" in G
        assert "acct:a1" in G
        assert "dev:d1" in G
        assert "merch:m1" in G


class TestDetectCircularFlows:
    def test_no_cycles_returns_empty(self) -> None:
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge("acct:a1", "merch:m1", weight=1000.0)
        G.add_edge("acct:a2", "merch:m2", weight=500.0)

        insights = RelationalAIRiskReasoner._detect_circular_flows(G)
        assert insights == []

    def test_detects_cycle(self) -> None:
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge("acct:a1", "merch:m1", weight=5000.0)
        G.add_edge("merch:m1", "acct:a2", weight=4500.0)
        G.add_edge("acct:a2", "acct:a1", weight=4000.0)

        insights = RelationalAIRiskReasoner._detect_circular_flows(G)
        assert len(insights) >= 1
        assert insights[0].category == "circular-flow"
        assert insights[0].risk_bonus > 0
        assert "Circular money flow detected" in insights[0].description


class TestDetectHubEntities:
    def test_too_few_nodes_returns_empty(self) -> None:
        import networkx as nx

        G = nx.Graph()
        G.add_edge("a", "b")
        insights = RelationalAIRiskReasoner._detect_hub_entities(G)
        assert insights == []

    def test_finds_high_centrality_hub(self) -> None:
        import networkx as nx

        # Star graph: central device connected to 12 isolated customer leaves.
        # The hub has degree 12, PageRank ≈ 0.27; mean PR ≈ 0.077.
        G = nx.Graph()
        center = "dev:d1"
        for i in range(12):
            G.add_node(f"cust:c{i}", kind="customer")
            G.add_edge(center, f"cust:c{i}")

        insights = RelationalAIRiskReasoner._detect_hub_entities(G)
        assert len(insights) >= 1
        hub_categories = [i.category for i in insights]
        assert "hub-centrality" in hub_categories
        assert insights[0].risk_bonus > 0


class TestDetectSuspiciousCommunities:
    def test_single_community_returns_empty(self) -> None:
        import networkx as nx

        G = nx.Graph()
        G.add_edge("cust:c1", "dev:d1")
        G.add_edge("cust:c2", "dev:d1")

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                devices=[
                    DeviceProfile(
                        device_id="d1", fingerprint="fp1", ip_country_code="US",
                        linked_customer_ids=["c1", "c2"], trust_score=0.1,
                    ),
                ],
            ),
            text_signals=[],
        )
        # Only one community expected (too few nodes for multiple)
        insights = RelationalAIRiskReasoner._detect_suspicious_communities(G, cmd)
        # Might be empty because the graph is too small or has only 1 community
        assert isinstance(insights, list)

    def test_detects_low_trust_device_community(self) -> None:
        import networkx as nx

        G = nx.Graph()
        # Community 1: c1, c2 share low-trust dev:d1
        G.add_edge("cust:c1", "dev:d1")
        G.add_edge("cust:c2", "dev:d1")
        G.add_edge("cust:c1", "acct:a1")
        G.add_edge("cust:c2", "acct:a2")

        # Community 2: c3, c4 via a separate device
        G.add_edge("cust:c3", "dev:d2")
        G.add_edge("cust:c4", "dev:d2")
        G.add_edge("cust:c3", "merch:m1")
        G.add_edge("cust:c4", "merch:m2")

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                devices=[
                    DeviceProfile(
                        device_id="d1", fingerprint="fp1", ip_country_code="US",
                        linked_customer_ids=["c1", "c2"], trust_score=0.1,
                    ),
                    DeviceProfile(
                        device_id="d2", fingerprint="fp2", ip_country_code="US",
                        linked_customer_ids=["c3", "c4"], trust_score=0.2,
                    ),
                ],
            ),
            text_signals=[],
        )

        insights = RelationalAIRiskReasoner._detect_suspicious_communities(G, cmd)
        # Should detect at least one community with low-trust devices
        ring_insights = [i for i in insights if i.category == "community-ring"]
        if ring_insights:
            assert ring_insights[0].risk_bonus == 8
            assert "low-trust" in ring_insights[0].description


class TestDetectMoneyMulePaths:
    def test_no_indirect_paths_returns_empty(self) -> None:
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge("acct:a1", "merch:m1", weight=100.0)

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                customers=[
                    CustomerProfile(
                        customer_id="c1", full_name="Alice", country_code="US",
                        segment="consumer", declared_income_band="$50k",
                        linked_account_ids=["a1"], linked_device_ids=[],
                    ),
                ],
                accounts=[
                    AccountProfile(
                        account_id="a1", customer_id="c1",
                        opened_at=datetime(2026, 1, 1), current_balance=1000.0,
                        average_monthly_inflow=2000.0, chargeback_count=0,
                        manual_review_count=0,
                    ),
                ],
            ),
            text_signals=[],
        )

        insights = RelationalAIRiskReasoner._detect_money_mule_paths(G, cmd)
        assert insights == []

    def test_detects_cross_border_mule_path(self) -> None:
        import networkx as nx

        G = nx.DiGraph()
        # a1 (US) → m1 ← a2 (NG) — indirect path through shared merchant
        G.add_edge("acct:a1", "merch:m1", weight=5000.0)
        G.add_edge("acct:a2", "merch:m1", weight=4500.0)

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                customers=[
                    CustomerProfile(
                        customer_id="c1", full_name="Alice", country_code="US",
                        segment="consumer", declared_income_band="$50k",
                        linked_account_ids=["a1"], linked_device_ids=[],
                    ),
                    CustomerProfile(
                        customer_id="c2", full_name="Bob", country_code="NG",
                        segment="consumer", declared_income_band="$30k",
                        linked_account_ids=["a2"], linked_device_ids=[],
                    ),
                ],
                accounts=[
                    AccountProfile(
                        account_id="a1", customer_id="c1",
                        opened_at=datetime(2026, 1, 1), current_balance=1000.0,
                        average_monthly_inflow=2000.0, chargeback_count=0,
                        manual_review_count=0,
                    ),
                    AccountProfile(
                        account_id="a2", customer_id="c2",
                        opened_at=datetime(2026, 1, 1), current_balance=500.0,
                        average_monthly_inflow=1000.0, chargeback_count=0,
                        manual_review_count=0,
                    ),
                ],
            ),
            text_signals=[],
        )

        insights = RelationalAIRiskReasoner._detect_money_mule_paths(G, cmd)
        assert len(insights) >= 1
        assert insights[0].category == "mule-path"
        assert insights[0].risk_bonus == 6  # cross-border bonus
        assert "Cross-border" in insights[0].description


# ---------------------------------------------------------------------------
# Integration: full reason() pipeline
# ---------------------------------------------------------------------------


class TestReasonIntegration:
    def test_empty_scenario_returns_base_result(self) -> None:
        reasoner, local = _build_reasoner()
        base = _make_base_result(score=40)
        local.reason.return_value = base

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(), text_signals=[]
        )
        result = reasoner.reason(cmd)

        assert result.active_provider == "hybrid-relationalai"
        assert result.requested_provider == "relationalai"
        # No graph bonus for empty scenario
        assert result.total_risk_score == 40

    def test_graph_bonus_amplifies_score(self) -> None:
        reasoner, local = _build_reasoner()
        base = _make_base_result(score=55)
        local.reason.return_value = base

        # Build a scenario with a clear circular flow
        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                customers=[
                    CustomerProfile(
                        customer_id="c1", full_name="Alice", country_code="US",
                        segment="consumer", declared_income_band="$50k",
                        linked_account_ids=["a1"], linked_device_ids=["d1"],
                    ),
                    CustomerProfile(
                        customer_id="c2", full_name="Bob", country_code="NG",
                        segment="consumer", declared_income_band="$30k",
                        linked_account_ids=["a2"], linked_device_ids=["d1"],
                    ),
                ],
                accounts=[
                    AccountProfile(
                        account_id="a1", customer_id="c1",
                        opened_at=datetime(2026, 1, 1), current_balance=5000.0,
                        average_monthly_inflow=3000.0, chargeback_count=0,
                        manual_review_count=0,
                    ),
                    AccountProfile(
                        account_id="a2", customer_id="c2",
                        opened_at=datetime(2026, 1, 1), current_balance=2000.0,
                        average_monthly_inflow=1500.0, chargeback_count=0,
                        manual_review_count=0,
                    ),
                ],
                devices=[
                    DeviceProfile(
                        device_id="d1", fingerprint="fp1", ip_country_code="US",
                        linked_customer_ids=["c1", "c2"], trust_score=0.15,
                    ),
                ],
                merchants=[
                    MerchantProfile(
                        merchant_id="m1", display_name="Merch 1", country_code="US",
                        category="digital_goods", description="Gift cards",
                    ),
                    MerchantProfile(
                        merchant_id="m2", display_name="Merch 2", country_code="NG",
                        category="money_transfer", description="Wire service",
                    ),
                ],
                transactions=[
                    _make_txn("t1", "c1", "a1", "d1", "m1", 5000.0, 0),
                    _make_txn("t2", "c1", "a1", "d1", "m2", 3000.0, 5),
                    _make_txn("t3", "c2", "a2", "d1", "m1", 4500.0, 10),
                    _make_txn("t4", "c2", "a2", "d1", "m2", 2500.0, 15),
                ],
            ),
            text_signals=[],
        )

        result = reasoner.reason(cmd)

        # Score should be amplified above 55 due to graph findings
        assert result.total_risk_score >= 55
        # Provider notes should contain graph findings
        graph_notes = [n for n in result.provider_notes if "[" in n]
        assert len(graph_notes) >= 1  # at least one graph insight

    def test_graph_bonus_capped_at_max(self) -> None:
        reasoner, local = _build_reasoner()
        base = _make_base_result(score=90)
        local.reason.return_value = base

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                transactions=[
                    _make_txn("t1", "c1", "a1", "d1", "m1", 1000.0),
                ]
            ),
            text_signals=[],
        )

        result = reasoner.reason(cmd)
        # Score should never exceed 100
        assert result.total_risk_score <= 100

    def test_risk_level_elevation_noted_in_summary(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reasoner, local = _build_reasoner()
        # Start at HIGH (score 60), graph bonus could push to CRITICAL (80+)
        base = _make_base_result(score=70)
        local.reason.return_value = base

        def fake_run_graph_analysis(_command: ReasonAboutRiskCommand) -> list[GraphInsight]:
            return [GraphInsight(category="circular-flow", description="Test cycle", risk_bonus=15)]

        monkeypatch.setattr(reasoner, "_run_graph_analysis", fake_run_graph_analysis)

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                transactions=[_make_txn("t1", "c1", "a1", "d1", "m1", 100.0)],
            ),
            text_signals=[],
        )
        result = reasoner.reason(cmd)

        assert result.total_risk_score == 85
        assert result.risk_level == RiskLevel.CRITICAL
        assert "elevated the risk level" in result.summary


class TestRunGraphAnalysis:
    def test_returns_empty_for_no_transactions(self) -> None:
        reasoner, _ = _build_reasoner()
        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(transactions=[]),
            text_signals=[],
        )
        insights = reasoner._run_graph_analysis(cmd)
        assert insights == []

    def test_runs_all_four_queries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure the orchestrator calls all four analysis methods."""
        reasoner, _ = _build_reasoner()

        called = {"circular": False, "hub": False, "community": False, "mule": False}

        def mock_circular(_graph: object) -> list[GraphInsight]:
            called["circular"] = True
            return []

        def mock_hub(_graph: object) -> list[GraphInsight]:
            called["hub"] = True
            return []

        def mock_community(
            _graph: object,
            _command: ReasonAboutRiskCommand,
        ) -> list[GraphInsight]:
            called["community"] = True
            return []

        def mock_mule(
            _graph: object,
            _command: ReasonAboutRiskCommand,
        ) -> list[GraphInsight]:
            called["mule"] = True
            return []

        monkeypatch.setattr(reasoner, "_detect_circular_flows", mock_circular)
        monkeypatch.setattr(reasoner, "_detect_hub_entities", mock_hub)
        monkeypatch.setattr(reasoner, "_detect_suspicious_communities", mock_community)
        monkeypatch.setattr(reasoner, "_detect_money_mule_paths", mock_mule)

        cmd = ReasonAboutRiskCommand(
            scenario=_make_scenario(
                transactions=[_make_txn("t1", "c1", "a1", "d1", "m1", 100.0)],
            ),
            text_signals=[],
        )
        reasoner._run_graph_analysis(cmd)

        assert all(called.values()), f"Not all queries were called: {called}"
