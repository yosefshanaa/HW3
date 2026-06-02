# TODO — Task Tracking

**Product:** `startup-book` · Companion to [`PRD.md`](PRD.md) / [`PLAN.md`](PLAN.md).
Status keys: ☐ not started · ◐ in progress · ☑ done. Owner: `dev` (solo) /
`ai` (AI-assisted). Each task lists its **Definition of Done (DoD)**.

---

## Phase 0 — Planning (M0)
- ☑ **T0.1** Initialise repo, scaffold tree, `.gitignore`, license, README stub
  · owner ai · *DoD:* pushed to GitHub, tree matches guidelines §2.4.
- ◐ **T0.2** Write `PRD.md` · *DoD:* goals, KPIs, FRs, NFRs, milestones. ☑
- ◐ **T0.3** Write `PLAN.md` · *DoD:* C4, ADRs, module map, versioning. ☑
- ☑ **T0.4** Write `TODO.md` (this file) · *DoD:* phased tasks with DoD.
- ☑ **T0.5** Per-mechanism PRDs: crew pipeline, LaTeX gen, API gatekeeper
  · *DoD:* each has theory, I/O, constraints, success/test scenarios.
- ◐ **T0.6** User review/approval of all planning docs (in progress).

## Phase 1 — Core software (M1)
- ☐ **T1.1** `pyproject.toml` (uv build, deps, ruff, coverage config), `uv.lock`
  · *DoD:* `uv sync` works on Python 3.12; ruff/coverage configured.
- ☐ **T1.2** `shared/version.py` (`__version__="1.00"` + compat check)
  · *DoD:* unit-tested, ruff-clean.
- ☐ **T1.3** `config/setup.json` + `config/rate_limits.json` + `ConfigManager`
  · *DoD:* values read from files; no hardcoded tunables; versioned.
- ☐ **T1.4** `shared/gatekeeper.py` (`ApiGatekeeper`: rate limit, retry, queue, log)
  · *DoD:* see `PRD_api_gatekeeper.md` scenarios; unit-tested with a fake clock.
- ☐ **T1.5** `constants.py` + pydantic models (`BookContent`, `Chapter`, …)
  · *DoD:* importable, typed, documented.
- ☐ **T1.6** `sdk/sdk.py` skeleton (method stubs + docstrings)
  · *DoD:* `from startup_book import BookBuilderSDK` works.

## Phase 2 — LaTeX deliverable (M2)
- ☐ **T2.1** `latex/preamble.tex` (LuaLaTeX, polyglossia He/En, fancyhdr, fonts)
  · *DoD:* compiles empty doc with headers/footers.
- ☐ **T2.2** Cover page + TOC + chapter scaffolding · *DoD:* FR-B1/FR-B2 visible.
- ☐ **T2.3** Required elements: image, table, fancy formula, TikZ diagram
  · *DoD:* FR-B3/FR-B5/FR-B6/FR-B8 present and compile.
- ☐ **T2.4** BiDi chapter (Hebrew prose + English code/terms) · *DoD:* FR-B7.
- ☐ **T2.5** `references.bib` + biber citations · *DoD:* FR-B9, links resolve.
- ☐ **T2.6** `build.sh` (lualatex×2 + biber + lualatex×2) · *DoD:* K3 green.

## Phase 3 — CrewAI pipeline (M3)
- ☐ **T3.1** `agents/definitions.py` (4 agents) · *DoD:* matches `PRD_crewai_pipeline.md`.
- ☐ **T3.2** `agents/tasks.py` (4 tasks, context chaining) · *DoD:* sequential flow.
- ☐ **T3.3** `services/crew_service.py` (assemble + kickoff, return `BookContent`)
  · *DoD:* integration test with mocked LLM is green (K7).
- ☐ **T3.4** `services/latex_service.py` (content → `.tex`) · *DoD:* fills chapters.
- ☐ **T3.5** `services/figure_service.py` (matplotlib) · *DoD:* FR-B4 PDF emitted.
- ☐ **T3.6** `services/compile_service.py` (wraps build) · *DoD:* returns `BuildResult`.

## Phase 4 — Content (M4)
- ☐ **T4.1** Curated source facts for the startup topic · *DoD:* grounds the crew.
- ☐ **T4.2** Wire real content into all chapters (~15 pp) · *DoD:* K1, K2.
- ☐ **T4.3** Cost/token reporting after a run · *DoD:* FR-S8.

## Phase 5 — Quality (M5)
- ☐ **T5.1** Unit tests mirroring `src/` · *DoD:* coverage ≥85 % (K4).
- ☐ **T5.2** Integration test for `build()` (mocked) · *DoD:* green in CI.
- ☐ **T5.3** ruff clean · *DoD:* `ruff check` → 0 (K5).
- ☐ **T5.4** `docs/PROMPTS.md` (Prompt Engineering Log) · *DoD:* key prompts logged.
- ☐ **T5.5** `notebooks/results_analysis.ipynb` (cost/sensitivity) · *DoD:* runs.
- ☐ **T5.6** Full `README.md` user manual · *DoD:* install/usage/config/license.

## Phase 6 — Ship (M6)
- ☐ **T6.1** Final clean compile + page/element verification · *DoD:* all KPIs.
- ☐ **T6.2** Final-checklist pass (guidelines §17) · *DoD:* checklist all ✓.
- ☐ **T6.3** Commit `latex/book.pdf`, tag `v1.0.0`, push · *DoD:* release tagged.

---

### Milestone ↔ phase map
M0=Phase0 · M1=Phase1 · M2=Phase2 · M3=Phase3 · M4=Phase4 · M5=Phase5 · M6=Phase6.
