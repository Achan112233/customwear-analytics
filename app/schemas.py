from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import JobStatus


class TransactionCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=100)
    customer_id: str = Field(min_length=1, max_length=100)
    order_id: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    purchased_at: datetime


class TransactionRead(TransactionCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BatchTransactions(BaseModel):
    transactions: list[TransactionCreate] = Field(min_length=1, max_length=5000)


class BatchResult(BaseModel):
    inserted: int
    duplicates: int


class SegmentCustomer(BaseModel):
    customer_id: str
    segment: str
    recency_days: int
    frequency: int
    monetary_value: Decimal
    favorite_category: str | None
    run_id: int
    model_config = ConfigDict(from_attributes=True)


class CustomerPage(BaseModel):
    items: list[SegmentCustomer]
    total: int
    limit: int
    offset: int


class SegmentCount(BaseModel):
    segment: str
    customer_count: int
    total_value: Decimal


class SegmentSummary(BaseModel):
    run_id: int
    as_of: datetime
    customer_count: int
    segments: list[SegmentCount]


class RunResult(BaseModel):
    run_id: int
    customer_count: int


class JobRead(BaseModel):
    id: str
    status: JobStatus
    error: str | None
    result_run_id: int | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
