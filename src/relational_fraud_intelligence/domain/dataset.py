"""Dataset aggregate — uploaded datasets, analysis results, anomaly detection."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.entity import EntityReference
from relational_fraud_intelligence.domain.enums import (
    AnomalyType,
    DatasetStatus,
    RiskLevel,
)
from relational_fraud_intelligence.domain.investigation import (
    GraphAnalysisResult,
    InvestigationLead,
)


class Dataset(AppModel):
    """A batch of uploaded transactions that can be analyzed."""

    dataset_id: str
    name: str
    uploaded_at: datetime
    row_count: int = Field(ge=0)
    status: DatasetStatus = DatasetStatus.UPLOADED
    error_message: str | None = None

    @property
    def is_analyzable(self) -> bool:
        """Return True if the dataset can be submitted for analysis."""
        return self.status in (DatasetStatus.UPLOADED, DatasetStatus.FAILED)


class BenfordDigitResult(AppModel):
    """Benford's Law analysis for a single leading digit."""

    digit: int = Field(ge=1, le=9)
    expected_pct: float
    actual_pct: float
    deviation: float


class VelocitySpike(AppModel):
    """A detected spike in transaction velocity for an entity."""

    entity_id: str
    entity_type: str  # "account" or "merchant"
    window_start: datetime
    window_end: datetime
    transaction_count: int
    total_amount: float
    baseline_avg_count: float
    z_score: float


class AnomalyFlag(AppModel):
    """A single anomaly detected during analysis."""

    anomaly_id: str
    anomaly_type: AnomalyType
    severity: RiskLevel
    title: str
    description: str
    affected_entity_id: str
    affected_entity_type: str  # "account", "merchant", "transaction"
    score: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, object] = Field(default_factory=dict)


class BehavioralInsight(AppModel):
    """A higher-level inference synthesized from multiple related transactions."""

    insight_id: str
    title: str
    severity: RiskLevel
    narrative: str
    entities: list[EntityReference] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)


class AnalysisResult(AppModel):
    """Complete analysis output for an uploaded dataset."""

    analysis_id: str
    dataset_id: str
    completed_at: datetime
    total_transactions: int = Field(ge=0)
    total_anomalies: int = Field(ge=0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel

    # Benford's Law
    benford_chi_squared: float = Field(ge=0.0)
    benford_p_value: float = Field(ge=0.0, le=1.0)
    benford_is_suspicious: bool = False
    benford_digits: list[BenfordDigitResult] = Field(default_factory=list)

    # Statistical outliers
    outlier_count: int = Field(ge=0, default=0)
    outlier_pct: float = Field(ge=0.0, le=100.0, default=0.0)

    # Velocity spikes
    velocity_spikes: list[VelocitySpike] = Field(default_factory=list)

    # Graph analysis
    graph_analysis: GraphAnalysisResult | None = None

    # Higher-level behavioral findings derived from entity relationships
    behavioral_insights: list[BehavioralInsight] = Field(default_factory=list)

    # Investigation-ready hypotheses synthesized from the analysis output
    investigation_leads: list[InvestigationLead] = Field(default_factory=list)

    # All anomaly flags
    anomalies: list[AnomalyFlag] = Field(default_factory=list)

    # Summary
    summary: str = ""
