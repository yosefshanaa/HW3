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


def test_empty_input_yields_empty_body() -> None:
    assert markdown_to_latex("") == "\n"


def test_bullets_flushed_before_following_paragraph() -> None:
    # A paragraph that directly follows a bullet must close the list first.
    out = markdown_to_latex("- one\n- two\nplain paragraph")
    assert out.index(r"\end{itemize}") < out.index("plain paragraph")


def test_star_bullets_supported() -> None:
    out = markdown_to_latex("* a\n* b")
    assert out.count(r"\item") == 2


def test_single_hash_heading_becomes_section() -> None:
    # A lone "# " maps to \section (the \chapter title is emitted separately).
    assert r"\section{Intro}" in markdown_to_latex("# Intro")


def test_citation_converted() -> None:
    out = markdown_to_latex("As shown [@ries2011lean] this works.")
    assert r"\cite{ries2011lean}" in out


def test_multi_key_citation() -> None:
    out = markdown_to_latex("see [@a2020,b2021]")
    assert r"\cite{a2020,b2021}" in out


def test_citation_key_with_underscore_survives_escaping() -> None:
    # The key must NOT be mangled into key\_word by the LaTeX escaper.
    out = markdown_to_latex("ref [@key_word]")
    assert r"\cite{key_word}" in out
    assert r"key\_word" not in out


def test_blockquote_becomes_takeaway_box() -> None:
    out = markdown_to_latex("> the bottom line")
    assert r"\begin{takeaway}" in out
    assert r"\end{takeaway}" in out
    assert "the bottom line" in out


def test_blockquote_flushed_before_paragraph() -> None:
    out = markdown_to_latex("> note\nplain after")
    assert out.index(r"\end{takeaway}") < out.index("plain after")


def test_citation_inside_bold_and_bullets() -> None:
    out = markdown_to_latex("- **key** point [@ries2011lean]")
    assert r"\textbf{key}" in out
    assert r"\cite{ries2011lean}" in out
