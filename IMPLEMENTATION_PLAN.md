# payhub — Implementation Plan

## Purpose

This is a **portfolio showcase repository** for a Senior Automation QA / SDET. It
demonstrates a real-world functional-test framework architecture (order lifecycle,
external-provider webhooks, async worker + queue, WireMock-style stubbing, SQS
polling) on a small, self-contained payment/order service — **without** any
proprietary code, without Kubernetes/Helm, and without a persistent deployment.

The design mirrors the architecture of a production payment-processing service
(`pay`) that handles purchase orders across app stores, but everything here is a
clean-room reimplementation using only open-source packages: a toy domain
(`stripe_like` / `paypal_like` webhook providers instead of real app stores), FastAPI
instead of a proprietary aiohttp toolkit, and hand-written thin QA helpers instead of
internal `qatoolset`/`qawiremock` packages.

**Everything runs via `docker compose` locally and in GitHub Actions CI.** No cloud
deployment, no Helm charts, no persistent environment — each CI run spins the stack
up, runs tests, tears it down.

Read this whole document before writing any code. Follow the file structure exactly
— it dictates import paths used throughout the plan. Work top-to-bottom through the
phases; each phase should result in a working, testable increment.

---

## Domain Model

`payhub` is an order/payment service. A client creates an **order** for a product
against a chosen payment **provider**. The provider (emulated via WireMock)
asynchronously sends a **webhook** reporting payment success/failure. A background
**worker** consumes the webhook event from a queue, verifies+parses it through a
**pluggable provider adapter**, updates the order status, and publishes a
status-change event to a second queue.

### Order lifecycle

```
PENDING → PROCESSING → PAID
                     → FAILED
PROCESSING → HOLD        (after retry budget exhausted on transient provider errors)
```

- `PENDING` — order created, awaiting webhook.
- `PROCESSING` — webhook received, being verified/parsed.
- `PAID` — payment confirmed by provider.
- `FAILED` — provider explicitly rejected the payment, or signature verification failed.
- `HOLD` — provider was unreachable/erroring across all retry attempts; needs manual reconciliation.

### Providers

Two independent, pluggable provider adapters — this is the architectural centerpiece,
mirroring a per-store verifier/parser registry:

- `stripe_like` — signs webhook body with HMAC-SHA256 in a `X-Signature` header.
- `paypal_like` — signs webhook body with HMAC-SHA256 but embeds the signature
  inside the JSON body as a `signature` field, and uses a different payload shape.

Each provider has:
- a **verifier**: validates the signature against a shared secret, raises on mismatch.
- a **parser**: normalizes the provider-specific payload into a common
  `NormalizedWebhook` model (`order_id`, `provider_transaction_id`, `status`,
  `amount`, `currency`).

Both are registered in a `registry.py` keyed by provider name, exactly like a
verifier/parser registry pattern — adding a third provider means adding one module
and one registry entry, touching nothing else.

---

## Repository Structure

Create this exact structure at the repo root (`~/PycharmProjects/payhub/`):

```
payhub/
├── src/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory, mounts routers
│   ├── settings.py                   # Pydantic BaseSettings, env-driven
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                 # SQLAlchemy ORM: Order
│   │   ├── session.py                # async engine + get_session dependency
│   │   └── migrations/
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── 0001_create_orders.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── order.py                  # OrderCreateRequest, OrderResponse
│   │   └── webhook.py                # NormalizedWebhook, raw payload types
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── orders.py             # POST /orders, GET /orders/{id}
│   │       └── webhooks.py           # POST /webhooks/{provider}
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                   # Verifier / Parser Protocols
│   │   ├── registry.py               # PROVIDERS: dict[str, ProviderAdapter]
│   │   ├── stripe_like/
│   │   │   ├── __init__.py
│   │   │   ├── verifier.py
│   │   │   └── parser.py
│   │   └── paypal_like/
│   │       ├── __init__.py
│   │       ├── verifier.py
│   │       └── parser.py
│   ├── queue/
│   │   ├── __init__.py
│   │   └── sqs.py                    # thin aioboto3 wrapper: send/receive/delete
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── process_webhook.py        # verify → parse → update status → publish
│   └── worker/
│       ├── __init__.py
│       └── order_worker.py           # polls inbound queue, runs pipeline, CLI entrypoint
├── tests/
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_stripe_like_provider.py
│   │   └── test_paypal_like_provider.py
│   └── functional/                   # SEPARATE project, own pyproject.toml
│       ├── pyproject.toml
│       ├── clients.py
│       ├── api_wrappers.py
│       ├── models.py
│       ├── constants.py
│       ├── settings.py
│       ├── mocks/
│       │   ├── __init__.py
│       │   ├── stripe_like_processing.py
│       │   └── paypal_like_processing.py
│       ├── qa_toolkit/
│       │   ├── __init__.py
│       │   ├── base_http_client.py
│       │   ├── wiremock_client.py
│       │   ├── sqs_client.py
│       │   └── waiter.py
│       └── tests/
│           ├── __init__.py
│           ├── conftest.py
│           ├── test_orders.py
│           ├── test_webhooks_stripe_like.py
│           ├── test_webhooks_paypal_like.py
│           └── test_retries.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                    # app project (uv or pdm, your choice — see below)
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
└── README.md
```

