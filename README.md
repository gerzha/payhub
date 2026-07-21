# payhub

A portfolio showcase demonstrating a functional-test framework architecture for an
async order/payment service: pluggable provider adapters, webhook signature
verification, a queue-driven worker, WireMock-style external-call stubbing, and SQS
polling assertions. This is a clean-room implementation — no code, structure, or
naming is derived from any employer's proprietary systems; the domain (`stripe_like`
/ `paypal_like` webhook providers) is a toy stand-in for a real payment integration.

## Architecture

```
                 ┌─────────────┐
  client ──POST──▶   payhub    │──POST /orders──▶ Postgres (orders)
                 │  (FastAPI)  │
                 └──────┬──────┘
                        │ POST /webhooks/{provider}
                        ▼
                 ┌─────────────┐
                 │  inbound    │  (SQS)
                 │   queue     │
                 └──────┬──────┘
                        │ long-poll
                        ▼
                 ┌─────────────┐        ┌───────────────────┐
                 │   worker    │──────▶ │ provider registry │
                 │             │ verify │  stripe_like       │
                 │             │ parse  │  paypal_like       │
                 └──────┬──────┘        └───────────────────┘
                        │ update status
                        ▼
                 ┌─────────────┐
                 │  Postgres   │
                 │  (orders)   │
                 └──────┬──────┘
                        │ publish status_changed
                        ▼
                 ┌─────────────┐
                 │  outbound   │  (SQS)
                 │   queue     │
                 └─────────────┘
```

Order lifecycle: `PENDING → PROCESSING → PAID | FAILED`, with `HOLD` reached from
`PROCESSING` if the worker exhausts its retry budget on transient errors.

## Quickstart

```bash
docker compose up -d --build
pip install -e tests/functional
pytest tests/functional/tests -v
```

Unit tests (no Docker required):

```bash
uv sync --extra dev
uv run pytest tests/unit -v
```

## Why this structure

- **Separate test-framework project** (`tests/functional/` has its own
  `pyproject.toml`) — the test suite defines its own `models.py` and never imports
  production code. It validates the wire contract, not implementation details.
- **Pluggable provider registry** (`src/providers/registry.py`) — adding a third
  provider means adding one module and one registry entry; nothing else in the
  codebase changes.
- **Idempotency / duplicate-webhook handling** — the worker treats an order already
  in a terminal status (`PAID`/`FAILED`) as a signal to drop a re-delivered webhook,
  rather than reprocessing it.
- **Retry/backoff tested at the right layer** — unit-tested against the worker's
  retry logic directly (`tests/unit/test_order_worker.py`), not via a brittle
  infra-level functional test that would require forcing real Postgres/SQS outages
  in CI.

## Test inventory

| File | Covers |
|---|---|
| `tests/unit/test_stripe_like_provider.py` | stripe_like verifier signature checks, parser payload → `NormalizedWebhook` |
| `tests/unit/test_paypal_like_provider.py` | paypal_like verifier (body-embedded signature), parser payload → `NormalizedWebhook` |
| `tests/unit/test_order_worker.py` | retry-count increment, requeue vs. `HOLD` transition after budget exhaustion |
| `tests/functional/tests/test_orders.py` | `/ping` smoke check, order creation, 404 on missing order |
| `tests/functional/tests/test_webhooks_stripe_like.py` | end-to-end webhook → order status transition, invalid signature, duplicate-webhook idempotency |
| `tests/functional/tests/test_webhooks_paypal_like.py` | same coverage as above, proving the adapter abstraction handles a structurally different provider |
| `tests/functional/tests/test_retries.py` | unknown-provider 404, webhook for a nonexistent order is dropped without error |

## Non-goals

No Kubernetes/Helm, no more than two providers, no outbound provider API calls (this
domain is webhook-push-only), no auth on the API, and no fault-injection plumbing in
production code — see `IMPLEMENTATION_PLAN.md` for the full rationale.
