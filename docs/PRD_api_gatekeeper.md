# PRD — Mechanism: API Gatekeeper

**Mechanism:** `shared/gatekeeper.py`. **Version:** 1.00.
Parent: [`PRD.md`](PRD.md), [`PLAN.md`](PLAN.md). Mandated by guidelines §5.

---

## 1. Description & theoretical background
Every external API call (OpenAI completions) **must** pass through one central
gatekeeper. It enforces rate limits before each call, queues over-limit requests
(FIFO, not dropped), retries transient failures with backoff, and logs every
call for observability/cost tracking. This realises the lecture's "production
agent = controlled system" principle and OWASP-style least-privilege control of
the agent's outward actions.

## 2. Interface
```python
class ApiGatekeeper:
    """Centralised, rate-limited, observable entry point for external calls."""
    def __init__(self, config: RateLimitConfig, clock: Clock | None = None): ...
    def execute(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """Run `fn` through limits → queue → retry → log. Returns its result."""
    def get_queue_status(self) -> QueueStatus:
        """Return current queue depth and counters."""
```
- `clock` is injectable so tests use a **fake clock** (no real sleeping).

## 3. Requirements & I/O
- **Input:** a callable (the actual API call) + args; a `RateLimitConfig` loaded
  from `config/rate_limits.json` (never hardcoded — guidelines §5.2/§7.2).
- **Behaviour:**
  - Enforce `requests_per_minute`, `requests_per_hour`, `concurrent_max`.
  - On limit reached → enqueue (FIFO) up to `max_queue_depth`; apply
    backpressure when full (raise/typed error), never silently drop.
  - Retry transient failures up to `max_retries` with `retry_after_seconds`.
  - Log each call: timestamp, function, attempt, outcome, duration.
- **Output:** the wrapped call's result, or a typed `GatekeeperError`
  / `RateLimitExceededError` on exhaustion.

## 4. Config (`config/rate_limits.json`)
```json
{ "version": "1.00",
  "services": { "default": {
    "requests_per_minute": 30, "requests_per_hour": 500,
    "concurrent_max": 5, "retry_after_seconds": 30, "max_retries": 3,
    "max_queue_depth": 100 } } }
```

## 5. Constraints, alternatives, rationale
- **Constraint:** must be deterministically testable → inject clock + use a
  monotonic token-bucket/sliding-window; no wall-clock `sleep` in unit tests.
- **Alternatives:** call OpenAI directly (rejected — no control/observability);
  a third-party limiter lib (rejected — overkill, adds a dependency for a small,
  well-specified component). *Rationale:* a tiny, owned, fully-tested seam that
  every agent step funnels through.

## 6. Success criteria & test scenarios
- **SC-1** Under limit → call passes straight through. *Test:* N < rpm calls all
  execute immediately (fake clock).
- **SC-2** Over limit → request is queued, then released when the window resets.
  *Test:* exceed rpm; advance fake clock; assert queued call runs.
- **SC-3** Transient error → retried up to `max_retries`, then typed error.
  *Test:* fn fails k<max then succeeds → success; fails > max → `GatekeeperError`.
- **SC-4** Full queue → backpressure (typed error), nothing dropped. *Test:* fill
  queue to `max_queue_depth`; next enqueue raises.
- **SC-5** Every call is logged. *Test:* spy logger receives one record per call.
