from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis import Redis
from rq import Queue
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AnalyticsJob, CustomerSegment, JobStatus, SegmentRun, Transaction
from app.schemas import (
    BatchResult,
    BatchTransactions,
    CustomerPage,
    JobRead,
    RunResult,
    SegmentCount,
    SegmentCustomer,
    SegmentSummary,
    TransactionCreate,
    TransactionRead,
)
from app.security import require_api_key
from app.services.insights import (
    Insight,
    InsightsUnavailable,
    InvalidInsight,
    generate_insight,
)
from app.services.segmentation import run_segmentation
from app.tasks import execute_segmentation

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
Database = Annotated[Session, Depends(get_db)]


@router.post("/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Database) -> Transaction:
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="external_id already exists") from exc
    db.refresh(transaction)
    return transaction


@router.post("/transactions/batch", response_model=BatchResult, status_code=status.HTTP_201_CREATED)
def create_transaction_batch(payload: BatchTransactions, db: Database) -> BatchResult:
    ids = [item.external_id for item in payload.transactions]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="Batch contains duplicate external_id values")
    existing = set(
        db.scalars(select(Transaction.external_id).where(Transaction.external_id.in_(ids)))
    )
    new_items = [
        Transaction(**item.model_dump())
        for item in payload.transactions
        if item.external_id not in existing
    ]
    db.add_all(new_items)
    db.commit()
    return BatchResult(inserted=len(new_items), duplicates=len(existing))


@router.post(
    "/segments/run",
    response_model=RunResult | JobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_segment_run(
    db: Database, background: Annotated[bool, Query()] = False
) -> RunResult | AnalyticsJob:
    if not background:
        run = run_segmentation(db)
        return RunResult(run_id=run.id, customer_count=run.customer_count)

    job = AnalyticsJob(id=str(uuid4()))
    db.add(job)
    db.commit()
    db.refresh(job)
    settings = get_settings()
    try:
        Queue(settings.segmentation_queue, connection=Redis.from_url(settings.redis_url)).enqueue(
            execute_segmentation, job.id, job_id=job.id
        )
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = f"Queue unavailable: {exc}"[:500]
        db.commit()
        raise HTTPException(status_code=503, detail="Segmentation queue unavailable") from exc
    return job


@router.get("/segments/summary", response_model=SegmentSummary)
def get_segment_summary(db: Database) -> SegmentSummary:
    run = db.scalar(select(SegmentRun).order_by(SegmentRun.id.desc()).limit(1))
    if run is None:
        raise HTTPException(status_code=404, detail="No segmentation run exists")
    rows = db.execute(
        select(
            CustomerSegment.segment,
            func.count(CustomerSegment.id),
            func.sum(CustomerSegment.monetary_value),
        )
        .where(CustomerSegment.run_id == run.id)
        .group_by(CustomerSegment.segment)
        .order_by(func.count(CustomerSegment.id).desc())
    ).all()
    return SegmentSummary(
        run_id=run.id,
        as_of=run.as_of,
        customer_count=run.customer_count,
        segments=[
            SegmentCount(segment=name, customer_count=count, total_value=value)
            for name, count, value in rows
        ],
    )


@router.get("/customers", response_model=CustomerPage)
def list_customers(
    db: Database,
    segment: Annotated[str | None, Query(max_length=100)] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CustomerPage:
    run_id = db.scalar(select(SegmentRun.id).order_by(SegmentRun.id.desc()).limit(1))
    if run_id is None:
        return CustomerPage(items=[], total=0, limit=limit, offset=offset)

    filters = [CustomerSegment.run_id == run_id]
    if segment:
        filters.append(CustomerSegment.segment == segment)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                CustomerSegment.customer_id.ilike(pattern),
                CustomerSegment.favorite_category.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count(CustomerSegment.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(CustomerSegment)
            .where(*filters)
            .order_by(CustomerSegment.monetary_value.desc(), CustomerSegment.customer_id)
            .limit(limit)
            .offset(offset)
        )
    )
    return CustomerPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/customers/{customer_id}", response_model=SegmentCustomer)
def get_customer(customer_id: str, db: Database) -> CustomerSegment:
    customer = db.scalar(
        select(CustomerSegment)
        .where(CustomerSegment.customer_id == customer_id)
        .order_by(CustomerSegment.run_id.desc())
        .limit(1)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer has no segment profile")
    return customer


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Database) -> AnalyticsJob:
    job = db.get(AnalyticsJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/customers/{customer_id}/insights", response_model=Insight)
def create_customer_insight(customer_id: str, db: Database) -> Insight:
    # Require authentication even when the rest of the development API is open.
    if not get_settings().api_key:
        raise HTTPException(status_code=503, detail="Configure API_KEY before enabling AI insights")
    customer = SegmentCustomer.model_validate(get_customer(customer_id, db))
    try:
        return generate_insight(customer)
    except InsightsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InvalidInsight as exc:
        raise HTTPException(status_code=502, detail="AI response failed grounding checks") from exc
