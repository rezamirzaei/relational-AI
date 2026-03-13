from relational_fraud_intelligence.application.ports.explanations import (
    AnalysisExplanationService,
)
from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AnalysisResult,
    Dataset,
    ExplanationAudience,
)


class FallbackAnalysisExplanationService:
    def __init__(
        self,
        primary: AnalysisExplanationService,
        fallback: AnalysisExplanationService,
        requested_provider: str,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._requested_provider = requested_provider

    def explain(
        self,
        *,
        dataset: Dataset,
        analysis: AnalysisResult,
        audience: ExplanationAudience,
    ) -> AnalysisExplanation:
        try:
            return self._primary.explain(
                dataset=dataset,
                analysis=analysis,
                audience=audience,
            )
        except Exception as exc:
            fallback_result = self._fallback.explain(
                dataset=dataset,
                analysis=analysis,
                audience=audience,
            )
            provider_summary = fallback_result.provider_summary.model_copy(
                update={
                    "requested_provider": self._requested_provider,
                    "notes": [
                        f"Primary explanation provider '{self._requested_provider}' failed: {exc}",
                        *fallback_result.provider_summary.notes,
                    ],
                }
            )
            return fallback_result.model_copy(update={"provider_summary": provider_summary})
