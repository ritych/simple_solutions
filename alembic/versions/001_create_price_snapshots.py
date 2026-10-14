"""create price_snapshots

Revision ID: 001
Revises:
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("recorded_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("price > 0", name="ck_price_snapshots_price_positive"),
        sa.CheckConstraint(
            "recorded_at >= 0",
            name="ck_price_snapshots_recorded_at_non_negative",
        ),
        sa.UniqueConstraint(
            "ticker",
            "recorded_at",
            name="uq_price_snapshots_ticker_recorded_at",
        ),
    )


def downgrade() -> None:
    op.drop_table("price_snapshots")
