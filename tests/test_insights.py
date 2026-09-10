import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine
from app.models import CustomerSegment, SegmentRun, Transaction
from app.schemas import SegmentCustomer
from app.services import insights
from app.services.segmentation import calculate_metrics
from evals.run import regressions, run


def test_metrics_use_order_counts_and_exact_spend():
    purchases = [
        Transaction(
            customer_id="x",
            order_id=order,
            quantity=quantity,
            unit_price=Decimal(price),
            category="tops",
            purchased_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        for order, quantity, price in [("a", 2, "19.99"), ("a", 1, "5.00"), ("b", 1, "10.00")]
    ]
    metric = calculate_metrics(purchases, datetime(2026, 1, 11, tzinfo=UTC))[0]
    assert metric.monetary_value == Decimal("54.98")
    assert metric.frequency == 2
    assert metric.recency_days == 10


def test_api_success_and_model_rejection(client, monkeypatch, customer):
    monkeypatch.setattr(get_settings(), "api_key", "test-key")
    with Session(engine) as db:
        db.add(SegmentRun(id=7, as_of=datetime.now(UTC), customer_count=1))
        db.flush()
        db.add(CustomerSegment(**customer.model_dump()))
        db.commit()
    url = f"/api/v1/customers/{customer.customer_id}/insights"
    headers = {"X-API-Key": "test-key"}
    monkeypatch.setattr(
        insights,
        "call_model",
        lambda facts: json.dumps(
            {
                "facts": facts,
                "actions": ["welcome"],
            }
        ),
    )
    response = client.post(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["run_id"] == 7
    monkeypatch.setattr(insights, "call_model", lambda facts: "bad output")
    assert client.post(url, headers=headers).status_code == 502

    def unavailable(facts):
        raise insights.InsightsUnavailable("AI provider unavailable")

    monkeypatch.setattr(insights, "call_model", unavailable)
    assert client.post(url, headers=headers).status_code == 503


def test_provider_timeout_and_truncation(customer, monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "secret")
    monkeypatch.setattr(get_settings(), "insights_model", "test")

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(insights.httpx, "post", timeout)
    with pytest.raises(insights.InsightsUnavailable):
        insights.generate_insight(customer)
    monkeypatch.setattr(
        insights.httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.anthropic.com"),
            json={"stop_reason": "max_tokens", "content": []},
        ),
    )
    with pytest.raises(insights.InvalidInsight):
        insights.generate_insight(customer)


@pytest.fixture
def customer():
    return SegmentCustomer(
        customer_id="private@example.com",
        run_id=7,
        segment="New Customers",
        recency_days=2,
        frequency=1,
        monetary_value="40.00",
        favorite_category="tops",
    )


def test_grounded_output_and_privacy(customer, monkeypatch):
    def model(facts):
        assert "private@example.com" not in json.dumps(facts)
        assert "run_id" not in facts
        return json.dumps({"facts": facts, "actions": ["welcome"]})

    monkeypatch.setattr(insights, "call_model", model)
    result = insights.generate_insight(customer)
    assert result.facts["monetary_value"] == "40.00"
    assert result.run_id == 7
    assert result.recommendations == [insights.ACTIONS["welcome"]]


@pytest.mark.parametrize(
    "field,value",
    [
        ("monetary_value", "999.00"),
        ("frequency", True),
        ("segment", "Champions"),
        ("favorite_category", "shoes"),
    ],
)
def test_rejects_fabricated_facts(customer, field, value):
    facts = insights.facts_for(customer)
    raw = json.dumps({"facts": {**facts, field: value}, "actions": ["welcome"]})
    with pytest.raises(insights.InvalidInsight):
        insights.validate_selection(raw, facts)


@pytest.mark.parametrize(
    "actions",
    [
        [],
        ["loyalty"],
        ["reengage"],
        ["welcome", "welcome"],
        ["invented"],
        ["welcome", "category", "learn_more"],
    ],
)
def test_rejects_bad_actions(customer, actions):
    facts = insights.facts_for(customer)
    with pytest.raises(insights.InvalidInsight):
        insights.validate_selection(json.dumps({"facts": facts, "actions": actions}), facts)


@pytest.mark.parametrize("raw", ["not json", "{}", "```json\n{}\n```"])
def test_rejects_malformed_output(customer, raw):
    with pytest.raises(insights.InvalidInsight):
        insights.validate_selection(raw, insights.facts_for(customer))


def test_rejects_free_text_claims(customer):
    facts = insights.facts_for(customer)
    with pytest.raises(insights.InvalidInsight):
        insights.validate_selection(
            json.dumps({"facts": facts, "actions": ["welcome"], "claim": "Revenue will double"}),
            facts,
        )


def test_provider_request(customer, monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(get_settings(), "insights_model", "test-model")
    facts = insights.facts_for(customer)

    def post(url, **kwargs):
        assert url == "https://api.anthropic.com/v1/messages"
        assert kwargs["timeout"] == 20
        assert kwargs["json"]["model"] == "test-model"
        assert customer.customer_id not in json.dumps(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "stop_reason": "end_turn",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "facts": facts,
                                "actions": ["welcome"],
                            }
                        ),
                    }
                ],
            },
        )

    monkeypatch.setattr(insights.httpx, "post", post)
    assert insights.generate_insight(customer).actions == ["welcome"]


@pytest.mark.parametrize("code", [401, 429, 500])
def test_provider_failure_is_sanitized(customer, monkeypatch, code):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "secret")
    monkeypatch.setattr(get_settings(), "insights_model", "test")
    monkeypatch.setattr(
        insights.httpx,
        "post",
        lambda *a, **k: httpx.Response(
            code, request=httpx.Request("POST", "https://api.anthropic.com"), text="secret"
        ),
    )
    with pytest.raises(insights.InsightsUnavailable, match="AI provider unavailable"):
        insights.generate_insight(customer)


def test_missing_configuration(customer, monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    with pytest.raises(insights.InsightsUnavailable):
        insights.generate_insight(customer)


def test_api_requires_key(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", None)
    assert client.post("/api/v1/customers/x/insights").status_code == 503
    monkeypatch.setattr(get_settings(), "api_key", "test-key")
    assert client.post("/api/v1/customers/x/insights").status_code == 401
    assert (
        client.post("/api/v1/customers/x/insights", headers={"X-API-Key": "test-key"}).status_code
        == 404
    )


def test_harness_and_regression_detection():
    baseline = run()
    assert baseline["mode"] == "offline-harness-only"
    assert all(
        c["valid_rate"] == c["usefulness_proxy"] == c["consistency"] == 1 for c in baseline["cases"]
    )
    changed = json.loads(json.dumps(baseline))
    changed["cases"][0]["consistency"] = 0.5
    assert regressions(changed, baseline) == ["new: consistency decreased"]
    changed["mode"] = "live"
    with pytest.raises(ValueError):
        regressions(changed, baseline)


def test_live_harness_detects_wrong_and_unstable_choices(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", "test")
    monkeypatch.setattr(get_settings(), "insights_model", "test")
    calls = 0

    def model(facts):
        nonlocal calls
        calls += 1
        return json.dumps(
            {
                "facts": facts,
                "actions": [
                    "learn_more" if calls % 2 else insights.eligible_actions(facts)[-1],
                ],
            }
        )

    monkeypatch.setattr("evals.run.call_model", model)
    report = run(live=True)
    assert report["cases"][0]["usefulness_proxy"] == 0
    assert report["cases"][0]["consistency"] < 1
