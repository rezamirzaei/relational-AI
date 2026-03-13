from __future__ import annotations

from unittest.mock import Mock

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
    ScoreTextSignalsCommand,
    ScoreTextSignalsResult,
)
from relational_fraud_intelligence.domain.models import (
    FraudScenario,
    InvestigationMetrics,
    RiskLevel,
    ScenarioTag,
)
from relational_fraud_intelligence.infrastructure.reasoners.fallback_reasoner import (
    FallbackRiskReasoner,
)
from relational_fraud_intelligence.infrastructure.text.fallback_text_signal_service import (
    FallbackTextSignalService,
)


def _make_scenario() -> FraudScenario:
    return FraudScenario(
        scenario_id="fallback-test",
        title="Fallback test",
        industry="finance",
        summary="Fallback test scenario",
        hypothesis="Fallback providers should preserve operator context.",
        tags=[ScenarioTag.FRAUD],
        customers=[],
        accounts=[],
        devices=[],
        merchants=[],
        transactions=[],
        investigator_notes=[],
    )


def _make_text_result(
    *,
    requested_provider: str = "keyword",
    active_provider: str = "keyword",
    notes: list[str] | None = None,
) -> ScoreTextSignalsResult:
    return ScoreTextSignalsResult(
        requested_provider=requested_provider,
        active_provider=active_provider,
        notes=notes or [],
        signals=[],
    )


def _make_reasoning_result(
    *,
    requested_provider: str = "local-rule-engine",
    active_provider: str = "local-rule-engine",
    provider_notes: list[str] | None = None,
) -> ReasonAboutRiskResult:
    return ReasonAboutRiskResult(
        requested_provider=requested_provider,
        active_provider=active_provider,
        provider_notes=provider_notes or [],
        risk_level=RiskLevel.MEDIUM,
        total_risk_score=40,
        summary="Fallback reasoner result.",
        metrics=InvestigationMetrics(
            total_transaction_volume=0.0,
            suspicious_transaction_volume=0.0,
            suspicious_transaction_count=0,
            shared_device_count=0,
            linked_customer_count=0,
        ),
        top_rule_hits=[],
        graph_links=[],
        suspicious_transactions=[],
        recommended_actions=[],
    )


def test_fallback_text_signal_service_returns_primary_result_when_available() -> None:
    scenario = _make_scenario()
    command = ScoreTextSignalsCommand(scenario=scenario)
    expected = _make_text_result()
    primary = Mock()
    primary.score.return_value = expected
    fallback = Mock()
    service = FallbackTextSignalService(primary, fallback, requested_provider="huggingface")

    result = service.score(command)

    assert result == expected
    primary.score.assert_called_once_with(command)
    fallback.score.assert_not_called()


def test_fallback_text_signal_service_preserves_requested_provider_on_failure() -> None:
    scenario = _make_scenario()
    command = ScoreTextSignalsCommand(scenario=scenario)
    primary = Mock()
    primary.score.side_effect = RuntimeError("provider offline")
    fallback = Mock()
    fallback.score.return_value = _make_text_result(
        requested_provider="keyword",
        active_provider="keyword",
        notes=["Keyword heuristics applied."],
    )
    service = FallbackTextSignalService(primary, fallback, requested_provider="huggingface")

    result = service.score(command)

    assert result.requested_provider == "huggingface"
    assert result.active_provider == "keyword"
    assert result.notes == [
        "Primary text provider 'huggingface' failed: provider offline",
        "Keyword heuristics applied.",
    ]


def test_fallback_reasoner_returns_primary_result_when_available() -> None:
    scenario = _make_scenario()
    command = ReasonAboutRiskCommand(scenario=scenario, text_signals=[])
    expected = _make_reasoning_result()
    primary = Mock()
    primary.reason.return_value = expected
    fallback = Mock()
    reasoner = FallbackRiskReasoner(primary, fallback, requested_provider="relationalai")

    result = reasoner.reason(command)

    assert result == expected
    primary.reason.assert_called_once_with(command)
    fallback.reason.assert_not_called()


def test_fallback_reasoner_preserves_requested_provider_on_failure() -> None:
    scenario = _make_scenario()
    command = ReasonAboutRiskCommand(scenario=scenario, text_signals=[])
    primary = Mock()
    primary.reason.side_effect = RuntimeError("reasoner offline")
    fallback = Mock()
    fallback.reason.return_value = _make_reasoning_result(
        requested_provider="local-rule-engine",
        active_provider="local-rule-engine",
        provider_notes=["Local rules used."],
    )
    reasoner = FallbackRiskReasoner(primary, fallback, requested_provider="relationalai")

    result = reasoner.reason(command)

    assert result.requested_provider == "relationalai"
    assert result.active_provider == "local-rule-engine"
    assert result.provider_notes == [
        "Primary reasoner 'relationalai' failed: reasoner offline",
        "Local rules used.",
    ]