---

## Phase 1 — Service Skeleton & Settings

1. Init a Python 3.12 project at repo root (`pyproject.toml`). Use `uv` if available,
   otherwise plain `pip` + `requirements.txt` — pick whichever tool is already
   installed in the target environment; don't add a new package manager dependency
   just for this. Runtime deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`,
   `asyncpg`, `alembic`, `pydantic`, `pydantic-settings`, `aioboto3`, `httpx`
   (for provider calls, not strictly required if providers are webhook-only push).
2. `src/settings.py`: `Settings(BaseSettings)` with `database_url`, `sqs_endpoint_url`,
   `inbound_queue_name`, `outbound_queue_name`, `stripe_like_secret`,
   `paypal_like_secret`, `max_provider_retries` (default 5), `retry_backoff_seconds`
   (default 1.0). Read from env with prefix `PAYHUB_`.
3. `src/main.py`: FastAPI app, includes `api/v1/orders.py` and `api/v1/webhooks.py`
   routers, adds a `/ping` health endpoint returning `{"status": "pong"}` (mirrors the
   `pay` `ping` convention used by functional tests as a smoke check).

## Phase 2 — Data Layer

1. `src/db/models.py`: SQLAlchemy `Order` model — `id` (int, PK, autoincrement),
   `product_id` (str), `provider` (str), `status` (str enum: PENDING/PROCESSING/
   PAID/FAILED/HOLD), `provider_transaction_id` (str, nullable), `amount` (numeric),
   `currency` (str), `retry_count` (int, default 0), `created_at`, `updated_at`.
2. `src/db/session.py`: async engine from `settings.database_url`, `async_sessionmaker`,
   a FastAPI dependency `get_session()`.
3. Alembic setup (`src/db/migrations/`) with one migration creating the `orders`
   table matching the model above.

## Phase 3 — Schemas

1. `src/schemas/order.py`:
   - `OrderCreateRequest`: `product_id: str`, `provider: Literal["stripe_like",
     "paypal_like"]`, `amount: Decimal`, `currency: str = "USD"`.
   - `OrderResponse`: mirrors the `Order` model fields, `model_config =
     ConfigDict(from_attributes=True)`.
2. `src/schemas/webhook.py`:
   - `NormalizedWebhook`: `order_id: int`, `provider_transaction_id: str`,
     `status: Literal["paid", "failed"]`, `amount: Decimal`, `currency: str`.

## Phase 4 — Provider Adapters (the architectural centerpiece)

1. `src/providers/base.py`: two `Protocol`s —
   ```python
   class Verifier(Protocol):
       def verify(self, raw_body: bytes, headers: Mapping[str, str]) -> None: ...
       # raises SignatureVerificationError on failure

   class Parser(Protocol):
       def parse(self, raw_body: bytes) -> NormalizedWebhook: ...
   ```
   Define `SignatureVerificationError(Exception)` here too.

2. `src/providers/stripe_like/verifier.py`: reads `X-Signature` header, computes
   `hmac.new(secret, raw_body, sha256).hexdigest()`, compares with
   `hmac.compare_digest`. Raises `SignatureVerificationError` on mismatch or missing
   header.

3. `src/providers/stripe_like/parser.py`: expects JSON body shaped like
   ```json
   {"order_id": 123, "transaction_id": "tx_abc", "event": "payment_succeeded", "amount": "19.99", "currency": "USD"}
   ```
   `event` maps `payment_succeeded → paid`, `payment_failed → failed`. Returns
   `NormalizedWebhook`.

4. `src/providers/paypal_like/verifier.py`: reads `signature` field **from the JSON
   body itself** (not a header) and validates HMAC over the body with that field
   stripped out before hashing. This deliberately differs from stripe_like to prove
   the adapter pattern handles heterogeneous auth schemes.

5. `src/providers/paypal_like/parser.py`: expects body shaped like
   ```json
   {"resource": {"order_id": 123, "txn_id": "PAY-xyz", "state": "COMPLETED", "value": "19.99", "currency_code": "USD"}, "signature": "..."}
   ```
   `state` maps `COMPLETED → paid`, `DENIED → failed`.

6. `src/providers/registry.py`:
   ```python
   @dataclass(frozen=True)
   class ProviderAdapter:
       verifier: Verifier
       parser: Parser

   PROVIDERS: dict[str, ProviderAdapter] = {
       "stripe_like": ProviderAdapter(StripeLikeVerifier(...), StripeLikeParser()),
       "paypal_like": ProviderAdapter(PaypalLikeVerifier(...), PaypalLikeParser()),
   }
   ```
   `process_webhook.py` looks up by provider name; unknown provider → 404 at the API
   layer, before it ever reaches the queue.

## Phase 5 — API Endpoints

1. `src/api/v1/orders.py`:
   - `POST /orders` — validates `OrderCreateRequest`, inserts `Order` with
     `status=PENDING`, returns `201` + `OrderResponse`.
   - `GET /orders/{order_id}` — 404 if missing, else `200` + `OrderResponse`.
2. `src/api/v1/webhooks.py`:
   - `POST /webhooks/{provider}` — looks up `provider` in `PROVIDERS` (404 if
     unknown), reads the raw body, pushes `{provider, raw_body (base64), headers}`
     onto the **inbound SQS queue**, returns `202` immediately. Signature
     verification happens in the worker, not in the HTTP handler — this mirrors an
     async processing pipeline and lets the functional tests assert on retry/backoff
     behavior that only the worker owns.

## Phase 6 — Queue Wrapper & Worker

1. `src/queue/sqs.py`: thin `aioboto3`-based class `SQSQueue` with `send(body: dict)`,
   `receive(max_messages, wait_seconds)`, `delete(receipt_handle)`. Endpoint URL from
   settings (LocalStack in dev/CI).
2. `src/pipeline/process_webhook.py`: `async def process_webhook_message(message: dict,
   session: AsyncSession, outbound_queue: SQSQueue) -> None`:
   - look up provider adapter in registry
   - `verifier.verify(raw_body, headers)` — on `SignatureVerificationError`, load the
     order (if `order_id` is parseable) and set `status=FAILED`, publish a
     `status_changed` event, return (do not raise — this is an expected outcome, not
     a worker crash)
   - `parser.parse(raw_body)` → `NormalizedWebhook`
   - load `Order` by `normalized.order_id`; if missing, log and drop the message
     (idempotency: if `order.status` is already `PAID` or `FAILED`, drop — this is
     the duplicate-webhook guard)
   - update `order.status` from `normalized.status` (`paid`/`failed` →
     `PAID`/`FAILED`), `order.provider_transaction_id = normalized.provider_transaction_id`
   - publish `{"order_id": order.id, "status": order.status, "provider":
     order.provider}` to the **outbound status queue**
3. `src/worker/order_worker.py`: `async def run() -> None` — infinite loop: receive
   from inbound queue (long-poll), for each message call
   `process_webhook_message`; wrap in try/except — on transient failure (e.g. DB
   connection error, not signature/parse errors which are terminal) increment
   `retry_count`; if `retry_count >= settings.max_provider_retries`, set
   `status=HOLD`, publish status event, and stop retrying that message; otherwise
   re-queue with an exponential backoff delay (`retry_backoff_seconds * 2 **
   retry_count`, use SQS `DelaySeconds` or a local asyncio sleep before re-send).
   Expose a `if __name__ == "__main__": asyncio.run(run())` entrypoint.

## Phase 7 — Docker & Compose

1. `Dockerfile`: multi-stage, `python:3.12-slim` base, installs deps, copies `src/`,
   `CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Add a
   second stage/target (or reuse the same image with a different `command:` in
   compose) for the worker — no need for a separate Dockerfile, just override
   `command: python -m src.worker.order_worker` in compose.
