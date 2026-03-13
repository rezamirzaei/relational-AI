from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AppModel,
    ExplanationAudience,
)


class GetAnalysisExplanationQuery(AppModel):
    dataset_id: str
    audience: ExplanationAudience = ExplanationAudience.ANALYST


class GetAnalysisExplanationResult(AppModel):
    explanation: AnalysisExplanation
