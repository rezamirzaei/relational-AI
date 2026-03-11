from relational_fraud_intelligence.application.dto.investigation import ScoreTextSignalsCommand
from relational_fraud_intelligence.infrastructure.config.demo_data import build_demo_scenarios
from relational_fraud_intelligence.infrastructure.text.keyword_text_signal_service import (
    KeywordTextSignalService,
)


def test_keyword_text_signal_service_flags_expected_labels() -> None:
    service = KeywordTextSignalService()
    synthetic_identity_scenario = build_demo_scenarios()[0]

    result = service.score(ScoreTextSignalsCommand(scenario=synthetic_identity_scenario))
    labels = {signal.label for signal in result.signals}

    assert "synthetic identity" in labels
    assert "device sharing" in labels
    assert "gift card liquidation" in labels