2. `docker-compose.yml` services:
   - `postgres` — `postgres:16-alpine`, exposes 5432, healthcheck via `pg_isready`.
   - `localstack` — `localstack/localstack`, `SERVICES=sqs`, exposes 4566.
   - `wiremock` — `wiremock/wiremock`, exposes 8080, used by functional tests as the
     "external provider" endpoint if you choose to have the app call providers
     outbound too (optional — see Phase 4 note: this MVP is webhook-push-only, so
     wiremock is primarily driven directly by the functional tests to originate
     webhook calls against `app`, not the other way around). Keep it in
     compose anyway since functional tests reference `MOCK_HOST`/`MOCK_PORT` for
     consistency with the `pay` pattern, and it's needed if you later add outbound
     provider verification calls.
   - `app` — builds from `Dockerfile`, depends_on postgres+localstack (healthy),
     runs migrations on startup (`command: sh -c "alembic upgrade head && uvicorn ..."`),
     env vars from `.env.example` / compose `environment:` block.
   - `worker` — same image, `command: python -m src.worker.order_worker`,
     depends_on same as `app`.
3. `.env.example`: documents every `PAYHUB_*` var with a working default for local
   compose use.

## Phase 8 — Unit Tests (`tests/unit/`)

Use `pytest`. Cover the pure logic that doesn't need the full stack:
- `test_stripe_like_provider.py`: verifier accepts a correctly-signed body, rejects
  a tampered body and a missing header; parser round-trips a valid payload into
  `NormalizedWebhook` for both `payment_succeeded` and `payment_failed`.
