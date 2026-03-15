"""Domain model re-exports.

All domain classes were split into focused aggregate modules under
``relational_fraud_intelligence.domain.*``.  This module re-exports every
public symbol so that existing ``from relational_fraud_intelligence.domain.models import X``
import statements continue to work unchanged.

Prefer importing directly from the aggregate module in new code::

    from relational_fraud_intelligence.domain.case import FraudCase
    from relational_fraud_intelligence.domain.alert import FraudAlert
"""

from __future__ import annotations  # noqa: I001 — grouped re-exports are intentional

# ── Base ───────────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.base import AppModel

# ── Enumerations ───────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.enums import (
    AlertStatus,
    AnomalyType,
    CaseDisposition,
    CasePriority,
    CaseStatus,
    DatasetStatus,
    EntityType,
    ExplanationAudience,
    OperatorRole,
    RiskLevel,
    ScenarioTag,
    TextSignalKind,
    TransactionChannel,
    TransactionStatus,
    WorkflowSourceType,
)

# ── Entity profiles ───────────────────────────────────────────────────
from relational_fraud_intelligence.domain.entity import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    EntityReference,
    MerchantProfile,
)

# ── Transactions ──────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.transaction import (
    TransactionRecord,
    UploadedTransaction,
)

# ── Scenarios ─────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.scenario import (
    FraudScenario,
    InvestigatorNote,
    ScenarioOverview,
)

# ── Investigations ────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.investigation import (
    GraphAnalysisResult,
    GraphLink,
    InvestigationCase,
    InvestigationLead,
    InvestigationMetrics,
    ProviderSummary,
    RuleHit,
    TextSignal,
)

# ── Alerts ────────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.alert import FraudAlert

# ── Cases ─────────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.case import (
    CaseComment,
    CaseEvidenceSnapshot,
    FraudCase,
)

# ── Datasets & Analysis ──────────────────────────────────────────────
from relational_fraud_intelligence.domain.dataset import (
    AnalysisResult,
    AnomalyFlag,
    BehavioralInsight,
    BenfordDigitResult,
    Dataset,
    VelocitySpike,
)

# ── Dashboard ─────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.dashboard import (
    ActivityEvent,
    DashboardStats,
    WorkflowStageSnapshot,
)

# ── Operators & Audit ─────────────────────────────────────────────────
from relational_fraud_intelligence.domain.operator import (
    AuditEvent,
    OperatorPrincipal,
)

# ── Workspace ─────────────────────────────────────────────────────────
from relational_fraud_intelligence.domain.workspace import (
    AnalysisExplanation,
    ExplanationProviderSummary,
    RoleStory,
    WorkspaceGuide,
)

# Resolve forward references across modules
CaseEvidenceSnapshot.model_rebuild()
FraudCase.model_rebuild()

__all__ = [
    # base
    "AppModel",
    # enums
    "AlertStatus",
    "AnomalyType",
    "CaseDisposition",
    "CasePriority",
    "CaseStatus",
    "DatasetStatus",
    "EntityType",
    "ExplanationAudience",
    "OperatorRole",
    "RiskLevel",
    "ScenarioTag",
    "TextSignalKind",
    "TransactionChannel",
    "TransactionStatus",
    "WorkflowSourceType",
    # entities
    "AccountProfile",
    "CustomerProfile",
    "DeviceProfile",
    "EntityReference",
    "MerchantProfile",
    # transactions
    "TransactionRecord",
    "UploadedTransaction",
    # scenarios
    "FraudScenario",
    "InvestigatorNote",
    "ScenarioOverview",
    # investigations
    "GraphAnalysisResult",
    "GraphLink",
    "InvestigationCase",
    "InvestigationLead",
    "InvestigationMetrics",
    "ProviderSummary",
    "RuleHit",
    "TextSignal",
    # alerts
    "FraudAlert",
    # cases
    "CaseComment",
    "CaseEvidenceSnapshot",
    "FraudCase",
    # datasets
    "AnalysisResult",
    "AnomalyFlag",
    "BehavioralInsight",
    "BenfordDigitResult",
    "Dataset",
    "VelocitySpike",
    # dashboard
    "ActivityEvent",
    "DashboardStats",
    "WorkflowStageSnapshot",
    # operators
    "AuditEvent",
    "OperatorPrincipal",
    # workspace
    "AnalysisExplanation",
    "ExplanationProviderSummary",
    "RoleStory",
    "WorkspaceGuide",
]
