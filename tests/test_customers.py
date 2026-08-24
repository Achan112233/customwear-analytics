from datetime import UTC, datetime, timedelta


def transaction(external_id: str, customer: str, days_ago: int, price: str) -> dict:
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


def test_list_customers_returns_latest_profiles(client):
    payload = {
        "transactions": [
            transaction("list-1", "alex@example.com", 2, "120.00"),
            transaction("list-2", "blair@example.com", 20, "45.00"),
        ]
    }
    assert client.post("/api/v1/transactions/batch", json=payload).status_code == 201
    assert client.post("/api/v1/segments/run").status_code == 202

    response = client.get("/api/v1/customers?limit=1")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["customer_id"] == "alex@example.com"

    searched = client.get("/api/v1/customers?search=blair")
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["customer_id"] == "blair@example.com"


def test_list_customers_before_first_run_is_empty(client):
    response = client.get("/api/v1/customers")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}
