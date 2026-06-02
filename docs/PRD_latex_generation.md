# PRD — Mechanism: LaTeX Generation & Compilation

**Mechanism:** `services/latex_service.py` + `services/compile_service.py` +
`latex/`. **Version:** 1.00. Parent: [`PRD.md`](PRD.md), [`PLAN.md`](PLAN.md).

---

## 1. Description & theoretical background
The book is typeset with **LuaLaTeX**, chosen for native Unicode + OpenType font
support and clean **Hebrew** shaping via **babel** (`bidi=basic`, Hebrew main
language, English as the secondary). BiDi (RTL Hebrew with embedded LTR
English/code/math) is handled by babel's Unicode bidi engine, which keeps LTR
runs upright; embedded English is marked with the `\en{…}` =
`\foreignlanguage{english}{…}` macro. The bibliography uses a `.bib` database
compiled by **biber** with `biblatex`. *(v1.0.0 switched from
polyglossia+luabidi — see PLAN.md ADR-3.)*

A correct build needs **multiple passes** so cross-references, the TOC and
citations stabilise (assignment §13.2): `lualatex → biber → lualatex → lualatex`
(we run lualatex twice up front for the TOC, then biber, then twice more — a
safe 4–5 pass sequence).

## 2. Document structure (`latex/`)
```
latex/
├── main.tex            # document root: loads preamble, cover, chapters, bib
├── preamble.tex        # packages, fonts, babel (bidi=basic), fancyhdr, biblatex
├── cover.tex           # cover page (FR-B1)
├── chapters/           # one .tex per chapter (some authored, some generated)
├── figures/            # TikZ sources / includegraphics targets
├── references.bib      # bibliography database (FR-B9)
└── build.sh            # multi-pass build script
```

## 3. Requirements & I/O
- **Input (latex_service):** `BookContent` (chapters + sources).
- **Output:** chapter `.tex` fragments under `latex/chapters/generated/` and a
  merged `references.bib`; structural files are hand-authored and stable.
- **Required elements (must compile):** FR-B1 cover, FR-B2 TOC + headers/footers
  (`fancyhdr`), FR-B3 image (`\includegraphics`), FR-B4 Python graph (vector PDF
  from matplotlib), FR-B5 table (`booktabs`), FR-B6 fancy formula (`amsmath`,
  real math), FR-B7 BiDi chapter, FR-B8 TikZ diagram, FR-B9 biber bibliography
  with linked citations (`\cite`, hyperref-linked).
- **Output (compile_service):** `BuildResult(pdf_path, pages, …)`; raises
  `LatexCompileError` (with the tail of the log) on non-zero exit.

## 4. Constraints, alternatives, rationale
- **Engine:** LuaLaTeX required for Hebrew + fontspec; **XeLaTeX** is the allowed
  fallback (same source). pdfLaTeX rejected (poor Unicode/Hebrew).
- **Fonts:** a Hebrew-capable OpenType font must be available to the engine; the
  preamble degrades gracefully and documents the font requirement.
- **Generated vs authored:** the LLM fills **chapter bodies** only; structure,
  preamble and BiDi scaffolding stay human-authored (ADR-6) to guarantee
  compilable, correct RTL/LTR output.
- **Distribution:** TeX Live (used for the v1.0.0 build on Ubuntu/WSL, with
  `fonts-culmus` for David CLM). MiKTeX works on Windows; its Ubuntu `.deb`
  targets older releases and won't satisfy dependencies on Ubuntu 25.10+.

## 5. Success criteria & test scenarios
- **SC-1** Clean build exits 0 and yields `book.pdf`. *Test:* run `build.sh` on a
  clean tree (env with LuaLaTeX); assert exit 0 and PDF exists.
- **SC-2** PDF is ≥ 14 pages. *Test:* `pdfinfo`/`pdfplumber` page count ≥ 14.
- **SC-3** All required elements present. *Test:* checklist + grep of `.tex`
  (\includegraphics, tikzpicture, begin{equation}, \cite, fancyhdr, babel).
- **SC-4** Citations resolve (no `?` markers). *Test:* grep build log for
  undefined-citation warnings → none after full pass sequence.
- **SC-5** `latex_service` escapes/handles content safely. *Test:* feed content
  with LaTeX special chars → assert valid, escaped output.
