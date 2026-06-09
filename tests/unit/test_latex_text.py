"""Unit tests for the Markdown -> LaTeX text helpers (PRD_latex_generation SC-5)."""

from __future__ import annotations

from startup_book.shared.latex_text import escape_latex, heading_to_latex, markdown_to_latex


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


def test_parenthesised_english_wrapped_in_en() -> None:
    # The reported BiDi bug: "(English)" inside Hebrew must become one LTR span.
    out = markdown_to_latex("עלות ה-CAC (Customer Acquisition Cost) חשובה")
    assert r"\en{(Customer Acquisition Cost)}" in out


def test_parenthesised_english_in_heading_uses_texorpdfstring() -> None:
    # In a heading the \en must be shielded from the PDF bookmark via texorpdfstring.
    out = markdown_to_latex("## הבנת ה-CAC (Customer Acquisition Cost)")
    assert r"\texorpdfstring{\en{(Customer Acquisition Cost)}}{(Customer Acquisition Cost)}" in out


def test_hebrew_only_parentheses_not_wrapped() -> None:
    # Parentheses around Hebrew (or no Latin letter) are left untouched.
    out = markdown_to_latex("מודל (כללי) ופשוט (123)")
    assert r"\en{" not in out


def test_english_paren_with_special_char_is_escaped_inside_en() -> None:
    out = markdown_to_latex("מדד (R&D ratio) עולה")
    assert r"\en{(R\&D ratio)}" in out


def test_heading_to_latex_wraps_parenthesised_english() -> None:
    # A \chapter title with parenthesised English must be wrapped (bookmark-safe).
    out = heading_to_latex("מוצר-שוק (Product–Market Fit)")
    assert r"\texorpdfstring{\en{(Product–Market Fit)}}{(Product–Market Fit)}" in out


def test_heading_to_latex_plain_hebrew_unchanged() -> None:
    assert heading_to_latex("מבוא") == "מבוא"


def test_bold_inside_english_parens_is_converted() -> None:
    # **bold** trapped inside a parenthesised English run must still become \textbf.
    out = markdown_to_latex("חשוב (**MVP**) כאן")
    assert r"\en{(\textbf{MVP})}" in out
    assert "**" not in out


def test_citation_inside_english_parens_not_swallowed() -> None:
    # A citation inside an English parenthetical must still become \cite, not be
    # absorbed into the \en run.
    out = markdown_to_latex("ראו (Lean Startup [@ries2011lean]) כאן")
    assert r"\cite{ries2011lean}" in out
