"""Create analytics tables.

Revision ID: 20260824_01
Revises:
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260824_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_status = postgresql.ENUM(
    "queued", "running", "completed", "failed", name="jobstatus", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("order_id", sa.String(length=100), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id", name="uq_transaction_external_id"),
    )
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])
    op.create_index("ix_transactions_order_id", "transactions", ["order_id"])
    op.create_index("ix_transactions_category", "transactions", ["category"])
    op.create_index("ix_transactions_purchased_at", "transactions", ["purchased_at"])
    op.create_index(
        "ix_transactions_customer_purchased", "transactions", ["customer_id", "purchased_at"]
    )

    op.create_table(
        "segment_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "customer_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("segment", sa.String(length=50), nullable=False),
        sa.Column("recency_days", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("monetary_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("favorite_category", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["segment_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "customer_id", name="uq_run_customer"),
    )
    op.create_index(
        "ix_customer_segments_customer_run", "customer_segments", ["customer_id", "run_id"]
    )
    op.create_index("ix_customer_segments_run_segment", "customer_segments", ["run_id", "segment"])

    job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "analytics_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", job_status, nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("result_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["result_run_id"], ["segment_runs.id"]),
    )


def downgrade() -> None:
    op.drop_table("analytics_jobs")
    job_status.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_customer_segments_run_segment", table_name="customer_segments")
    op.drop_index("ix_customer_segments_customer_run", table_name="customer_segments")
    op.drop_table("customer_segments")
    op.drop_table("segment_runs")
    op.drop_index("ix_transactions_customer_purchased", table_name="transactions")
    op.drop_index("ix_transactions_purchased_at", table_name="transactions")
    op.drop_index("ix_transactions_category", table_name="transactions")
    op.drop_index("ix_transactions_order_id", table_name="transactions")
    op.drop_index("ix_transactions_customer_id", table_name="transactions")
    op.drop_table("transactions")
