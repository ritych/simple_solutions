from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Identity, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PriceSnapshotRow(Base):
    """ORM mapping for one stored index-price observation."""

    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "recorded_at",
            name="uq_price_snapshots_ticker_recorded_at",
        ),
        CheckConstraint("price > 0", name="ck_price_snapshots_price_positive"),
        CheckConstraint(
            "recorded_at >= 0",
            name="ck_price_snapshots_recorded_at_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    recorded_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