- `test_paypal_like_provider.py`: same shape, adapted to the body-embedded signature
  and `COMPLETED`/`DENIED` states.

No DB, no network — these run in plain `pytest` with no fixtures beyond simple
factories.

## Phase 9 — Functional Test Framework (`tests/functional/`)

This is a **separate Python project** (own `pyproject.toml`, own virtualenv),
exactly mirroring the layered structure of a mature functional-test suite. It talks
to the `app` service over HTTP, drives WireMock's admin API to originate webhook
calls, and polls SQS to assert on the outbound status queue.

### `tests/functional/pyproject.toml`
Deps: `pytest`, `requests`, `pydantic`, `boto3`. No proprietary packages — see
`qa_toolkit/` below for what replaces them.

### `tests/functional/qa_toolkit/` — open-source replacements for internal QA packages

This directory exists specifically to demonstrate what a private `qatoolset`/
`qawiremock`-style internal package looks like when reimplemented on nothing but
`requests`/`boto3`. Keep each file under ~60 lines.

1. `base_http_client.py`:
   ```python
   class BaseHttpClient:
       def __init__(self, scheme: str, host: str, port: int, version: str = "v1"):
           self.base_url = f"{scheme}://{host}:{port}/api/{version}"
           self.session = requests.Session()

       def build_url(self, endpoint: str, entity_id=None, action=None) -> str:
           parts = [self.base_url, endpoint]
           if entity_id is not None:
               parts.append(str(entity_id))
           if action is not None:
               parts.append(action)
           return "/".join(parts)

       def get(self, url, params=None, wrapper=None): ...
       def post(self, url, json=None, data=None, headers=None, wrapper=None): ...
       # wrapper: Callable[[Response], Any] applied to the raw response
   ```
2. `wiremock_client.py`: `WiremockClient(host, port)` with `create_stub(request_matcher,
   response)`, `delete_stub(stub_id)`, `clear_history()`, `find_requests(url_pattern,
   method)` — all implemented as plain `requests` calls against WireMock's
   `__admin` REST API (`POST /__admin/mappings`, `GET /__admin/requests`, etc. — this
   is public WireMock API, safe to hit directly with `requests`, no client library
   needed).
3. `sqs_client.py`: thin `boto3.client("sqs", endpoint_url=...)` wrapper —
   `send_message`, `receive_messages`, `purge_queue`, `delete_message`.
4. `waiter.py`: `smart_wait(function, expected_result, timeout=10, interval=0.5)` —
   polls `function()` until `expected_result(result)` is truthy or timeout, raising
   `TimeoutError` with the last seen value on failure.

### `tests/functional/models.py`
Pydantic models: `OrderCreateRequest`, `OrderResponse` (mirrors `src/schemas/order.py`
but is intentionally a separate definition — the test suite must not import
production code, it validates the wire contract independently), `StatusEventMessage`
(for parsing outbound-queue SQS bodies).

