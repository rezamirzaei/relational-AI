from __future__ import annotations

from typing import Any

from huggingface_hub import InferenceClient

from relational_fraud_intelligence.application.dto.investigation import (
    ScoreTextSignalsCommand,
    ScoreTextSignalsResult,
)
from relational_fraud_intelligence.domain.models import TextSignal, TextSignalKind
from relational_fraud_intelligence.settings import AppSettings


class HuggingFaceTextSignalService:
    _note_labels = [
        "synthetic identity",
        "account takeover",
        "money mule",
        "device sharing",
        "credential compromise",
        "sim swap",
    ]
    _merchant_labels = [
        "digital goods",
        "gift card liquidation",
        "money transfer",
        "cross-border payouts",
        "low risk commerce",
    ]

    def __init__(self, settings: AppSettings) -> None:
        if not settings.huggingface_api_token:
            raise ValueError("RFI_HUGGINGFACE_API_TOKEN must be set for the Hugging Face provider.")
        self._settings = settings
        self._client = InferenceClient(
            token=settings.huggingface_api_token,
            timeout=settings.huggingface_timeout_seconds,
        )

    def score(self, command: ScoreTextSignalsCommand) -> ScoreTextSignalsResult:
        signals: list[TextSignal] = []

        for note in command.scenario.investigator_notes:
            outputs = self._client.zero_shot_classification(
                note.body,
                candidate_labels=self._note_labels,
                multi_label=True,
                model=self._settings.huggingface_zero_shot_model,
            )
            signals.extend(
                self._build_signals(
                    source_prefix="note",
                    source_id=note.note_id,
                    source_kind=TextSignalKind.INVESTIGATOR_NOTE,
                    outputs=outputs,
                    threshold=0.55,
                )
            )

        for merchant in command.scenario.merchants:
            text = (
                f"{merchant.display_name}. {merchant.description}. Category: {merchant.category}."
            )
            outputs = self._client.zero_shot_classification(
                text,
                candidate_labels=self._merchant_labels,
                multi_label=True,
                model=self._settings.huggingface_zero_shot_model,
            )
            signals.extend(
                self._build_signals(
                    source_prefix="merchant",
                    source_id=merchant.merchant_id,
                    source_kind=TextSignalKind.MERCHANT_DESCRIPTION,
                    outputs=outputs,
                    threshold=0.52,
                )
            )

        return ScoreTextSignalsResult(
            requested_provider="huggingface",
            active_provider="huggingface",
            notes=[
                "Hugging Face zero-shot classification enriched investigator notes "
                "and merchant descriptions."
            ],
            signals=signals,
        )

    def _build_signals(
        self,
        source_prefix: str,
        source_id: str,
        source_kind: TextSignalKind,
        outputs: list[Any],
        threshold: float,
    ) -> list[TextSignal]:
        signals: list[TextSignal] = []
        for output in outputs:
            label = self._extract_value(output, "label")
            score = float(self._extract_value(output, "score"))
            if score < threshold:
                continue
            signals.append(
                TextSignal(
                    signal_id=f"{source_prefix}::{source_id}::{label.replace(' ', '-')}",
                    provider="huggingface",
                    source_kind=source_kind,
                    source_id=source_id,
                    label=label,
                    confidence=round(score, 4),
                    rationale=(
                        "Hugging Face classified this text as "
                        f"'{label}' with confidence {score:.2f}."
                    ),
                )
            )
        return signals

    @staticmethod
    def _extract_value(output: Any, field_name: str) -> Any:
        if isinstance(output, dict):
            return output[field_name]
        return getattr(output, field_name)
