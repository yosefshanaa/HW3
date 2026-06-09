# Quality Model & Extension Points

Companion to [`PRD.md`](PRD.md) and [`PLAN.md`](PLAN.md). Maps the project to the
**ISO/IEC 25010** product-quality model (guidelines §13) and documents the
**extension points** for swapping models, providers and templates or adding an
agent (guidelines §12.1).

---

## 1. ISO/IEC 25010 Quality Characteristics (§13)

The eight characteristics of the 2011 product-quality model, each tied to
concrete evidence in this repository. (The 2023 revision adds *Safety* as a
ninth; not applicable to an offline book generator.)

| # | Characteristic | How `startup-book` addresses it (evidence) |
|---|----------------|--------------------------------------------|
| 1 | **Functional Suitability** | End-to-end `build()` produces a typeset PDF with every required element (cover, ToC, formulas, figures, tables, BiDi prose, bibliography). Verified by `tests/integration/test_build_pipeline.py` and the committed `latex/book.pdf`. |
| 2 | **Performance Efficiency** | Chapters generate **concurrently** through a bounded thread pool (`CrewService._run_chapters`, PLAN §8) — ~8× wall-clock improvement over sequential. The gatekeeper's sliding-window limiter prevents wasteful 429 retries. Cost/latency are measured, not guessed (token usage → `BuildResult.estimated_cost_usd`; `notebooks/results_analysis.ipynb`). |
| 3 | **Compatibility** | Clean seams: the SDK is provider-agnostic; the LLM is wrapped behind `GatekeptLLM` (`services/gatekept_llm.py`); structured data crosses boundaries as pydantic models (`shared/models.py`). Logs are emitted as machine-readable JSON lines (`shared/logging_setup.py`). |
| 4 | **Usability** | One-command CLI (`startup-book build` / `content` / `figures` / `audit`) with `--help` and a clear cost report. The `audit` command gives graders a one-glance health verdict. |
| 5 | **Reliability** | The API gatekeeper retries transient failures with backpressure (`shared/gatekeeper.py`); a typed error hierarchy (`shared/errors.py`) fails loudly and specifically; the LaTeX build halts on error and surfaces the log tail. 92 tests, 98% coverage. |
| 6 | **Security** | Secrets come only from the environment, never source (`shared/config.py`); every log record is scrubbed of `sk-…` keys and the live `OPENAI_API_KEY` (`shared/redaction.py`) — covered by a test asserting a key never reaches the logs. |
| 7 | **Maintainability** | SDK-centric architecture (§4), one responsibility per module, files kept small, strict `ruff` lint, and unit tests mirroring `src/`. Versioned code + config with a startup compatibility check (`shared/version.py`). |
| 8 | **Portability** | Pure-Python package managed with `uv` (locked `uv.lock`, `requires-python >=3.12,<3.14`); the only external tool is a TeX engine, selectable in config (`build.engine`). No OS-specific paths — everything derives from `constants.REPO_ROOT`. |

---

## 2. Extension Points (§12.1)

The system is designed to be reconfigured **without editing business logic** —
most changes are config-only.

### 2.1 Swap the model
Edit `config/setup.json` → `llm.model` (e.g. `gpt-4o`, `gpt-4.1-mini`), or set
the `OPENAI_MODEL` environment variable (env wins). Update
`llm.cost_per_1m_input_usd` / `…_output_usd` so the cost report stays accurate.
No code change.

### 2.2 Swap the provider / endpoint
The agents call a `crewai.LLM` wrapped by `GatekeptLLM`. Point it at any
LiteLLM-supported provider by setting the model prefix (e.g.
`anthropic/claude-…`, `azure/…`) in `setup.json` and the matching credentials in
`.env` (`OPENAI_BASE_URL` for OpenAI-compatible gateways). The gatekeeper, SDK
and services are untouched — only the LLM construction in
`CrewService._build_llm` reads config.

### 2.3 Swap / re-theme the LaTeX template
Structural LaTeX is hand-authored and additive (ADR-6): the crew only fills
prose. Change the look by editing `latex/theme.tex` / `latex/preamble.tex` /
`latex/cover.tex`, or change the document the generated prose flows into via
`latex/main_generated.tex`. `LatexService` writes only into `latex/generated/`,
so re-theming never collides with generated content.

### 2.4 Add an agent or pipeline stage
1. Add a factory entry in `agents/definitions.py` (`role` / `goal` / `backstory`
   + the shared `llm`), returned from `build_agents`.
2. Add the matching `Task` wiring in `agents/tasks.py` (`build_chapter_tasks`),
   placing it in the sequential chain.
   The crew is `Process.sequential`, so order is the list order; the final task
   must still yield the structured `BookContent`. No SDK/service change needed.

### 2.5 Tune limits & concurrency
`config/rate_limits.json` controls RPM/RPH, `concurrent_max` (which also bounds
chapter parallelism, PLAN §8), retries and queue depth — all without code edits.

### 2.6 Adjust logging
`config/logging_config.json` is a standard `logging.config.dictConfig`. Change
levels, add a file handler, or attach the `RedactionFilter` to new handlers
there; the redaction guarantee travels with the filter.
