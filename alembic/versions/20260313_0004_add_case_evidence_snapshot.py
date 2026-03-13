"""add case evidence snapshots

Revision ID: 20260313_0004
Revises: 20260312_0003
Create Date: 2026-03-13 22:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260313_0004"
down_revision: str | Sequence[str] | None = "20260312_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fraud_cases", sa.Column("evidence_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("fraud_cases", "evidence_snapshot")
