# PLAN — Architecture & Technical Plan

**Product:** `startup-book` · **Version:** 1.00 · **Status:** Draft
Companion to [`PRD.md`](PRD.md). Defines how the system is structured and why.

---

## 1. C4 Model

### 1.1 Context (Level 1)
```mermaid
flowchart LR
    author([Author / Evaluator]) -->|topic, build cmd| sys[startup-book system]
    sys -->|chat completions| openai[(OpenAI API)]
    sys -->|compile| latex[[LuaLaTeX + biber]]
    sys -->|book.pdf + cost report| author
```

### 1.2 Container (Level 2)
```mermaid
flowchart TB
    cli[CLI / main.py] --> sdk[BookBuilderSDK  ‹single entry point›]
    sdk --> crew[Crew Service ‹CrewAI›]
    sdk --> fig[Figure Service ‹matplotlib›]
    sdk --> tex[LaTeX Service ‹templating›]
    sdk --> comp[Compile Service ‹lualatex/biber›]
    crew --> gate[API Gatekeeper]
    gate --> openai[(OpenAI)]
    crew & fig & tex & comp --> cfg[Config + Version + Constants]
```

### 1.3 Component (Level 3) — package layout
```
src/startup_book/
├── __init__.py            # exports public API + __version__
├── main.py                # CLI entry (thin; delegates to SDK)
├── constants.py           # immutable project constants
├── sdk/
│   ├── __init__.py
│   └── sdk.py             # BookBuilderSDK — the ONLY business entry point
├── services/
│   ├── crew_service.py    # build + run the CrewAI crew
│   ├── latex_service.py   # content -> .tex (template fill)
│   ├── compile_service.py # multi-pass LuaLaTeX + biber build
│   └── figure_service.py  # matplotlib figures -> vector PDF
├── agents/
│   ├── definitions.py     # Agent factory (role/goal/backstory/tools)
│   └── tasks.py           # Task factory (description/expected_output/context)
└── shared/
    ├── gatekeeper.py      # ApiGatekeeper — all external calls funnel here
    ├── config.py          # ConfigManager — reads config/*.json + .env
    └── version.py         # __version__ = "1.00" + compatibility check
```

> **150-LOC rule:** any file approaching the limit is split (e.g. agent
> definitions vs task definitions live in separate files; the crew service only
> wires them together).

---

## 2. SDK-Centric Architecture (guidelines §4)

```
External consumers (CLI / future GUI / REST / tests)
        │
        ▼
   ┌──────────────┐
   │ BookBuilderSDK│  ← single entry point for ALL business logic
   └──────┬───────┘
          ▼
   ┌──────────────┐
   │   Services   │  ← crew, latex, compile, figure (orchestrators)
   └──────┬───────┘
          ▼
   ┌──────────────────┐
   │ Infrastructure   │  ← Gatekeeper→OpenAI, file I/O, lualatex subprocess
   └──────────────────┘
```

- **No business logic in `main.py`** — it parses args and calls the SDK.
- The SDK exposes: `generate_content(topic)`, `make_figures()`,
  `render_latex(content)`, `compile_pdf()`, and `build(topic)` (full pipeline).

---

## 3. Data Flow & Contracts

```mermaid
sequenceDiagram
    participant U as CLI
    participant S as SDK
    participant C as CrewService
    participant G as Gatekeeper
    U->>S: build(topic)
    S->>C: generate_content(topic)
    C->>G: execute(llm_call) (per agent step)
    G-->>C: completion (rate-limited, logged)
    C-->>S: BookContent (chapters, sources, metadata)
    S->>S: make_figures() -> assets/figures/*.pdf
    S->>S: render_latex(content) -> latex/chapters/*.tex
    S->>S: compile_pdf() -> latex/book.pdf
    S-->>U: BuildResult(pdf_path, token_usage, cost)
```

**Key contracts (pydantic models in `services`/`shared`):**
- `BookContent`: `title`, `chapters: list[Chapter]`, `sources: list[Source]`,
  `token_usage`.
- `Chapter`: `heading`, `body_markdown`, `language` (`he`/`mixed`).
- `BuildResult`: `pdf_path`, `pages`, `token_usage`, `estimated_cost_usd`.
- `RateLimitConfig`: `requests_per_minute`, `concurrent_max`,
  `retry_after_seconds`, `max_retries` (from `config/rate_limits.json`).

---

## 4. Architecture Decision Records (ADRs)

**ADR-1 — CrewAI for orchestration.**
*Context:* role-based writing team with clear, bounded tasks.
*Decision:* CrewAI sequential process (Researcher→Writer→Reviewer→LaTeX).
*Trade-off:* less stateful control than LangGraph, but the workflow is linear and
predictable → CrewAI is the better fit (architecture deck: "role-based agent
teams, clear tasks, bounded autonomy"). *Alternatives:* LangGraph (overkill for
a linear pipeline), AutoGen (conversational, harder to reproduce).

**ADR-2 — OpenAI provider behind a Gatekeeper.**
*Decision:* funnel every LLM call through `ApiGatekeeper` with config-driven rate
limits, retries and logging. *Trade-off:* a thin indirection layer for a large
gain in observability, cost control and testability (mockable seam).
*Alternative:* call the SDK directly (rejected — violates §5).

