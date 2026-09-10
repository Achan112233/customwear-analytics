# AI insights and evaluations

## What is implemented

The existing RFM segmentation remains deterministic. OpenAI selects and orders up to two
marketing experiments from a fixed catalog using stored customer metrics. It does not
calculate spend, relabel customers, generate unrestricted prose, or execute campaigns.
Recommendation wording is rendered from reviewed templates. This deliberately constrained
first version makes factual grounding enforceable, at the cost of less creative advice.

`POST /api/v1/customers/{customer_id}/insights` returns the source facts, actions,
recommendation text, snapshot run ID, configured model, and prompt version. The endpoint
uses the customer's latest available profile, which may be older than the latest global
run. Re-run segmentation after importing transactions. Monetary value means total spend
in the snapshot, not spend over an invented rolling window. RFM labels are relative to
the cohort; recommendation eligibility uses explicit absolute thresholds separately.

There is no dashboard integration yet. Use the authenticated API or FastAPI `/docs`.
Results are generated on demand and are not persisted or cached.

## Enable locally

Set these server-side environment variables (or entries in `.env`):

```dotenv
API_KEY=your-own-local-api-access-key
OPENAI_API_KEY=your-openai-api-key
INSIGHTS_MODEL=your-supported-OpenAI-model-ID
```

Restart the API after changing configuration. No default model is assumed: choose one
available to your API account that supports text generation through Responses.
Set INSIGHTS_MODEL to its API model ID, not the product name "ChatGPT". The adapter uses the
[OpenAI Responses API](https://developers.openai.com/api/docs/guides/text).
The OpenAI key must never be added to frontend code or committed to Git.
Requests set store=false and reject incomplete responses, refusals, and missing text.
Setting API_KEY also protects the existing API routes; a browser must use a server-side
proxy/session integration before calling a protected backend. Do not expose this shared
key in a public dashboard bundle.

After importing data and running segmentation, call the endpoint with an `X-API-Key`
header. For example, using locally configured shell variables:

```bash
curl -X POST http://localhost:8000/api/v1/customers/demo-customer/insights \
  -H "X-API-Key: $API_KEY"
```

Replace `demo-customer` with an existing customer ID (URL-encoded if necessary).
Missing application/provider configuration produces 503, a missing customer produces
404, and rejected model output produces 502. Provider failures never silently return
fake AI results. Requests have a 20-second timeout and no automatic paid retries.

Only segment, recency, frequency, monetary value and favorite category are sent to
OpenAI. Customer identifiers and raw orders are excluded. These metrics are still
customer-derived data: confirm the brand's permission and provider privacy terms before
enabling live use. Category values are untrusted input and must not contain personal
information. Keep the endpoint behind authentication, quotas/rate limits and appropriate
customer-level authorization before multi-user production use. The existing shared API
key is not tenant isolation. Campaign execution and consent checks remain human-owned.

## Automated checks

```bash
pytest
python -m evals.run
```

Normal CI makes no model calls. Tests cover schema failures, invented facts, duplicate or
ineligible actions, privacy exclusions, authentication, provider failures, and the evaluation
logic. The offline runner returns `offline-harness-only`: it feeds expected synthetic
responses through the validator. Its passing score is NOT measured OpenAI quality.

The golden dataset in `evals/cases.json` includes new, inactive, loyal, sparse-data,
threshold-boundary and malicious-category cases. Expected primary actions are a small,
explicit business rubric, not empirically proven marketing outcomes. Review them with
the brand owner before treating them as acceptance criteria.

## Live model evaluation (opt-in and paid)

With the provider variables configured, run:

```bash
python -m evals.run --live --repeats 3
```

This makes 18 provider calls on synthetic data. Reports print as JSON to stdout and include
model, prompt version/hash, dataset hash, per-case latency, and:

| Metric | Meaning |
| --- | --- |
| valid_rate | Fraction passing schema, exact-fact and action-eligibility checks |
| usefulness_proxy | Fraction whose first action matches the reviewed expected action |
| consistency | Most frequent ordered action list divided by all attempts; failures count against it |

Save a reviewed live JSON report as `baseline.json`, then compare a new prompt or model:

```bash
python -m evals.run --live --repeats 3 --baseline baseline.json
```

Comparisons require identical dataset, repeat count and mode. Any metric decrease is
flagged. Exit code 1 means any metric is below 100% or a regression exists; code 2 means
configuration/baseline failure. These intentionally strict smoke-test thresholds can be
noisy with only three repetitions. A larger reviewed dataset is needed for robust estimates.
Latency is reported but not gated; token cost is not yet measured. There is no live baseline
committed because no real model evaluation has been performed during implementation.

## Honest project description

The code adds a constrained AI recommendation endpoint and a synthetic evaluation harness.
Offline tests establish software behavior, not real-model accuracy or business usefulness.
Before claiming observed reliability, run the live evaluations, review recommendations
with the brand owner, and record actual results. Campaign lift requires a separate experiment.
