from __future__ import annotations

import json
from typing import Any, cast

from huggingface_hub import InferenceClient

from relational_fraud_intelligence.domain.models import (
    AnalysisExplanation,
    AnalysisResult,
    Dataset,
    ExplanationAudience,
    ExplanationProviderSummary,
)
from relational_fraud_intelligence.settings import AppSettings

from .deterministic_analysis_explanation_service import (
    DeterministicAnalysisExplanationService,
)


class HuggingFaceAnalysisExplanationService:
    def __init__(self, settings: AppSettings) -> None:
        if not settings.huggingface_api_token:
            raise ValueError(
                "RFI_HUGGINGFACE_API_TOKEN must be set for the Hugging Face explanation provider."
            )
        self._settings = settings
        self._client = InferenceClient(
            token=settings.huggingface_api_token,
            timeout=settings.huggingface_timeout_seconds,
        )
        self._deterministic = DeterministicAnalysisExplanationService()

    def explain(
        self,
        *,
        dataset: Dataset,
        analysis: AnalysisResult,
        audience: ExplanationAudience,
    ) -> AnalysisExplanation:
        deterministic = self._deterministic.explain(
            dataset=dataset,
            analysis=analysis,
            audience=audience,
        )
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a fraud operations copilot. Rewrite the provided "
                    "deterministic evidence into a concise operator brief. Do not "
                    "change any score, threshold, finding count, or recommendation. "
                    "Return a JSON object with keys: headline, narrative, "
                    "recommended_actions, watchouts."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "dataset_name": dataset.name,
                        "audience": audience,
                        "headline": deterministic.headline,
                        "narrative": deterministic.narrative,
                        "deterministic_evidence": deterministic.deterministic_evidence,
                        "recommended_actions": deterministic.recommended_actions,
                        "watchouts": deterministic.watchouts,
                    }
                ),
            },
        ]
        completion = self._client.chat_completion(
            messages=messages,
            model=self._settings.huggingface_explanation_model,
            max_tokens=self._settings.huggingface_explanation_max_tokens,
            temperature=0.2,
            response_format=cast(Any, {"type": "json_object"}),
        )
        payload = json.loads(_extract_completion_text(completion))

        return deterministic.model_copy(
            update={
                "headline": str(payload.get("headline", deterministic.headline)),
                "narrative": str(payload.get("narrative", deterministic.narrative)),
                "recommended_actions": _coerce_list(
                    payload.get("recommended_actions"),
                    deterministic.recommended_actions,
                ),
                "watchouts": _coerce_list(payload.get("watchouts"), deterministic.watchouts),
                "provider_summary": ExplanationProviderSummary(
                    requested_provider="huggingface",
                    active_provider="huggingface",
                    source_of_truth="statistical-and-behavioral-analysis",
                    notes=[
                        "The Hugging Face copilot rewrote dataset-derived findings "
                        "into operator language.",
                        "The underlying analyzers still own the score, alerts, "
                        "and case thresholds.",
                    ],
                ),
            }
        )


def _extract_completion_text(completion: Any) -> str:
    choices = getattr(completion, "choices", None)
    if not choices:
        raise ValueError("Hugging Face explanation response did not include choices.")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message is not None else None
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
            for part in content
        )
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Hugging Face explanation response did not include content.")
    return content


def _coerce_list(value: object, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:4] or fallback