### `tests/functional/constants.py`
`class Provider(StrEnum): STRIPE_LIKE = "stripe_like"; PAYPAL_LIKE = "paypal_like"`,
`class OrderStatus(StrEnum): PENDING = ...; PROCESSING = ...; PAID = ...; FAILED =
...; HOLD = ...`, `class Routes(StrEnum): ORDERS = "orders"; WEBHOOKS = "webhooks"`.

### `tests/functional/settings.py`
Env-driven host/port constants for `app` (`PAYHUB_HOST`/`PAYHUB_PORT`, default
`localhost:8000` for local runs against compose), `wiremock` (unused unless outbound
calls are added later, keep for parity), `localstack`
(`http://localhost:4566` default), queue names.

### `tests/functional/mocks/`
`stripe_like_processing.py`: `def stripe_like_webhook_payload(order_id, status="payment_succeeded", amount="19.99", currency="USD") -> dict` and
`def sign_stripe_like(body: bytes, secret: str) -> str` (HMAC helper the tests use to
produce a valid `X-Signature`).
`paypal_like_processing.py`: analogous, producing the nested `resource` shape and a
body-embedded signature.

### `tests/functional/clients.py`
`class PayhubClient(BaseHttpClient)`:
- `create_order(product_id, provider, amount, currency="USD") -> OrderResponse`
- `get_order(order_id) -> OrderResponse`
- `send_webhook(provider, payload: dict, headers: dict | None = None) -> requests.Response`
  (posts directly to `app`'s `/webhooks/{provider}`, not through WireMock — WireMock
  isn't in the call path for this MVP since providers push to `payhub`, they don't
  get called by it; **do not** introduce a WireMock round-trip here, that would be
  fictitious for this domain shape)
- `wait_order_in_status(order_id, status, timeout=10) -> OrderResponse` — uses
  `smart_wait` from `qa_toolkit`.
- `ping() -> dict`

### `tests/functional/api_wrappers.py`
`class PayhubWrappers`: `wrap_order(response) -> OrderResponse` (asserts `201`/`200`,
parses `.json()`), `wrap_raw(response) -> requests.Response` (passthrough, asserts
nothing — used for webhook POSTs where the test itself checks status code).

### `tests/functional/tests/conftest.py`
Fixtures:
- `payhub_client` — `PayhubClient` instance from settings.
- `sqs_client` — `SQSClient` from `qa_toolkit`, auto-purges inbound/outbound queues
  on teardown via `request.addfinalizer`.
- `make_order` — factory fixture: `def _make(provider=Provider.STRIPE_LIKE,
  amount="19.99") -> OrderResponse`, calls `payhub_client.create_order(...)`.

### `tests/functional/tests/test_orders.py`
- `test_ping` — smoke check.
- `test_create_order_returns_pending` — `POST /orders` → `201`, `status == PENDING`.
- `test_get_order_not_found` — `GET /orders/999999` → `404`.

### `tests/functional/tests/test_webhooks_stripe_like.py`
- `test_webhook_payment_succeeded_moves_order_to_paid` — create order, POST signed
  `payment_succeeded` webhook, `wait_order_in_status(..., PAID)`, assert outbound SQS
  has a `status_changed` message with `status=PAID` for that `order_id`.
- `test_webhook_payment_failed_moves_order_to_failed` — same, `payment_failed` → `FAILED`.
- `test_webhook_invalid_signature_leaves_order_pending` — send with a garbage
  signature, assert order stays `PENDING` (worker drops it as `FAILED` per the design
  in Phase 6 — **decide during implementation** whether invalid signature should
  leave the order untouched or flip it to `FAILED`, and make the test assert
  whichever behavior Phase 6 actually implements; the plan text above says `FAILED`,
  keep the test consistent with that).
- `test_duplicate_webhook_is_idempotent` — send the same valid webhook twice, assert
  only one `status_changed` event lands on the outbound queue.

### `tests/functional/tests/test_webhooks_paypal_like.py`
Same four cases, adapted to the paypal_like payload/signature shape — proves the
framework's abstraction (`mocks/paypal_like_processing.py` + same `PayhubClient`
methods) handles a structurally different provider without touching `clients.py`.

