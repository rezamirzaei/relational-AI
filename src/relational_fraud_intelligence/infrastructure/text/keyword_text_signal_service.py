from relational_fraud_intelligence.application.dto.investigation import (
    ScoreTextSignalsCommand,
    ScoreTextSignalsResult,
)
from relational_fraud_intelligence.domain.models import TextSignal, TextSignalKind


class KeywordTextSignalService:
    _note_keywords: tuple[tuple[str, str, float, str], ...] = (
        (
            "synthetic identity",
            "synthetic identity",
            0.94,
            "The note explicitly references synthetic identity behavior.",
        ),
        (
            "shared device",
            "device sharing",
            0.88,
            "The note references a shared device used across identities.",
        ),
        ("mule", "money mule", 0.83, "The note points to mule-style cash out behavior."),
        ("sim swap", "sim swap", 0.9, "The note mentions possible SIM swap activity."),
        (
            "credential",
            "credential compromise",
            0.78,
            "The note mentions credential compromise or stuffing.",
        ),
    )

    _merchant_keywords: tuple[tuple[str, str, float, str], ...] = (
        (
            "gift card",
            "gift card liquidation",
            0.89,
            "The merchant description indicates digital gift card resale.",
        ),
        ("instant resale", "rapid resale channel", 0.8, "The merchant supports fast liquidation."),
        (
            "cross-border payout",
            "cross-border payouts",
            0.84,
            "The merchant operates in cross-border disbursement.",
        ),
        ("money transfer", "money transfer", 0.76, "The merchant category is money transfer."),
    )

    def score(self, command: ScoreTextSignalsCommand) -> ScoreTextSignalsResult:
        signals: list[TextSignal] = []

        for note in command.scenario.investigator_notes:
            normalized_body = note.body.lower()
            for keyword, label, confidence, rationale in self._note_keywords:
                if keyword in normalized_body:
                    signals.append(
                        TextSignal(
                            signal_id=f"note::{note.note_id}::{label.replace(' ', '-')}",
                            provider="keyword",
                            source_kind=TextSignalKind.INVESTIGATOR_NOTE,
                            source_id=note.note_id,
                            label=label,
                            confidence=confidence,
                            rationale=rationale,
                        )
                    )

        for merchant in command.scenario.merchants:
            normalized_description = (
                f"{merchant.display_name} {merchant.description} {merchant.category}".lower()
            )
            for keyword, label, confidence, rationale in self._merchant_keywords:
                if keyword in normalized_description:
                    signal_id = f"merchant::{merchant.merchant_id}::{label.replace(' ', '-')}"
                    signals.append(
                        TextSignal(
                            signal_id=signal_id,
                            provider="keyword",
                            source_kind=TextSignalKind.MERCHANT_DESCRIPTION,
                            source_id=merchant.merchant_id,
                            label=label,
                            confidence=confidence,
                            rationale=rationale,
                        )
                    )

        return ScoreTextSignalsResult(
            requested_provider="keyword",
            active_provider="keyword",
            notes=["Keyword heuristics are active for deterministic demo mode."],
            signals=signals,
        )
