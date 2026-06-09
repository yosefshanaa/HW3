"""Block-level Markdown -> LaTeX conversion (headings, lists, blockquotes).

Why: turns the crew's Markdown chapter body into LaTeX, delegating inline markup
(escaping, citations, embedded-English BiDi, ``**bold**``) to ``latex_text``.
Split from the inline helpers so each module stays small and single-purpose.
"""

from __future__ import annotations

from startup_book.shared.latex_text import _inline


def markdown_to_latex(markdown: str) -> str:
    """Convert a small Markdown subset to LaTeX body text.

    Supports headings (``#``/``##`` -> ``\\section``, ``###`` -> ``\\subsection``),
    ``-``/``*`` bullet lists, ``> ...`` blockquotes (rendered as a ``takeaway``
    callout box), ``**bold**``, ``[@key]`` citations, and paragraphs. Everything
    else is escaped and emitted as paragraph text.
    """
    lines = markdown.splitlines()
    out: list[str] = []
    bullets: list[str] = []
    quote: list[str] = []

    def flush_bullets() -> None:
        if not bullets:
            return
        out.append("\\begin{itemize}")
        out.extend(rf"  \item {item}" for item in bullets)
        out.append("\\end{itemize}")
        bullets.clear()

    def flush_quote() -> None:
        if not quote:
            return
        out.append("\\begin{takeaway}")
        out.append(" ".join(quote))
        out.append("\\end{takeaway}")
        quote.clear()

    def flush_all() -> None:
        flush_bullets()
        flush_quote()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_all()
            out.append("")
        elif line.startswith("### "):
            flush_all()
            out.append(rf"\subsection{{{_inline(line[4:], heading=True)}}}")
        elif line.startswith("## "):
            flush_all()
            out.append(rf"\section{{{_inline(line[3:], heading=True)}}}")
        elif line.startswith("# "):
            flush_all()
            out.append(rf"\section{{{_inline(line[2:], heading=True)}}}")
        elif line.lstrip().startswith("> "):
            flush_bullets()
            quote.append(_inline(line.lstrip()[2:]))
        elif line.lstrip().startswith(("- ", "* ")):
            flush_quote()
            bullets.append(_inline(line.lstrip()[2:]))
        else:
            flush_all()
            out.append(_inline(line))
    flush_all()
    return "\n".join(out).strip() + "\n"