### `tests/functional/tests/test_retries.py`
- `test_worker_holds_order_after_retry_budget_exhausted` — this test needs a way to
  force transient failures (e.g. temporarily stop the `postgres` container, or —
  simpler and preferred — add a debug-only fault-injection lever: an env var
  `PAYHUB_FAULT_INJECT_DB_ERROR_COUNT=N` read by the worker that raises a simulated
  transient error the first N times it processes any message, decrementing a
  counter in Redis/Postgres... **this is over-engineering for a portfolio piece.**
  Simplify: instead, test retry/backoff purely at the **unit level**
  (`tests/unit/test_order_worker.py`, add this file) by calling the worker's retry
  logic directly with a mocked `process_webhook_message` that raises a transient
  exception N times, and assert `retry_count` incrementing and eventual `HOLD`. Drop
  the functional-level retry test — document in the README that retry/backoff is
  unit-tested, not functionally tested, because reliably forcing infra-level
  transient failures in a docker-compose CI job is disproportionately complex for
  what it proves. **Do not build fault-injection plumbing into the production
  worker just to make a functional test pass** — that would be adding
  production-code complexity for a test's sake.

  Revise `tests/functional/tests/test_retries.py` to instead cover a still-valuable
  functional case: `test_webhook_for_unknown_provider_returns_404` and
  `test_webhook_for_nonexistent_order_is_dropped_without_error` (send a valid,
  well-signed webhook whose `order_id` doesn't exist — assert `202` at the HTTP
  layer, no order created, no crash, nothing on the outbound queue after a short
  wait).

## Phase 10 — CI

`.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit -v

  functional:
    runs-on: ubuntu-latest
    needs: unit
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: docker compose up -d --build
      - name: Wait for app health
        run: |
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/ping && break
            sleep 2
          done
      - run: pip install -e tests/functional
      - run: pytest tests/functional/tests -v
      - if: always()
        run: docker compose logs
      - if: always()
        run: docker compose down -v
```
Two jobs: unit tests run standalone (fast feedback, no docker), functional tests
build+run the full compose stack, wait for `/ping`, run pytest against it, always
dump logs and tear the stack down (`always()` so teardown/logs happen even on
failure — don't leak containers on a failed run).

## Phase 11 — README.md

Write a README aimed at a reviewer skimming the repo for 2 minutes. Sections:
1. One-paragraph pitch: what this demonstrates (functional-test framework design
   for an async order/payment service — pluggable provider adapters, webhook
   verification, queue-driven worker, WireMock-style external-call stubbing, SQS
   polling assertions), and that it's a clean-room portfolio piece, not derived from
   any employer's proprietary code.
2. Architecture diagram (ASCII is fine) showing: client → API → inbound queue →
   worker → pipeline (verify/parse via registry) → DB + outbound queue.
3. `docker compose up -d --build` quickstart, then `pip install -e tests/functional
   && pytest tests/functional/tests -v`.
4. "Why this structure" — 3-4 bullets explicitly calling out the design decisions
   that make this a good QA showcase: separate test-framework project (tests don't
   import production code — they validate the wire contract, not implementation
   details), pluggable provider registry (adding a provider = one new module + one
   registry line, zero changes elsewhere), idempotency/duplicate-webhook handling,
   retry/backoff tested at the right layer (unit, not brittle infra-level functional
   tests).
5. Test inventory table: file → what it covers.

---

## Explicit Non-Goals

Do not implement any of the following — they were considered and deliberately cut:
- Kubernetes manifests / Helm charts — no persistent deployment exists.
- More than 2 providers — 2 is enough to prove the registry pattern; a 3rd is pure
  repetition.
- Outbound provider API calls (e.g. `payhub` calling out to verify a charge) — this
  domain is webhook-push-only by design; don't add speculative outbound HTTP calls
  the tests would then need to mock for no behavioral gain.
- Fault-injection plumbing in production code to make retry tests pass functionally
  — see Phase 9 rationale. Retry/backoff is a unit-test concern here.
- Auth/JWT on the `payhub` API itself — out of scope; the focus is the test
  framework and worker pipeline, not building a production auth system.
- Any dependency on `qatoolset`, `qawiremock`, or any other private/internal
  package — everything in `tests/functional/qa_toolkit/` must resolve from PyPI
  (`requests`, `boto3`, `pytest`) only.

## Definition of Done

- [ ] `docker compose up -d --build` brings up a healthy stack (`/ping` returns 200).
- [ ] `pytest tests/unit -v` passes with zero failures, no network/DB required.
- [ ] `pytest tests/functional/tests -v` passes against the compose stack.
- [ ] GitHub Actions CI (`unit` + `functional` jobs) is green on a fresh clone.
- [ ] README lets a reviewer understand the architecture and run everything in
  under 5 minutes without asking questions.
- [ ] No references to `qatoolset`, `qawiremock`, Helm, or Kubernetes anywhere in
  the repo.
