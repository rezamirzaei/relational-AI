"""Case aggregate — persistent fraud investigation cases with lifecycle management."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import (
    CaseDisposition,
    CasePriority,
    CaseStatus,
    RiskLevel,
    WorkflowSourceType,
)
from relational_fraud_intelligence.domain.investigation import (
    InvestigationCase,
)
from relational_fraud_intelligence.domain.scenario import InvestigatorNote
from relational_fraud_intelligence.domain.transaction import TransactionRecord, UploadedTransaction

if TYPE_CHECKING:
    from relational_fraud_intelligence.domain.dataset import AnalysisResult, Dataset


class FraudCase(AppModel):
    """A persistent fraud investigation case with lifecycle management.

    Domain invariants:
    - A case cannot move backwards in its lifecycle
      (OPEN → INVESTIGATING → ESCALATED → RESOLVED → CLOSED).
    - ``disposition`` is required when transitioning to RESOLVED.
    - ``resolved_at`` is set automatically when status becomes RESOLVED.
    """

    case_id: str
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str
    scenario_id: str | None = None
    title: str
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    assigned_analyst_id: str | None = None
    assigned_analyst_name: str | None = None
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    summary: str
    disposition: CaseDisposition | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    sla_deadline: datetime | None = None
    comment_count: int = Field(ge=0, default=0)
    alert_count: int = Field(ge=0, default=0)
    evidence_snapshot: CaseEvidenceSnapshot | None = Field(default=None, exclude=True)

    _STATUS_ORDER: list[CaseStatus] = [
        CaseStatus.OPEN,
        CaseStatus.INVESTIGATING,
        CaseStatus.ESCALATED,
        CaseStatus.RESOLVED,
        CaseStatus.CLOSED,
    ]

    def can_transition_to(self, new_status: CaseStatus) -> bool:
        """Return True if transitioning from the current status to *new_status* is valid."""
        try:
            current_idx = self._STATUS_ORDER.index(self.status)
            new_idx = self._STATUS_ORDER.index(new_status)
        except ValueError:
            return False
        return new_idx > current_idx

    @property
    def is_terminal(self) -> bool:
        """Return True if the case is in a terminal state."""
        return self.status in (CaseStatus.RESOLVED, CaseStatus.CLOSED)


class CaseComment(AppModel):
    """A timestamped note attached to a fraud case by an analyst."""

    comment_id: str
    case_id: str
    author_id: str
    author_name: str
    body: str
    created_at: datetime


class CaseEvidenceSnapshot(AppModel):
    """Immutable source evidence captured when a case is created."""

    investigation: InvestigationCase | None = None
    analysis: AnalysisResult | None = None
    dataset: Dataset | None = None
    scenario_transactions: list[TransactionRecord] = Field(default_factory=list)
    dataset_transactions: list[UploadedTransaction] = Field(default_factory=list)
    investigator_notes: list[InvestigatorNote] = Field(default_factory=list)



