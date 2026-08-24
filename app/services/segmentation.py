from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustomerSegment, SegmentRun, Transaction


@dataclass
class CustomerMetrics:
    customer_id: str
    recency_days: int
    frequency: int
    monetary_value: Decimal
    favorite_category: str | None


def _score(values: list[Decimal | int], value: Decimal | int, higher_is_better: bool = True) -> int:
    """Return a stable 1-5 percentile score without requiring a data-science dependency."""
    ordered = sorted(values)
    below_or_equal = sum(item <= value for item in ordered)
    score = min(5, max(1, (below_or_equal * 5 + len(ordered) - 1) // len(ordered)))
    return score if higher_is_better else 6 - score


def _segment(r: int, f: int, m: int) -> str:
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if f >= 4 and m >= 3:
        return "Loyal Customers"
    if m == 5:
        return "Big Spenders"
    if r <= 2 and (f >= 3 or m >= 3):
        return "At Risk"
    if r >= 4 and f >= 2:
        return "Promising"
    if r >= 4 and f == 1:
        return "New Customers"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Needs Attention"


def calculate_metrics(transactions: list[Transaction], as_of: datetime) -> list[CustomerMetrics]:
    by_customer: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        by_customer[transaction.customer_id].append(transaction)

    metrics: list[CustomerMetrics] = []
    for customer_id, purchases in by_customer.items():
        last_purchase = max(item.purchased_at for item in purchases)
        if last_purchase.tzinfo is None:
            last_purchase = last_purchase.replace(tzinfo=UTC)
        order_count = len({item.order_id for item in purchases})
        total = sum((item.unit_price * item.quantity for item in purchases), start=Decimal("0"))
        category = Counter(item.category for item in purchases).most_common(1)[0][0]
        metrics.append(
            CustomerMetrics(
                customer_id=customer_id,
                recency_days=max(0, (as_of - last_purchase).days),
                frequency=order_count,
                monetary_value=total,
                favorite_category=category,
            )
        )
    return metrics


def run_segmentation(db: Session, as_of: datetime | None = None) -> SegmentRun:
    as_of = as_of or datetime.now(UTC)
    transactions = list(db.scalars(select(Transaction).where(Transaction.purchased_at <= as_of)))
    metrics = calculate_metrics(transactions, as_of)
    run = SegmentRun(as_of=as_of, customer_count=len(metrics))
    db.add(run)
    db.flush()

    recencies = [item.recency_days for item in metrics]
    frequencies = [item.frequency for item in metrics]
    values = [item.monetary_value for item in metrics]
    for item in metrics:
        r = _score(recencies, item.recency_days, higher_is_better=False)
        f = _score(frequencies, item.frequency)
        m = _score(values, item.monetary_value)
        db.add(
            CustomerSegment(
                run_id=run.id,
                customer_id=item.customer_id,
                segment=_segment(r, f, m),
                recency_days=item.recency_days,
                frequency=item.frequency,
                monetary_value=item.monetary_value,
                favorite_category=item.favorite_category,
            )
        )
    db.commit()
    db.refresh(run)
    return run
