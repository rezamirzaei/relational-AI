"""Entity profiles — customers, accounts, devices, merchants."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import EntityType


class EntityReference(AppModel):
    entity_type: EntityType
    entity_id: str
    display_name: str


class CustomerProfile(AppModel):
    customer_id: str
    full_name: str
    country_code: str = Field(min_length=2, max_length=2)
    segment: str
    declared_income_band: str
    linked_account_ids: list[str]
    linked_device_ids: list[str]
    watchlist_tags: list[str] = Field(default_factory=list)


class AccountProfile(AppModel):
    account_id: str
    customer_id: str
    opened_at: datetime
    current_balance: float
    average_monthly_inflow: float
    chargeback_count: int = Field(ge=0)
    manual_review_count: int = Field(ge=0)


class DeviceProfile(AppModel):
    device_id: str
    fingerprint: str
    ip_country_code: str = Field(min_length=2, max_length=2)
    linked_customer_ids: list[str]
    trust_score: float = Field(ge=0.0, le=1.0)


class MerchantProfile(AppModel):
    merchant_id: str
    display_name: str
    country_code: str = Field(min_length=2, max_length=2)
    category: str
    description: str

