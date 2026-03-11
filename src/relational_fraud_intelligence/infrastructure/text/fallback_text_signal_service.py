from relational_fraud_intelligence.application.dto.investigation import (
    ScoreTextSignalsCommand,
    ScoreTextSignalsResult,
)
from relational_fraud_intelligence.application.ports.text_signals import TextSignalService


class FallbackTextSignalService:
    def __init__(
        self,
        primary: TextSignalService,
        fallback: TextSignalService,
        requested_provider: str,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._requested_provider = requested_provider

    def score(self, command: ScoreTextSignalsCommand) -> ScoreTextSignalsResult:
        try:
            return self._primary.score(command)
        except Exception as exc:
            fallback_result = self._fallback.score(command)
            return fallback_result.model_copy(
                update={
                    "requested_provider": self._requested_provider,
                    "notes": [
                        f"Primary text provider '{self._requested_provider}' failed: {exc}",
                        *fallback_result.notes,
                    ],
                }
            )
