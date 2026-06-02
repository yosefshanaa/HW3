"""Pure helpers to turn (LLM-produced) Markdown into safe LaTeX body text.

Why: crew output is free Markdown that may contain LaTeX-special characters. These
functions escape those characters and map a small Markdown subset to LaTeX, so the
generated chapter fragments compile. Keeping them pure makes escaping easy to unit
test (PRD_latex_generation SC-5).
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


def markdown_to_latex(markdown: str) -> str:
    """Convert a small Markdown subset to LaTeX body text.

    Supports ``##``/``###`` headings, ``-``/``*`` bullet lists, ``**bold**`` and
    paragraphs. All other text is escaped and emitted as paragraphs.
    """
    lines = markdown.splitlines()
    out: list[str] = []
    bullets: list[str] = []

    def flush_bullets() -> None:
        if not bullets:
            return
        out.append("\\begin{itemize}")
        out.extend(rf"  \item {item}" for item in bullets)
        out.append("\\end{itemize}")
        bullets.clear()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            out.append("")
        elif line.startswith("### "):
            flush_bullets()
            out.append(rf"\subsection{{{_emphasis(escape_latex(line[4:]))}}}")
        elif line.startswith("## "):
            flush_bullets()
            out.append(rf"\section{{{_emphasis(escape_latex(line[3:]))}}}")
        elif line.lstrip().startswith(("- ", "* ")):
            bullets.append(_emphasis(escape_latex(line.lstrip()[2:])))
        else:
            flush_bullets()
            out.append(_emphasis(escape_latex(line)))
    flush_bullets()
    return "\n".join(out).strip() + "\n"
