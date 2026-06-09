"""CrewAI task factory — the per-chapter, context-chained workflow.

Why: tasks declare *what* each agent must do and how their outputs connect. The
``context`` argument is the glue (lecture: "Context is the bridge"): the writer
builds on the researcher, the reviewer on the writer, and the LaTeX engineer
emits a structured :class:`BookContent`. The crew runs **once per chapter** so
each chapter gets the full output budget and comes out full-length, rather than
rationing one short response across the whole book. ``{topic}`` is filled by
``crew.kickoff(inputs=...)``; the chapter heading is baked into the descriptions.
"""

from __future__ import annotations

from crewai import Agent, Task

from startup_book.shared.models import BookContent


def build_chapter_tasks(agents: dict[str, Agent], heading: str) -> list[Task]:
    """Build the four chained tasks that author ONE chapter (in run order).

    Args:
        agents: The role-keyed crew agents.
        heading: The Hebrew heading of the chapter to author.
    """
    research = Task(
        description=(
            f"חקור לעומק את הנושא '{{topic}}' עבור פרק יחיד שכותרתו: '{heading}'. "
            "אסוף 6-8 עובדות מפתח מדויקות, מספרים ודוגמאות קונקרטיות מהעולם האמיתי, "
            "ולפחות שני מקורות אמינים. לכל מקור קבע מפתח ציטוט יציב באנגלית בסגנון "
            "authorYEARword (למשל ries2011lean) — זהו המפתח שישמש בציטוט ובביבליוגרפיה."
        ),
        expected_output=(
            f"תקציר מחקר עשיר לפרק '{heading}': עובדות, מספרים, דוגמאות ורשימת "
            "מקורות עם מפתח, כותרת, מחבר ושנה."
        ),
        agent=agents["researcher"],
    )
    write = Task(
        description=(
            f"בהתבסס על המחקר, כתוב פרק מלא ומעמיק בעברית שכותרתו '{heading}', "
            "בפורמט Markdown. אורך הוא דרישה קשיחה — לפחות 600 מילים. הפרק כולל:\n"
            "- 5-6 כותרות-משנה בשורה שמתחילה ב-'## ';\n"
            "- תחת כל כותרת-משנה פסקה מלאה ועשירה של 110-150 מילים — הסבר, נימוק "
            "ודוגמה קונקרטית; לעולם לא משפט בודד או רשימה בלבד;\n"
            "- הדגשה של מונחי מפתח ב-**מודגש**, ושמירת מונחים טכניים באנגלית;\n"
            "- ציטוט אחד לפחות בפורמט [@key] באמצעות מפתחות המקורות מהמחקר;\n"
            "- שורת סיכום אחת שמתחילה ב-'> ' (תיהפך לתיבת 'שורה תחתונה').\n"
            "אל תקצר כדי לחסוך מקום — פרק קצר מ-600 מילים אינו תקין."
        ),
        expected_output=(
            "פרק מלא ב-Markdown (לפחות 600 מילים), עם 5-6 כותרות-משנה (פסקה מלאה "
            "לכל אחת), מונחים מודגשים, ציטוט [@key] ושורת '> ' מסכמת."
        ),
        agent=agents["writer"],
        context=[research],
    )
    review = Task(
        description=(
            "ערוך והעשר את הפרק: דיוק עובדתי, בהירות ומבנה לוגי. **אל תקצר** — "
            "תפקידך להעשיר. אם פסקה קצרה מ-110 מילים או הפרק קצר מ-600 מילים, הרחב "
            "אותם בעובדות, נימוקים ודוגמאות. שמר על מבנה ה-Markdown: כותרות '## ', "
            "מונחים **מודגשים**, ציטוטי [@key] ושורת '> ' המסכמת. החזר את הגרסה המלאה."
        ),
        expected_output="פרק מלוטש ומורחב ב-Markdown (לפחות 600 מילים).",
        agent=agents["reviewer"],
        context=[write],
    )
    latex = Task(
        description=(
            "מפה את הפרק המלוטש למבנה BookContent עם פרק יחיד: id קצר, heading "
            f"('{heading}'), body_markdown ו-language ('he' או 'mixed'). שמר "
            "ב-body_markdown את כל סימוני ה-Markdown כפי שהם (## כותרות, **מודגש**, "
            "[@key], '> '). רכז את המקורות (key, title, author, year) כאשר ה-key "
            "תואם למפתחות הציטוט שבפרוזה."
        ),
        expected_output="אובייקט BookContent תקין עם הפרק היחיד (body_markdown עשיר) והמקורות.",
        agent=agents["latex"],
        context=[review],
        output_pydantic=BookContent,
    )
    return [research, write, review, latex]
