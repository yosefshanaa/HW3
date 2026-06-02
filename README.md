# HW3 — Startup Mini-Book Generator (CrewAI → LaTeX)

> A professional, agent-based system that researches, writes, reviews and
> typesets a ~15-page Hebrew/English mini-book on **"How to Correctly Build a
> Startup"**, and compiles it to a polished PDF with **LuaLaTeX**.

This repository is the deliverable for **HW3 — "Mass Production of AI Agents"**
(course: *Mass Production of AI Agents*, lecturer: Dr. Yoram Segal). It is built
to the standards in *Guidelines for Writing Professional Software at the Highest
Level of Excellence* (v3.00).

> 🚧 **Status:** scaffolding. Full documentation lives in [`docs/`](docs/).
> Start with [`docs/PRD.md`](docs/PRD.md) → [`docs/PLAN.md`](docs/PLAN.md) →
> [`docs/TODO.md`](docs/TODO.md).

## What it produces

A CrewAI crew (Researcher → Writer → Reviewer → LaTeX Engineer) generates the
book content; a LaTeX layer typesets it into a mini-book that includes a cover
page, table of contents, headers/footers, an image, a Python-generated graph, a
table, a "fancy" math formula, a Hebrew↔English BiDi chapter, a TikZ diagram and
a linked bibliography.

## Quick start

```bash
uv sync                      # install dependencies (uv is mandatory)
cp .env-example .env         # then add your OPENAI_API_KEY
uv run startup-book build    # research → write → review → emit LaTeX → compile
```

Full installation, usage, configuration and license details will be documented
here as the project is built.
