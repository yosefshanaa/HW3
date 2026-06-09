# Prompt Engineering Log (ספר הפרומפטים)

Per the submission guidelines (§8.3), this log documents the meaningful prompts
used while building the project with an AI coding agent, and the prompts that
live *inside* the product (the crew's agent prompts). It records context, goal,
outcomes and the iterative refinements that followed.

---

## Part A — Build prompts (how the project was constructed)

The project was built with an AI agent under "vibe coding" / agent-orchestration,
following the mandated workflow PRD → PLAN → TODO → code.

### A1. Scope & requirements intake
- **Context:** five course PDFs (lecture summary, CrewAI A/B, 2026 architecture,
  LangChain) plus the software-submission guidelines.
- **Prompt (intent):** *"Read the assignment and supporting decks; the priority
  is the lecture's assignment §13. Start working on HW3."*
- **Outcome:** extracted the §13 deliverable (CrewAI crew → ~15-page LaTeX book
  with required BiDi/figure/table/formula/TikZ/bibliography elements).
- **Refinement:** a follow-up clarified the chosen topic ("how to build a
  start-up"), provider (OpenAI), and that the **submission guidelines** (PRD/PLAN/
  TODO, SDK, gatekeeper, uv, tests) also apply — and that **commit count matters**.

### A2. Planning documents
- **Goal:** produce `docs/PRD.md`, `docs/PLAN.md`, `docs/TODO.md` and three
  per-mechanism PRDs before coding.
- **Practice that worked:** writing KPIs as a table with explicit acceptance
  criteria, and ADRs with trade-offs — these became the checklist the code was
  measured against.

### A3. Core software (SDK + gatekeeper + config)
- **Goal:** "single entry-point SDK; all external calls through a rate-limited
  gatekeeper; no hardcoded tunables; version tracking."
- **Iterative fixes:**
  - ruff **N818** → renamed `RateLimitExceeded` → `RateLimitExceededError`.
  - Made the gatekeeper clock **injectable** so rate-limit tests don't sleep.

### A4. LaTeX book
- **Goal:** "LuaLaTeX + polyglossia Hebrew/English BiDi; cover, TOC, headers/
  footers; one image, one Python graph, one table, one fancy formula, a BiDi
  chapter, a TikZ diagram, a biber bibliography."
- **Practice:** keep structural LaTeX human-authored and inject prose (ADR-6) to
  guarantee compilable, correct RTL/LTR output.
- **Outcome (v1.0.0):** the BiDi layer was switched at compile time from
  polyglossia to **babel `bidi=basic`** — polyglossia's `luabidi` mirror-reversed
  embedded English. See PLAN.md ADR-3.

### A5. CrewAI pipeline
- **Goal:** "Researcher → Writer → Reviewer → LaTeX Engineer, sequential,
  context-chained; final task returns structured `BookContent`
  (`output_pydantic`); run through the gatekeeper."
- **Refinement:** inspected the CrewAI 1.x API (model fields, `CrewOutput`) before
  wiring, rather than assuming the 0.x signatures from the slides.

### A6. Tests & debugging
- **Goal:** "≥85% coverage, ruff clean, mock the LLM and the LaTeX compile."
- **Notable bug found & fixed:** importing CrewAI makes **pydantic replace
  `warnings.warn`** with a wrapper that rejects matplotlib's py3.12
  `skip_file_prefixes` kwarg → a benign matplotlib warning became a `TypeError`.
  Fixed with `shared/safe_warnings.py`, which restores the stdlib `warnings.warn`
  during figure rendering.
- **Bug:** `escape_latex` re-escaped characters its own replacements inserted
  (backslash → braces) → switched to a **single-pass regex**.

---

## Part B — In-product agent prompts (the crew)

These are the system prompts that ship in `src/startup_book/agents/`. They are
short, role-scoped, and append a shared Hebrew/BiDi instruction.

| Agent | role | goal |
|-------|------|------|
| Researcher | Startup Research Analyst | extract accurate structured facts per chapter |
| Writer | Senior Startup Author | turn research into clear Hebrew chapters |
| Reviewer | Senior Editor | improve accuracy/clarity without changing meaning |
| LaTeX Engineer | LaTeX Typesetter | map chapters into structured `BookContent` |

Shared appended instruction (BiDi):
> *"כתוב בעברית תקנית וברורה. השאר מונחים טכניים באנגלית (כגון MVP,
> Product-Market Fit, CAC) באנגלית, ושלב אותם באופן טבעי בתוך הטקסט."*

Task chaining uses CrewAI `context` (research → write → review → latex), and the
final task declares `output_pydantic=BookContent` so the crew returns validated,
structured data instead of free text.

### B1. Getting the crew to write the *whole* book (v1.40)

The first crew prose was one thin paragraph per chapter (≈60 words → an 11-page
`book_generated.pdf`). The root cause was **asking for all 8 chapters in one
response**: any model rations a single completion, and CrewAI bundles it into one
`BookContent` JSON — so it self-limited to ~300 words/chapter, and pushing harder
just truncated the JSON to a single chapter. Not an AI limit, a pipeline-shape
limit. The fix and its supporting changes:

- **Per-chapter generation (the key change):** `crew_service` now runs the full
  Researcher → Writer → Reviewer → LaTeX crew **once per chapter**, so each chapter
  gets the model's entire output budget and comes out full-length (600–900 words,
  6–7 sections). Result: a complete **21-page** crew-authored book.
- **Prompt (length + structure):** the Writer mandates ≥600 words, 5–6 `## `
  sub-sections (a full 110–150-word paragraph each), **bold** terms, a `[@key]`
  citation, and a `> ` takeaway line. The Reviewer is **"enrich, never shorten"** —
  LLM editors default to compressing.
- **Renderer (`shared/latex_text.py`):** crew Markdown inherits the book's design —
  `## ` → styled `\section`, `> ` → a brand `takeaway` box, `[@key]` →
  `\cite{key}` (keys carried through escaping by an indexed placeholder).
- **Compile-safety lessons (live-LLM output breaks LaTeX in ways curated text does
  not):** crew bib fields are now LaTeX-escaped — a raw `&` in author *"McKinsey &
  Company"* was a **fatal** biber error that aborted the whole build; `AutoFakeBold`
  keeps **bold Hebrew** on the Hebrew font (David CLM ships no bold `.otf`, so
  `\textbf{Hebrew}` was silently falling back to Latin Modern and dropping glyphs);
  and the crew bibliography stays in the Hebrew main language so the agents' mixed
  Hebrew/English source titles all render. Math passthrough was tried and **removed**
  — letting the LLM emit raw LaTeX math is exactly the fragility ADR-6 avoids.
- **Stable filenames:** generated chapters are named by position (`01-1`…), not by
  the crew-chosen id, so they always match `main_generated.tex`'s input list.

---

## Recommended practices (lessons)
1. **Docs before code** turned vague intent into a measurable checklist.
2. **Inspect the real library API** (CrewAI 1.x) before coding from slides.
3. **Inject time/IO seams** (clock, subprocess, services) so everything is
   testable without the network, the wall clock, or a LaTeX engine.
4. **Keep structural LaTeX human-authored**; let the LLM fill prose only.
5. **Pin the environment** (`uv` + Python 3.12) — newer interpreters (3.14) broke
   CrewAI installation.
