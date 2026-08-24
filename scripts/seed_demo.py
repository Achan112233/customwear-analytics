from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Transaction

CUSTOMERS = {
    "ava@example.com": [(1, "outerwear", "180"), (8, "tops", "75"), (20, "tops", "65")],
    "liam@example.com": [(4, "footwear", "140")],
    "mia@example.com": [(120, "accessories", "40"), (190, "tops", "55")],
    "noah@example.com": [(250, "bottoms", "90")],
}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    now = datetime.now(UTC)
    with SessionLocal() as db:
        index = 0
        for customer_id, purchases in CUSTOMERS.items():
            for days_ago, category, price in purchases:
                index += 1
                external_id = f"demo-{index}"
                exists = db.scalar(
                    select(Transaction.id).where(Transaction.external_id == external_id)
                )
                if not exists:
                    db.add(
                        Transaction(
                            external_id=external_id,
                            customer_id=customer_id,
                            order_id=f"order-{index}",
                            sku=f"{category[:3].upper()}-{index:03}",
                            category=category,
                            quantity=1,
                            unit_price=Decimal(price),
                            purchased_at=now - timedelta(days=days_ago),
                        )
                    )
        db.commit()
    print(f"Seeded {index} demo transactions")


if __name__ == "__main__":
    main()
