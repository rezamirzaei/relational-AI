"""Domain enumerations — shared vocabulary for the fraud intelligence platform."""

from __future__ import annotations

from enum import StrEnum


class EntityType(StrEnum):
    CUSTOMER = "customer"
    ACCOUNT = "account"
    DEVICE = "device"
    MERCHANT = "merchant"
    TRANSACTION = "transaction"
    NOTE = "note"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseDisposition(StrEnum):
    CONFIRMED_FRAUD = "confirmed-fraud"
    FALSE_POSITIVE = "false-positive"
    INCONCLUSIVE = "inconclusive"
    REFERRED_TO_LAW_ENFORCEMENT = "referred-to-law-enforcement"


class AlertStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false-positive"


class ScenarioTag(StrEnum):
    FRAUD = "fraud"
    SYNTHETIC_IDENTITY = "synthetic-identity"
    ACCOUNT_TAKEOVER = "account-takeover"
    DEVICE_RING = "device-ring"
    CROSS_BORDER = "cross-border"
    MONEY_MULE = "money-mule"
    BUST_OUT = "bust-out"
    FIRST_PARTY = "first-party"


class TransactionChannel(StrEnum):
    CARD_NOT_PRESENT = "card-not-present"
    WALLET = "wallet"
    BANK_TRANSFER = "bank-transfer"
    CARD_PRESENT = "card-present"
    ACH = "ach"


class TransactionStatus(StrEnum):
    APPROVED = "approved"
    REVIEW = "review"
    DECLINED = "declined"
    PENDING = "pending"


class TextSignalKind(StrEnum):
    INVESTIGATOR_NOTE = "investigator-note"
    MERCHANT_DESCRIPTION = "merchant-description"


class DatasetStatus(StrEnum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnomalyType(StrEnum):
    BENFORD_VIOLATION = "benford-violation"
    STATISTICAL_OUTLIER = "statistical-outlier"
    VELOCITY_SPIKE = "velocity-spike"
    GRAPH_CLUSTER = "graph-cluster"
    ROUND_AMOUNT = "round-amount"
    SHARED_IDENTIFIER = "shared-identifier"
    MERCHANT_CONCENTRATION = "merchant-concentration"
    GEOGRAPHIC_DRIFT = "geographic-drift"
    PEER_GROUP_OUTLIER = "peer-group-outlier"


class OperatorRole(StrEnum):
    ANALYST = "analyst"
    ADMIN = "admin"


class ExplanationAudience(StrEnum):
    ANALYST = "analyst"
    ADMIN = "admin"


class WorkflowSourceType(StrEnum):
    SCENARIO = "scenario"
    DATASET = "dataset"

