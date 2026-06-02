"""Unit tests for the Markdown -> LaTeX text helpers (PRD_latex_generation SC-5)."""

from __future__ import annotations

from startup_book.shared.latex_text import escape_latex, markdown_to_latex


def test_escape_specials() -> None:
    assert escape_latex("100% & cost_$") == r"100\% \& cost\_\$"


def test_escape_backslash_first() -> None:
    # The backslash must be escaped before the braces it introduces.
    assert escape_latex("a\\b") == r"a\textbackslash{}b"


def test_headings() -> None:
    out = markdown_to_latex("## Title\n### Sub")
    assert r"\section{Title}" in out
    assert r"\subsection{Sub}" in out


def test_bullets_grouped_in_itemize() -> None:
    out = markdown_to_latex("- one\n- two")
    assert out.count(r"\begin{itemize}") == 1
    assert out.count(r"\item") == 2
    assert r"\end{itemize}" in out


def test_bold_conversion() -> None:
    assert r"\textbf{x}" in markdown_to_latex("body **x** end")


def test_unbalanced_bold_left_intact() -> None:
    # An odd number of ** markers is not converted (kept escaped/plain).
    assert r"\textbf" not in markdown_to_latex("a ** b")


def test_special_chars_in_body_escaped() -> None:
    assert r"\%" in markdown_to_latex("growth of 50%")
