"""add persistent workflow tables

Revision ID: 20260312_0003
Revises: 20260312_0002
Create Date: 2026-03-12 23:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260312_0003"
down_revision: str | Sequence[str] | None = "20260312_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fraud_cases",
        sa.Column("case_id", sa.String(length=36), primary_key=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("assigned_analyst_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_analyst_name", sa.String(length=160), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.Column("disposition", sa.String(length=64), nullable=True),
        sa.Column("resolution_notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alert_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_fraud_cases_source_type", "fraud_cases", ["source_type"])
    op.create_index("ix_fraud_cases_source_id", "fraud_cases", ["source_id"])
    op.create_index("ix_fraud_cases_scenario_id", "fraud_cases", ["scenario_id"])
    op.create_index("ix_fraud_cases_status", "fraud_cases", ["status"])
    op.create_index("ix_fraud_cases_priority", "fraud_cases", ["priority"])
    op.create_index("ix_fraud_cases_created_at", "fraud_cases", ["created_at"])
    op.create_index("ix_fraud_cases_updated_at", "fraud_cases", ["updated_at"])

    op.create_table(
        "fraud_alerts",
        sa.Column("alert_id", sa.String(length=36), primary_key=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("scenario_id", sa.String(length=120), nullable=True),
        sa.Column("rule_code", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("narrative", sa.String(length=2000), nullable=False),
        sa.Column("assigned_analyst_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_analyst_name", sa.String(length=160), nullable=True),
        sa.Column("linked_case_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_fraud_alerts_source_type", "fraud_alerts", ["source_type"])
    op.create_index("ix_fraud_alerts_source_id", "fraud_alerts", ["source_id"])
    op.create_index("ix_fraud_alerts_scenario_id", "fraud_alerts", ["scenario_id"])
    op.create_index("ix_fraud_alerts_rule_code", "fraud_alerts", ["rule_code"])
    op.create_index("ix_fraud_alerts_severity", "fraud_alerts", ["severity"])
    op.create_index("ix_fraud_alerts_status", "fraud_alerts", ["status"])
    op.create_index("ix_fraud_alerts_created_at", "fraud_alerts", ["created_at"])

    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("transactions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("analysis", sa.JSON(), nullable=True),
    )
    op.create_index("ix_datasets_uploaded_at", "datasets", ["uploaded_at"])
    op.create_index("ix_datasets_status", "datasets", ["status"])


def downgrade() -> None:
    op.drop_index("ix_datasets_status", table_name="datasets")
    op.drop_index("ix_datasets_uploaded_at", table_name="datasets")
    op.drop_table("datasets")

    op.drop_index("ix_fraud_alerts_created_at", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_status", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_severity", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_rule_code", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_scenario_id", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_source_id", table_name="fraud_alerts")
    op.drop_index("ix_fraud_alerts_source_type", table_name="fraud_alerts")
    op.drop_table("fraud_alerts")

    op.drop_index("ix_fraud_cases_updated_at", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_created_at", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_priority", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_status", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_scenario_id", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_source_id", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_source_type", table_name="fraud_cases")
    op.drop_table("fraud_cases")
