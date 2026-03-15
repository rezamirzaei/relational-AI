"""Transaction models — individual transaction records and uploads."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import TransactionChannel, TransactionStatus


class TransactionRecord(AppModel):
    transaction_id: str
    customer_id: str
    account_id: str
    device_id: str
    merchant_id: str
    occurred_at: datetime
    amount: float = Field(gt=0.0)
    currency: str = Field(min_length=3, max_length=3)
    channel: TransactionChannel
    status: TransactionStatus


class UploadedTransaction(AppModel):
    """A single transaction row from a user-uploaded CSV or API ingestion."""

    row_index: int = Field(ge=0)
    transaction_id: str
    account_id: str
    amount: float = Field(gt=0.0)
    timestamp: datetime
    merchant: str = ""
    category: str = ""
    device_fingerprint: str = ""
    ip_country: str = ""
    channel: str = ""
    is_fraud_label: bool | None = None  # ground-truth label if available

