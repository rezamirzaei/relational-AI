from typing import Protocol

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)


class RiskReasoner(Protocol):
    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult: ...
