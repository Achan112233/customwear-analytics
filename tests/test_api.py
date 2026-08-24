from datetime import UTC, datetime, timedelta


def transaction(external_id: str, customer: str, days_ago: int, price: str = "50.00") -> dict:
    return {
        "external_id": external_id,
        "customer_id": customer,
        "order_id": external_id,
        "sku": "TEE-001",
        "category": "tops",
        "quantity": 1,
        "unit_price": price,
        "purchased_at": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
    }


def test_ingest_run_and_query_customer(client):
    payload = {
        "transactions": [
            transaction("tx-1", "customer-a", 1, "120.00"),
            transaction("tx-2", "customer-a", 3, "80.00"),
            transaction("tx-3", "customer-b", 200, "20.00"),
        ]
    }
    response = client.post("/api/v1/transactions/batch", json=payload)
    assert response.status_code == 201
    assert response.json() == {"inserted": 3, "duplicates": 0}

    run = client.post("/api/v1/segments/run")
    assert run.status_code == 202
    assert run.json()["customer_count"] == 2

    profile = client.get("/api/v1/customers/customer-a")
    assert profile.status_code == 200
    assert profile.json()["frequency"] == 2
    assert profile.json()["monetary_value"] == "200.00"

    summary = client.get("/api/v1/segments/summary")
    assert summary.status_code == 200
    assert summary.json()["customer_count"] == 2


def test_batch_ingestion_is_idempotent(client):
    payload = {"transactions": [transaction("tx-1", "customer-a", 1)]}
    assert client.post("/api/v1/transactions/batch", json=payload).json()["inserted"] == 1
    result = client.post("/api/v1/transactions/batch", json=payload)
    assert result.json() == {"inserted": 0, "duplicates": 1}


def test_duplicate_single_transaction_returns_conflict(client):
    payload = transaction("tx-1", "customer-a", 1)
    assert client.post("/api/v1/transactions", json=payload).status_code == 201
    assert client.post("/api/v1/transactions", json=payload).status_code == 409
