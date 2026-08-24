import enum
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_transaction_external_id"),
        Index("ix_transactions_customer_purchased", "customer_id", "purchased_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100))
    customer_id: Mapped[str] = mapped_column(String(100), index=True)
    order_id: Mapped[str] = mapped_column(String(100), index=True)
    sku: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SegmentRun(Base):
    __tablename__ = "segment_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    customer_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    customers: Mapped[list["CustomerSegment"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CustomerSegment(Base):
    __tablename__ = "customer_segments"
    __table_args__ = (
        UniqueConstraint("run_id", "customer_id", name="uq_run_customer"),
        Index("ix_customer_segments_customer_run", "customer_id", "run_id"),
        Index("ix_customer_segments_run_segment", "run_id", "segment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("segment_runs.id", ondelete="CASCADE"))
    customer_id: Mapped[str] = mapped_column(String(100))
    segment: Mapped[str] = mapped_column(String(50))
    recency_days: Mapped[int] = mapped_column(Integer)
    frequency: Mapped[int] = mapped_column(Integer)
    monetary_value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    favorite_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    run: Mapped[SegmentRun] = relationship(back_populates="customers")


class AnalyticsJob(Base):
    __tablename__ = "analytics_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_run_id: Mapped[int | None] = mapped_column(ForeignKey("segment_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
