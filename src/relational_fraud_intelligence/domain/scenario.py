"""Scenario aggregate — reference fraud scenarios and their metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.entity import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    MerchantProfile,
)
from relational_fraud_intelligence.domain.enums import RiskLevel, ScenarioTag
from relational_fraud_intelligence.domain.transaction import TransactionRecord


class InvestigatorNote(AppModel):
    note_id: str
    subject_customer_id: str
    author: str
    created_at: datetime
    body: str


class FraudScenario(AppModel):
    scenario_id: str
    title: str
    industry: str
    summary: str
    hypothesis: str
    tags: list[ScenarioTag]
    customers: list[CustomerProfile]
    accounts: list[AccountProfile]
    devices: list[DeviceProfile]
    merchants: list[MerchantProfile]
    transactions: list[TransactionRecord]
    investigator_notes: list[InvestigatorNote]


class ScenarioOverview(AppModel):
    scenario_id: str
    title: str
    industry: str
    summary: str
    hypothesis: str
    tags: list[ScenarioTag]
    transaction_count: int = Field(ge=0)
    total_volume: float = Field(ge=0.0)
    baseline_risk: RiskLevel

