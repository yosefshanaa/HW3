#!/usr/bin/env bash
# build.sh [job] — compile a book with the multi-pass sequence the bibliography
# and cross-references need (assignment §13.2):
#   lualatex -> biber -> lualatex -> lualatex
# job defaults to "main" (curated book); pass "main_generated" for the crew book.
# Override the engine with LATEX_ENGINE=xelatex if LuaLaTeX is unavailable.
set -euo pipefail
cd "$(dirname "$0")"

JOB="${1:-main}"
ENGINE="${LATEX_ENGINE:-lualatex}"
RUN="$ENGINE -interaction=nonstopmode -halt-on-error"

echo ">> pass 1/4: $ENGINE"            && $RUN "$JOB.tex"  >/dev/null
echo ">> pass 2/4: biber"              && biber "$JOB"     >/dev/null
echo ">> pass 3/4: $ENGINE"            && $RUN "$JOB.tex"  >/dev/null
echo ">> pass 4/4: $ENGINE"            && $RUN "$JOB.tex"  >/dev/null

OUT="book.pdf"
[ "$JOB" = "main_generated" ] && OUT="book_generated.pdf"
cp "$JOB.pdf" "$OUT"
echo ">> done: $(pwd)/$OUT"
