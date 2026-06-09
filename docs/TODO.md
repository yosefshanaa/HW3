# TODO — Task Tracking

**Product:** `startup-book` · Companion to [`PRD.md`](PRD.md) / [`PLAN.md`](PLAN.md).
Status keys: ☐ not started · ◐ in progress · ☑ done. Owner: `dev` (solo) /
`ai` (AI-assisted). Each task lists its **Definition of Done (DoD)**.

> **Overall:** ✅ **All phases complete (v1.4.0).** Software, book source, crew,
> tests, docs, and the final compile are done. The polished deliverable is
> `latex/book.pdf` (17 pp, within the ~15-page target) — fully redesigned (TikZ
> chapter banners, callouts, highlighted formulas, five TikZ diagrams, colophon
> crediting the crew), compiled with LuaLaTeX (TeX Live) and correct Hebrew RTL /
> English LTR typesetting.
>
> **v1.4.0 — the crew writes the whole book.** The agent-authored book
> (`latex/book_generated.pdf`, now committed, **21 pp**) is produced by running
> the full pipeline **once per chapter** (Researcher → Writer → Reviewer → LaTeX),
> so each chapter gets the model's full output budget and comes out full-length
> (600–900 words, 6–7 styled sections, bold terms, a takeaway box, `\cite`
> citations, 40+ sources). Supporting fixes: Markdown→LaTeX converter renders
> crew prose into the book's design; crew-collected bib fields are LaTeX-escaped
> (a raw `&` in "McKinsey & Company" was a fatal biber error); `AutoFakeBold`
> keeps bold Hebrew on the Hebrew font; the crew bibliography stays in the Hebrew
> main language so mixed He/En sources render. Re-run: `python scripts/run_crew.py`
> (live OpenAI) then `./build.sh main_generated`.

## Phase 0 — Planning (M0)
- ☑ **T0.1** Initialise repo, scaffold, `.gitignore`, license, README stub.
- ☑ **T0.2** Write `PRD.md`. ☑ **T0.3** `PLAN.md`. ☑ **T0.4** `TODO.md`.
- ☑ **T0.5** Per-mechanism PRDs (crew, LaTeX, gatekeeper).
- ◐ **T0.6** User review/approval of all planning docs.

## Phase 1 — Core software (M1)
- ☑ **T1.1** `pyproject.toml` (uv, ruff, coverage) + `uv.lock`.
- ☑ **T1.2** `shared/version.py`. ☑ **T1.3** config files + `ConfigManager`.
- ☑ **T1.4** `shared/gatekeeper.py`. ☑ **T1.5** models + constants.
- ☑ **T1.6** `sdk/sdk.py` + thin CLI.

## Phase 2 — LaTeX deliverable (M2)
- ☑ **T2.1** `preamble.tex` (LuaLaTeX, babel `bidi=basic`, fancyhdr).
- ☑ **T2.2** Cover + TOC + chapters. ☑ **T2.3** image/table/formula/TikZ.
- ☑ **T2.4** BiDi chapter. ☑ **T2.5** `references.bib` + biber. ☑ **T2.6** `build.sh`.

## Phase 3 — CrewAI pipeline (M3)
- ☑ **T3.1** agents. ☑ **T3.2** tasks. ☑ **T3.3** `crew_service`.
- ☑ **T3.4** `latex_service`. ☑ **T3.5** `figure_service`. ☑ **T3.6** `compile_service`.

## Phase 4 — Content (M4)
- ☑ **T4.1** Curated source facts embedded in authored chapters.
- ☑ **T4.2** All 8 chapters populated (curated; crew can regenerate to `latex/generated/`).
- ☑ **T4.3** Cost/token reporting in the SDK (`_estimate_cost`).

## Phase 5 — Quality (M5)
- ☑ **T5.1** Unit tests (coverage ≥95 %). ☑ **T5.2** Integration test.
- ☑ **T5.3** ruff clean. ☑ **T5.4** `docs/PROMPTS.md`.
- ☑ **T5.5** `notebooks/results_analysis.ipynb`. ☑ **T5.6** full `README.md`.
- ☑ **T5.7** CI workflow (`.github/workflows/ci.yml`): ruff + pytest/coverage
  gate on every push/PR — automated quality enforcement (HW1-feedback gap).

## Phase 6 — Ship (M6) — ✅ complete
- ☑ **T6.1** Final clean compile + page/element verification. Built on TeX Live
  LuaLaTeX; `book.pdf` = 17 pp (within the ~15-page target, PRD K1 ✓),
  `book_generated.pdf` = 11 pp.
  Verified visually: cover, TOC, headers/footers, image, Python graph, table,
  boxed formula, BiDi chapter, TikZ, linked bibliography — all present with
  correct Hebrew RTL / English LTR.
- ☑ **T6.2** Final-checklist pass (guidelines §17).
- ☑ **T6.3** Committed `latex/book.pdf`, retained the buildable crew-output
  variant as evidence, tagged through `v1.1.0`, pushed.

> **Compile notes (host setup):** LuaLaTeX engine = TeX Live (`texlive-luatex`
> + friends), Hebrew font = David CLM from `fonts-culmus`. Two manual steps were
> needed: (1) `luabidi.sty` is absent from Ubuntu's TeX Live, so the language
> layer was switched from polyglossia+luabidi to **babel `bidi=basic`** (which
> also fixed reversed embedded-English runs); (2) the build needs the `culmus`
> Hebrew mono/sans families for `\texttt`/`\textsf` inside Hebrew.

---

### Milestone ↔ phase map
M0=Phase0 · M1=Phase1 · M2=Phase2 · M3=Phase3 · M4=Phase4 · M5=Phase5 · M6=Phase6.
