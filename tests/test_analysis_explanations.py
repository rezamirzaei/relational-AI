from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AnalysisResult,
    AnomalyFlag,
    AnomalyType,
    BenfordDigitResult,
    Dataset,
    DatasetStatus,
    ExplanationAudience,
    InvestigationLead,
    RiskLevel,
    VelocitySpike,
)
from relational_fraud_intelligence.infrastructure.explanations import (
    DeterministicAnalysisExplanationService,
    FallbackAnalysisExplanationService,
    HuggingFaceAnalysisExplanationService,
)
from relational_fraud_intelligence.settings import AppSettings


def test_deterministic_explanation_service_builds_operator_brief() -> None:
    service = DeterministicAnalysisExplanationService()

    explanation = service.explain(
        dataset=_build_dataset(),
        analysis=_build_analysis_result(),
        audience=ExplanationAudience.ANALYST,
    )

    assert explanation.dataset_name == "march-transactions.csv"
    assert explanation.provider_summary.active_provider == "deterministic"
    assert explanation.provider_summary.source_of_truth == "statistical-and-behavioral-analysis"
    assert explanation.recommended_actions
    assert any("source of truth" in item.lower() for item in explanation.watchouts)
    assert any("Benford" in item for item in explanation.deterministic_evidence)
    assert any("Top lead" in item for item in explanation.deterministic_evidence)


def test_fallback_explanation_service_annotates_primary_failure() -> None:
    deterministic = DeterministicAnalysisExplanationService()

    class BrokenExplanationService:
        def explain(
            self,
            *,
            dataset: Dataset,
            analysis: AnalysisResult,
            audience: ExplanationAudience,
        ) -> AnalysisExplanation:
            _ = (dataset, analysis, audience)
            raise RuntimeError("provider unavailable")

    service = FallbackAnalysisExplanationService(
        primary=BrokenExplanationService(),
        fallback=deterministic,
        requested_provider="huggingface",
    )

    explanation = service.explain(
        dataset=_build_dataset(),
        analysis=_build_analysis_result(),
        audience=ExplanationAudience.ADMIN,
    )

    assert explanation.provider_summary.requested_provider == "huggingface"
    assert "provider unavailable" in explanation.provider_summary.notes[0]
    assert explanation.provider_summary.active_provider == "deterministic"


def test_huggingface_explanation_service_rewrites_deterministic_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeInferenceClient:
        def __init__(self, *, token: str, timeout: float) -> None:
            self.token = token
            self.timeout = timeout

        def chat_completion(self, **_: object) -> object:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"headline":"Rewritten headline",'
                                '"narrative":"Rewritten narrative",'
                                '"recommended_actions":["Inspect queue"],'
                                '"watchouts":["Stay deterministic"]}'
                            )
                        )
                    )
                ]
            )

    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.explanations."
        "huggingface_analysis_explanation_service.InferenceClient",
        FakeInferenceClient,
    )

    service = HuggingFaceAnalysisExplanationService(
        AppSettings(
            jwt_secret="test-secret-key-for-unit-tests-0001",
            huggingface_api_token="hf-test-token",
        )
    )

    explanation = service.explain(
        dataset=_build_dataset(),
        analysis=_build_analysis_result(),
        audience=ExplanationAudience.ADMIN,
    )

    assert explanation.headline == "Rewritten headline"
    assert explanation.narrative == "Rewritten narrative"
    assert explanation.recommended_actions == ["Inspect queue"]
    assert explanation.watchouts == ["Stay deterministic"]
    assert explanation.provider_summary.active_provider == "huggingface"
    assert explanation.provider_summary.source_of_truth == "statistical-and-behavioral-analysis"


def _build_dataset() -> Dataset:
    return Dataset(
        dataset_id="dataset-1",
        name="march-transactions.csv",
        uploaded_at=datetime.now(UTC),
        row_count=128,
        status=DatasetStatus.COMPLETED,
    )


def _build_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        analysis_id="analysis-1",
        dataset_id="dataset-1",
        completed_at=datetime.now(UTC),
        total_transactions=128,
        total_anomalies=3,
        risk_score=68,
        risk_level=RiskLevel.HIGH,
        benford_chi_squared=18.4,
        benford_p_value=0.0021,
        benford_is_suspicious=True,
        benford_digits=[
            BenfordDigitResult(digit=1, expected_pct=30.1, actual_pct=18.4, deviation=-11.7)
        ],
        outlier_count=2,
        outlier_pct=1.6,
        velocity_spikes=[
            VelocitySpike(
                entity_id="acct-77",
                entity_type="account",
                window_start=datetime.now(UTC),
                window_end=datetime.now(UTC),
                transaction_count=7,
                total_amount=12400,
                baseline_avg_count=1.1,
                z_score=4.8,
            )
        ],
        anomalies=[
            AnomalyFlag(
                anomaly_id="anom-1",
                anomaly_type=AnomalyType.VELOCITY_SPIKE,
                severity=RiskLevel.HIGH,
                title="Velocity spike",
                description="Rapid sequence of high-value transactions.",
                affected_entity_id="acct-77",
                affected_entity_type="account",
                score=0.91,
                evidence={},
            ),
            AnomalyFlag(
                anomaly_id="anom-2",
                anomaly_type=AnomalyType.ROUND_AMOUNT,
                severity=RiskLevel.MEDIUM,
                title="Round amount cluster",
                description="Multiple rounded transactions were detected.",
                affected_entity_id="acct-77",
                affected_entity_type="account",
                score=0.54,
                evidence={},
            ),
        ],
        investigation_leads=[
            InvestigationLead(
                lead_id="lead::velocity::account::acct-77",
                lead_type="velocity-burst",
                title="Rapid transaction burst requires timeline review",
                severity=RiskLevel.HIGH,
                hypothesis=(
                    "The account compressed unusual volume into a short window, which is "
                    "consistent with takeover or fast cash-out behavior."
                ),
                narrative=(
                    "Account acct-77 generated 7 transactions totaling $12,400.00 with z=4.8."
                ),
                supporting_anomaly_ids=["anom-1"],
                recommended_actions=[
                    (
                        "Reconstruct the timeline around the spike window and identify "
                        "the triggering event."
                    )
                ],
                evidence={"supporting_amount": 12400.0},
            )
        ],
        summary="Dataset analysis generated a high-risk alert candidate.",
    )
