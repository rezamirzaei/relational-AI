"""create scenario schema

Revision ID: 20260312_0001
Revises:
Create Date: 2026-03-12 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260312_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("scenario_id", sa.String(length=100), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("hypothesis", sa.String(length=1000), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
    )
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("segment", sa.String(length=80), nullable=False),
        sa.Column("declared_income_band", sa.String(length=80), nullable=False),
        sa.Column("watchlist_tags", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_customers_scenario_id", "customers", ["scenario_id"])
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("current_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("average_monthly_inflow", sa.Numeric(12, 2), nullable=False),
        sa.Column("chargeback_count", sa.Integer(), nullable=False),
        sa.Column("manual_review_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"])
    op.create_index("ix_accounts_scenario_id", "accounts", ["scenario_id"])
    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column("ip_country_code", sa.String(length=2), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_devices_scenario_id", "devices", ["scenario_id"])
    op.create_table(
        "device_customer_links",
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("device_id", "customer_id"),
    )
    op.create_table(
        "merchants",
        sa.Column("merchant_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_merchants_scenario_id", "merchants", ["scenario_id"])
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("account_id", sa.String(length=100), nullable=False),
        sa.Column("device_id", sa.String(length=100), nullable=False),
        sa.Column("merchant_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.account_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.merchant_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])
    op.create_index("ix_transactions_device_id", "transactions", ["device_id"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_scenario_id", "transactions", ["scenario_id"])
    op.create_table(
        "investigator_notes",
        sa.Column("note_id", sa.String(length=100), primary_key=True),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("subject_customer_id", sa.String(length=100), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subject_customer_id"],
            ["customers.customer_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_investigator_notes_scenario_id",
        "investigator_notes",
        ["scenario_id"],
    )
    op.create_index(
        "ix_investigator_notes_subject_customer_id",
        "investigator_notes",
        ["subject_customer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_investigator_notes_subject_customer_id", table_name="investigator_notes")
    op.drop_index("ix_investigator_notes_scenario_id", table_name="investigator_notes")
    op.drop_table("investigator_notes")
    op.drop_index("ix_transactions_scenario_id", table_name="transactions")
    op.drop_index("ix_transactions_merchant_id", table_name="transactions")
    op.drop_index("ix_transactions_device_id", table_name="transactions")
    op.drop_index("ix_transactions_customer_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_merchants_scenario_id", table_name="merchants")
    op.drop_table("merchants")
    op.drop_table("device_customer_links")
    op.drop_index("ix_devices_scenario_id", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_accounts_scenario_id", table_name="accounts")
    op.drop_index("ix_accounts_customer_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_index("ix_customers_scenario_id", table_name="customers")
    op.drop_table("customers")
    op.drop_table("scenarios")