**ADR-3 — LuaLaTeX + babel `bidi=basic` for Hebrew BiDi.**
*Decision:* LuaLaTeX with **babel** (`bidi=basic`, Hebrew main + English) and a
Hebrew-capable OpenType font (David CLM from `fonts-culmus`). *Trade-off:*
heavier than pdfLaTeX but the only clean path to correct RTL/LTR + Hebrew
shaping; matches assignment §13.2. *Alternative:* XeLaTeX (allowed fallback,
same source).
*Revision (v1.0.0):* originally implemented with `polyglossia`+`luabidi`. On
TeX Live, `luabidi.sty` is unpackaged and, when supplied manually, its LuaTeX
bidi mirror-reversed every embedded English (LTR) run inside the Hebrew (RTL)
text (e.g. "Lean Startup" → "putratS naeL"). Switched to babel `bidi=basic`,
whose Unicode bidi algorithm keeps LTR runs upright. Fonts now set via
`\babelfont`; `\textenglish{…}` replaced by the `\en{…}` =
`\foreignlanguage{english}{…}` macro.

**ADR-4 — Deterministic, grounded content by default.**
*Decision:* ship curated source facts and keep live web-search tools optional
(off by default). *Trade-off:* less "live" research, but reproducible, cheap and
build-stable runs (KPI K3/K7). Web search can be enabled via config.

**ADR-5 — `uv` + pinned Python 3.12.**
*Decision:* manage env and deps with `uv`, pin Python 3.12 (CrewAI lags 3.14).
*Trade-off:* an extra interpreter download; gains reproducibility (guidelines §8).

**ADR-6 — LaTeX as committed source + generated chapters.**
*Decision:* hand-author a robust template/preamble; the crew fills chapter
bodies. *Trade-off:* the LLM doesn't emit the whole document (risky for BiDi
correctness); we keep structural LaTeX human-controlled and inject prose.

---

## 5. Versioning Plan (guidelines §8.1)

| Item | Location | Initial |
|------|----------|---------|
| Code version | `src/startup_book/shared/version.py` (`__version__`) | 1.00 |
| Config version | `config/setup.json` → `"version"` | 1.00 |
| Rate-limit config version | `config/rate_limits.json` → `"version"` | 1.00 |

On startup the SDK validates that config versions are compatible with the code
version (logs a warning on mismatch). Git **tags** mark releases (`v1.0.0`).

---

## 6. Testing & CI Strategy
- `tests/unit/` mirrors `src/` (one test module per source module).
- `tests/integration/` exercises `build()` with a **mocked** crew/LLM and a real
  (fast) LaTeX compile in CI-capable environments.
- `conftest.py` holds shared fixtures (fake config, fake completions).
- Coverage gate `fail_under = 85`; ruff gate 0 violations.

## 7. Git Workflow
- Frequent, small commits with conventional messages.
- Short-lived feature branches for larger units, merged with `--no-ff` to keep
  history; tag the final release. (Professor counts commits → favour granularity.)

---

## 8. Concurrency Model (guidelines §15)

The 8 chapters are **independent** units of work whose cost is dominated by
network latency (LLM round-trips), so they are generated **concurrently** rather
than back-to-back. This is the project's answer to §15.

### 8.1 Why threads (not async/processes) — §15.1
- The work is **I/O-bound** (waiting on the OpenAI API), so the GIL is released
  during the call; threads give near-linear speed-up without rewriting CrewAI's
  synchronous API as `async`.
- No CPU-bound hot loop ⇒ processes would only add IPC/serialization overhead.
- Implementation: `CrewService._run_chapters` submits one
  `_run_chapter` per chapter to a `ThreadPoolExecutor`.

### 8.2 Bounding & backpressure
- Pool width = `min(n_chapters, rate_limits.concurrent_max)` — chapter
  parallelism never exceeds the configured concurrency budget.
- The **API Gatekeeper** independently rate-limits every individual LLM call
  (sliding-window RPM/RPH, FIFO admission, `concurrent_max`, retry, queue-depth
  backpressure). Chapter threads do **not** hold a gatekeeper slot while idle, so
  nesting the two limits cannot deadlock.

### 8.3 Thread-safety note
- Each chapter builds its **own** agents + `Crew` inside `_run_chapter`; the only
  shared object is the `GatekeptLLM`, whose calls are stateless and serialized
  through the gatekeeper's `threading.Condition`.
- The gatekeeper's mutable counters/queues are all guarded by that single
  `Condition` (one lock); admission tickets give FIFO ordering.
- Results are written to **disjoint** indices of a pre-sized list, then
  reassembled in outline order — no shared mutable accumulator during the run.

### 8.4 §15 checklist
- [x] Identified the concurrency model (thread pool over chapters) and justified
      it (I/O-bound → threads, §15.1).
- [x] Bounded concurrency via configuration (`concurrent_max`), not hardcoded.
- [x] Shared state is lock-protected (gatekeeper `Condition`); per-task state is
      isolated; results merged deterministically.
- [x] No deadlock between the two bounded resources (chapter pool ⟂ gatekeeper).
- [x] Regression test asserts observed concurrency never exceeds `concurrent_max`
      while still running in parallel
      (`test_chapters_run_concurrently_bounded_by_concurrent_max`).
