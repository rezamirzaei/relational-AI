from typing import Protocol

from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AnalysisResult,
    Dataset,
    ExplanationAudience,
)


class AnalysisExplanationService(Protocol):
    def explain(
        self,
        *,
        dataset: Dataset,
        analysis: AnalysisResult,
        audience: ExplanationAudience,
    ) -> AnalysisExplanation: ...
