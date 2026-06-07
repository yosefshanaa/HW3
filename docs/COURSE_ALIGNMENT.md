# Course PDF Alignment Report

This report maps the project against the five course PDFs reviewed from
`/mnt/c/Users/yosef/Downloads`:

- `ארכיטקטורת_סוכני_בינה_מלאכותית_בשנת_2026.pdf`
- `main-L06-summary-and-ex03-defination.pdf`
- `LangChain_בעברית.pdf`
- `CrewAI_—_צוותי_Agents_שעובדים_כמו_ארגון-Part-A.pdf`
- `CrewAI_—_מהפסאודו-קוד_לשרשרת_עבודה_מלאה-part-B.pdf`

## What Is Good

| Course requirement / idea | Project evidence |
|---|---|
| L06 assignment: CrewAI team writes an article/book and emits a respectable LaTeX PDF | `src/startup_book/services/crew_service.py`, `latex/book.pdf` |
| About 15 pages | `latex/book.pdf` is 17 pages (within the requested ~15-page scope) |
| Cover with topic, author, date, course, lecturer | `latex/cover.tex` |
| Table of contents, chapters, headers and footers | `latex/main.tex`, `latex/preamble.tex` |
| At least one image | `assets/figures/illustration.png` |
| At least one Python-generated graph | `assets/figures/jcurve.pdf`, `unit_economics.pdf`, `funnel.pdf` |
| At least one table | `latex/chapters/06-economics.tex` |
| Real mathematical formula | `latex/elements/economics-block.tex`, `latex/chapters/06-economics.tex` |
| Hebrew/English BiDi chapter | `latex/chapters/03-lean.tex` |
| TikZ diagrams | `latex/elements/lean-diagram.tex`, `latex/elements/pitfalls-diagram.tex` |
| Bibliography with linked citations | `latex/references.bib`, `biblatex`, `biber`, `hyperref` |
| CrewAI Part A/B: Agent, Task, Crew, Process | `agents/definitions.py`, `agents/tasks.py`, `crew_service.py` |
| CrewAI context passing | `Task(context=[...])` in `agents/tasks.py` |
| CrewAI sequential workflow | `Process.sequential` in `crew_service.py` |
| "Production agent is a system, not a prompt" | SDK, config files, gatekeeper, tests, build script, docs |
| Automated quality enforcement (HW1 feedback) | `.github/workflows/ci.yml` runs ruff + pytest (85% gate) on every push/PR |

## What Was Missing Or Weak

1. The docs did not explicitly trace the project back to the five named PDFs.
   This file fixes that gap.
2. The lecture asks for about 15 pages. The final build is 17 pages, within the
   requested scope; the docs report the real page count rather than inventing a
   hard requirement.
3. The CrewAI Part B slides show a live search tool example. This project keeps
   web search optional and off by default, using curated facts for repeatable
   grading. That is a deliberate architecture trade-off, not a missing assignment
   requirement.
4. The 2026 architecture deck discusses memory, durable state, human gates,
   tracing and broader observability. The project implements config, retries,
   gatekeeping, tests and logs, but not persistent memory, RAG, human-in-the-loop,
   or a trace UI. Those are production extensions outside the HW3 PDF checklist.

## Design / RTL / LTR

- The LaTeX source uses LuaLaTeX with `babel` and `bidi=basic`, Hebrew as the main
  language and English as the secondary language.
- Embedded English is marked with `\en{...}` / `\foreignlanguage{english}{...}`,
  so English terms stay left-to-right inside Hebrew paragraphs.
- The current cover and formula areas avoid mixed-direction labels that previously
  caused visual risk.
- The final PDF has been rebuilt and visually checked for cover, TOC,
  headers/footers, image, graphs, table, formula, TikZ diagrams, citations and
  Hebrew RTL / English LTR behavior.

## Bottom Line

The project satisfies the L06 assignment checklist and follows the CrewAI
Agent/Task/Crew/Process pattern from Part A/B. The main remaining limitations are
production-depth features from the architecture deck: persistent memory, RAG,
human review gates and richer trace observability.
