from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from relational_fraud_intelligence.infrastructure.persistence.base import Base

device_customer_links = Table(
    "device_customer_links",
    Base.metadata,
    Column(
        "device_id",
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "customer_id",
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ScenarioRecord(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(1000))
    hypothesis: Mapped[str] = mapped_column(String(1000))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    customers: Mapped[list[CustomerRecord]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list[AccountRecord]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    devices: Mapped[list[DeviceRecord]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    merchants: Mapped[list[MerchantRecord]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list[TransactionRecordOrm]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )
    investigator_notes: Mapped[list[InvestigatorNoteRecord]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class CustomerRecord(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(160))
    country_code: Mapped[str] = mapped_column(String(2))
    segment: Mapped[str] = mapped_column(String(80))
    declared_income_band: Mapped[str] = mapped_column(String(80))
    watchlist_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="customers")
    accounts: Mapped[list[AccountRecord]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    linked_devices: Mapped[list[DeviceRecord]] = relationship(
        secondary=device_customer_links,
        back_populates="linked_customers",
    )
    investigator_notes: Mapped[list[InvestigatorNoteRecord]] = relationship(
        back_populates="subject_customer",
        cascade="all, delete-orphan",
    )


class AccountRecord(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        index=True,
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    current_balance: Mapped[float] = mapped_column(Numeric(12, 2))
    average_monthly_inflow: Mapped[float] = mapped_column(Numeric(12, 2))
    chargeback_count: Mapped[int] = mapped_column(Integer)
    manual_review_count: Mapped[int] = mapped_column(Integer)

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="accounts")
    customer: Mapped[CustomerRecord] = relationship(back_populates="accounts")


class DeviceRecord(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    fingerprint: Mapped[str] = mapped_column(String(255))
    ip_country_code: Mapped[str] = mapped_column(String(2))
    trust_score: Mapped[float] = mapped_column(Float)

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="devices")
    linked_customers: Mapped[list[CustomerRecord]] = relationship(
        secondary=device_customer_links,
        back_populates="linked_devices",
    )


class MerchantRecord(Base):
    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(1000))

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="merchants")


class TransactionRecordOrm(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        index=True,
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="CASCADE"),
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        index=True,
    )
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"),
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    channel: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="transactions")
    customer: Mapped[CustomerRecord] = relationship()
    account: Mapped[AccountRecord] = relationship()
    device: Mapped[DeviceRecord] = relationship()
    merchant: Mapped[MerchantRecord] = relationship()


class InvestigatorNoteRecord(Base):
    __tablename__ = "investigator_notes"

    note_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
    )
    subject_customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        index=True,
    )
    author: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    body: Mapped[str] = mapped_column(String(2000))

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="investigator_notes")
    subject_customer: Mapped[CustomerRecord] = relationship(back_populates="investigator_notes")


class OperatorUserRecord(Base):
    __tablename__ = "operator_users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    http_method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(255))
    status_code: Mapped[int] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)


class FraudCaseRecord(Base):
    __tablename__ = "fraud_cases"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    scenario_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    priority: Mapped[str] = mapped_column(String(32), index=True)
    assigned_analyst_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_analyst_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(String(2000))
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)


class FraudAlertRecord(Base):
    __tablename__ = "fraud_alerts"

    alert_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    scenario_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    rule_code: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    narrative: Mapped[str] = mapped_column(String(2000))
    assigned_analyst_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_analyst_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    linked_case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class DatasetRecord(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), index=True)
    row_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    transactions: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    analysis: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
