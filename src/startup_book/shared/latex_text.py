"""Pure helpers to turn (LLM-produced) Markdown into safe LaTeX body text.

Why: crew output is free Markdown that may contain LaTeX-special characters. These
functions escape those characters and map a small Markdown subset to LaTeX, so the
generated chapter fragments compile *and* pick up the book's visual design (styled
sections, ``takeaway`` callout boxes, ``\\cite`` citations) — closing the gap
between the crew-authored book and the curated one. Keeping them pure makes the
mapping easy to unit test (PRD_latex_generation SC-5).
"""

import re

# Single-pass map: each special char maps to its LaTeX-safe form. A one-pass
# regex substitution avoids re-escaping characters that a replacement itself
# inserts (e.g. the braces inside ``\textbackslash{}``).
_LATEX_MAP: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_LATEX_RE = re.compile("|".join(re.escape(key) for key in _LATEX_MAP))

# Markdown citation: ``[@ries2011lean]`` or ``[@a2020,b2021]`` -> ``\cite{...}``.
_CITE_RE = re.compile(r"\[@([\w,]+)\]")
# Index placeholder used to carry citation keys through escaping untouched (the
# null byte and digits are never LaTeX-special, so escaping leaves them intact).
_CITE_HOLE = re.compile("\x00C(\\d+)\x00")


def escape_latex(text: str) -> str:
    """Escape LaTeX-special characters in plain text.

    Args:
        text: Raw text that may contain ``& % $ # _ { } ~ ^ \\``.

    Returns:
        The text with each special character replaced by its LaTeX-safe form.
    """
    return _LATEX_RE.sub(lambda match: _LATEX_MAP[match.group()], text)


def _emphasis(text: str) -> str:
    """Convert ``**bold**`` to ``\\textbf{bold}`` on already-escaped text."""
    parts = text.split("**")
    if len(parts) % 2 == 0:  # unbalanced markers — leave as-is
        return text
    out = []
    for index, part in enumerate(parts):
        out.append(rf"\textbf{{{part}}}" if index % 2 else part)
    return "".join(out)


def _inline(text: str) -> str:
    """Apply inline markup to one raw run: citations + ``**bold**``, safely escaped.

    Citations are stashed as indexed placeholders *before* escaping so that keys
    containing ``_`` survive intact, then restored as ``\\cite{...}`` afterwards.
    """
    keys: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        keys.append(match.group(1))
        return f"\x00C{len(keys) - 1}\x00"

    text = _CITE_RE.sub(_stash, text)
    text = _emphasis(escape_latex(text))
    return _CITE_HOLE.sub(lambda m: rf"\cite{{{keys[int(m.group(1))]}}}", text)


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
            out.append(rf"\subsection{{{_inline(line[4:])}}}")
        elif line.startswith("## "):
            flush_all()
            out.append(rf"\section{{{_inline(line[3:])}}}")
        elif line.startswith("# "):
            flush_all()
            out.append(rf"\section{{{_inline(line[2:])}}}")
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
