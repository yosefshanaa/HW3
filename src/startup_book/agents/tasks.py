"""CrewAI task factory — the sequential, context-chained workflow.

Why: tasks declare *what* each agent must do and how their outputs connect. The
``context`` argument is the glue (lecture: "Context is the bridge"): the writer
builds on the researcher, the reviewer on the writer, and the LaTeX engineer
emits a structured :class:`BookContent`. ``{topic}`` and ``{outline}`` are filled
by ``crew.kickoff(inputs=...)``.
"""

from __future__ import annotations

from crewai import Agent, Task

from startup_book.shared.models import BookContent


def build_tasks(agents: dict[str, Agent]) -> list[Task]:
    """Build the four chained tasks for the given agents (in run order)."""
    research = Task(
        description=(
            "חקור את הנושא '{topic}' עבור ספרון סטארט-אפ עם הפרקים הבאים:\n"
            "{outline}\n"
            "עבור כל פרק, אסוף עובדות מפתח מדויקות ומקורות אמינים."
        ),
        expected_output="תקציר מחקר מובנה לכל פרק, עם עובדות ומקורות.",
        agent=agents["researcher"],
    )
    write = Task(
        description=(
            "בהתבסס על המחקר, כתוב כל פרק בעברית ברורה ומובנית. שמור על מונחי "
            "אנגלית טכניים היכן שטבעי. הפק טיוטה לכל כותרת בראשי הפרקים."
        ),
        expected_output="טיוטות פרקים מלאות בעברית, פרק לכל כותרת.",
        agent=agents["writer"],
        context=[research],
    )
    review = Task(
        description=(
            "ערוך ושפר כל פרק: דיוק עובדתי, בהירות ומבנה לוגי. אל תשנה את "
            "המשמעות המקורית. החזר את הגרסה המלוטשת."
        ),
        expected_output="פרקים מלוטשים ומוכנים לטיפוגרפיה.",
        agent=agents["reviewer"],
        context=[write],
    )
    latex = Task(
        description=(
            "מפה את הפרקים המלוטשים למבנה BookContent: לכל פרק id, heading, "
            "body_markdown ו-language ('he' או 'mixed'). רכז את המקורות "
            "לביבליוגרפיה (key, title, author, year)."
        ),
        expected_output="אובייקט BookContent תקין עם כל הפרקים והמקורות.",
        agent=agents["latex"],
        context=[review],
        output_pydantic=BookContent,
    )
    return [research, write, review, latex]
