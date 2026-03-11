from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner


class FallbackRiskReasoner:
    def __init__(
        self,
        primary: RiskReasoner,
        fallback: RiskReasoner,
        requested_provider: str,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._requested_provider = requested_provider

    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult:
        try:
            return self._primary.reason(command)
        except Exception as exc:
            fallback_result = self._fallback.reason(command)
            return fallback_result.model_copy(
                update={
                    "requested_provider": self._requested_provider,
                    "provider_notes": [
                        f"Primary reasoner '{self._requested_provider}' failed: {exc}",
                        *fallback_result.provider_notes,
                    ],
                }
            )
