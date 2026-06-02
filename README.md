# HW3 — Startup Mini-Book Generator (CrewAI → LaTeX)

> A professional, agent-based system that **researches, writes, reviews and
> typesets** a ~15-page Hebrew/English mini-book on **"How to Correctly Build a
> Start-up"**, and compiles it to a polished PDF with **LuaLaTeX**.

Deliverable for **HW3 — "Mass Production of AI Agents"** (lecturer: Dr. Yoram
Segal). Built to the standards in *Guidelines for Writing Professional Software
at the Highest Level of Excellence* (v3.00): SDK architecture, central API
gatekeeper, `uv`, ruff-clean code, ≤150 LOC/file, ≥85 % test coverage, version
tracking, and full `docs/`.

---

## What it does

A **CrewAI** crew of four role-specialised agents runs sequentially —

```
Researcher → Writer → Reviewer → LaTeX Engineer
```

— passing work forward via CrewAI `context`. The result is mapped into a
structured `BookContent`, the Python figures are rendered, and the LaTeX layer
typesets a mini-book containing every required element:

| Requirement (assignment §13.1) | Where |
|--------------------------------|-------|
| Cover page (title/author/date/course/lecturer) | `latex/cover.tex` |
| Table of contents, chapters, **headers/footers** | `latex/main.tex`, `preamble.tex` |
| **Image** (raster illustration) | `assets/figures/illustration.png` |
| **Python-generated graph** | `assets/figures/jcurve.pdf`, `unit_economics.pdf` |
| **Table** | ch. *Unit Economics* |
| **Fancy math formula** | ch. *Unit Economics* (LTV/CAC/runway) |
| **Hebrew↔English BiDi chapter** | ch. *Lean Startup* |
| **TikZ diagram** | Build–Measure–Learn loop, risk chain |
| **Bibliography (linked citations)** | `latex/references.bib` + biber |

## Architecture (overview)

```
CLI ─▶ BookBuilderSDK ─▶ services{crew, figure, latex, compile}
                         crew ─▶ ApiGatekeeper ─▶ OpenAI
```

The **SDK** is the single entry point for all business logic; the **gatekeeper**
rate-limits, retries and logs every external call. See
[`docs/PLAN.md`](docs/PLAN.md) for C4 diagrams and ADRs, and the per-mechanism
PRDs in [`docs/`](docs/).

## Installation

Prerequisites: **`uv`**, and a **LuaLaTeX** engine (MiKTeX recommended; TeX Live
works too) for the final compile.

```bash
# 1. Python deps (uv is mandatory; it fetches Python 3.12 automatically)
uv sync --extra dev

# 2. Secrets
cp .env-example .env        # then edit .env and set OPENAI_API_KEY

# 3. LaTeX engine (Ubuntu/WSL example — MiKTeX)
#    Install MiKTeX so `lualatex` and `biber` are on PATH (see docs/PLAN.md).
```

## Usage

```bash
# Full pipeline: research → write → review → render LaTeX → compile PDF
uv run startup-book build

# Regenerate only the Python figures (no API key needed)
uv run startup-book figures

# Run the crew and print the chapter headings it produced
uv run startup-book content

# Version
uv run startup-book --version
```

Compile the curated book directly (no Python needed):

```bash
cd latex && ./build.sh      # lualatex → biber → lualatex → lualatex → book.pdf
```

## Configuration

All tunables live in `config/` (never hardcoded); secrets live only in `.env`.

| File | Purpose |
|------|---------|
| `config/setup.json` | book metadata, chapter outline, model, build settings |
| `config/rate_limits.json` | API gatekeeper rate limits |
| `.env` | `OPENAI_API_KEY` (git-ignored) |

Change the model without touching code: edit `config/setup.json → llm.model`
(or set `OPENAI_MODEL` in `.env`).

## Project structure

```
src/startup_book/   SDK, services, agents, shared (gatekeeper/config/version)
latex/              the LaTeX mini-book (preamble, cover, chapters, bib, build.sh)
assets/figures/     Python-generated figures (matplotlib)
config/             versioned JSON configuration
docs/               PRD, PLAN, TODO, per-mechanism PRDs, PROMPTS
tests/              unit + integration (≥85% coverage)
notebooks/          results / cost analysis
```

## Development

```bash
uv run pytest            # tests + coverage (gate: 85%)
uv run ruff check        # lint (zero violations required)
```

## License & credits

MIT — see [`LICENSE`](LICENSE). Built with
[CrewAI](https://docs.crewai.com), [matplotlib](https://matplotlib.org),
[pydantic](https://docs.pydantic.dev) and LuaLaTeX (`polyglossia`, `biblatex`,
`TikZ`). Bibliography sources are credited in `latex/references.bib`.
