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
# Index placeholders carry stashed runs through escaping untouched (the control
# bytes \x00 / \x01 and digits are never LaTeX-special). \x00 = citation key,
# \x01 = embedded-English run.
_CITE_HOLE = re.compile("\x00(\\d+)\x00")
_EN_HOLE = re.compile("\x01(\\d+)\x01")

# A parenthesised English phrase such as ``(Customer Acquisition Cost)`` must
# render as ONE left-to-right span — parentheses included — or babel's bidi
# mis-orders the brackets inside the Hebrew (RTL) line. Match ``(...)`` whose
# interior holds a Latin letter and no Hebrew/stash byte, so it is safe to flip
# the whole group LTR via ``\en`` (\foreignlanguage english).
_NOT_EN = r"[^()֐-׿\x00\x01]"  # not paren, Hebrew, or a stash byte
_EN_PAREN = re.compile(rf"\({_NOT_EN}*[A-Za-z]{_NOT_EN}*\)")


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


def _english_span(raw: str, heading: bool) -> str:
    """Wrap a raw English run in ``\\en{...}`` (forced LTR + Latin font).

    Inside a heading the span is shielded with ``\\texorpdfstring`` so the PDF
    bookmark gets plain text (``\\foreignlanguage`` is illegal in a bookmark).
    """
    span = rf"\en{{{_emphasis(escape_latex(raw))}}}"
    if heading:
        return rf"\texorpdfstring{{{span}}}{{{raw.replace('**', '')}}}"
    return span


def _inline(text: str, *, heading: bool = False) -> str:
    """Apply inline markup to one raw run: citations, embedded English, ``**bold**``.

    Citations and parenthesised English runs are stashed as indexed placeholders
    *before* escaping (so keys with ``_`` and the English text survive intact),
    then restored afterwards as ``\\cite{...}`` and ``\\en{...}`` respectively.
    """
    keys: list[str] = []
    runs: list[str] = []

    def _stash_cite(match: re.Match[str]) -> str:
        keys.append(match.group(1))
        return f"\x00{len(keys) - 1}\x00"

    def _stash_english(match: re.Match[str]) -> str:
        runs.append(match.group(0))
        return f"\x01{len(runs) - 1}\x01"

    text = _CITE_RE.sub(_stash_cite, text)
    text = _EN_PAREN.sub(_stash_english, text)
    text = _emphasis(escape_latex(text))
    text = _EN_HOLE.sub(lambda m: _english_span(runs[int(m.group(1))], heading), text)
    return _CITE_HOLE.sub(lambda m: rf"\cite{{{keys[int(m.group(1))]}}}", text)


def heading_to_latex(text: str) -> str:
    """Convert a heading string (e.g. a ``\\chapter`` title) to LaTeX.

    Escapes specials and wraps embedded parenthesised English in ``\\en{...}``,
    shielded by ``\\texorpdfstring`` so the PDF bookmark stays plain — the same
    treatment ``##`` section headings get.
    """
    return _inline(text, heading=True)


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
