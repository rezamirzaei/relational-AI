from typing import Protocol

from relational_fraud_intelligence.application.dto.investigation import (
    ScoreTextSignalsCommand,
    ScoreTextSignalsResult,
)


class TextSignalService(Protocol):
    def score(self, command: ScoreTextSignalsCommand) -> ScoreTextSignalsResult:
        ...
