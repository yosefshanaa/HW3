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
            "עבור כל פרק אסוף 4-6 עובדות מפתח מדויקות, מספרים/דוגמאות קונקרטיות, "
            "ולפחות מקור אמין אחד. לכל מקור קבע מפתח ציטוט יציב באנגלית בסגנון "
            "authorYEARword (למשל ries2011lean) — זהו המפתח שישמש בציטוטים ובביבליוגרפיה."
        ),
        expected_output=(
            "תקציר מחקר מובנה לכל פרק: עובדות, מספרים, ורשימת מקורות עם מפתח, "
            "כותרת, מחבר ושנה."
        ),
        agent=agents["researcher"],
    )
    write = Task(
        description=(
            "בהתבסס על המחקר, כתוב כל פרק בעברית ברורה ומובנית, בפורמט Markdown. "
            "אורך הוא דרישה קשיחה — כל פרק חייב להכיל לפחות 450 מילים. כל פרק כולל:\n"
            "- 3-4 כותרות-משנה בשורה שמתחילה ב-'## ';\n"
            "- תחת כל כותרת-משנה פסקה מלאה ועשירה של 110-150 מילים — הסבר, נימוק "
            "ודוגמה קונקרטית; לעולם לא משפט בודד או רשימה בלבד;\n"
            "- הדגשה של מונחי מפתח ב-**מודגש**, ושמירת מונחים טכניים באנגלית;\n"
            "- ציטוט אחד לפחות בפורמט [@key] באמצעות מפתחות המקורות מהמחקר;\n"
            "- שורת סיכום אחת שמתחילה ב-'> ' (תיהפך לתיבת 'שורה תחתונה').\n"
            "אל תקצר כדי לחסוך מקום — פרק קצר מ-450 מילים אינו תקין."
        ),
        expected_output=(
            "טיוטות פרקים מלאות ב-Markdown, כל פרק לפחות 450 מילים, עם 3-4 "
            "כותרות-משנה (פסקה מלאה לכל אחת), מונחים מודגשים, ציטוט [@key] ושורת '> '."
        ),
        agent=agents["writer"],
        context=[research],
    )
    review = Task(
        description=(
            "ערוך והעשר כל פרק: דיוק עובדתי, בהירות ומבנה לוגי. **אל תקצר** — "
            "תפקידך להעשיר. אם פסקה קצרה מ-110 מילים או פרק קצר מ-450 מילים, הרחב "
            "אותם בעובדות, נימוקים ודוגמאות; שמור על אורך של לפחות 450 מילים לפרק. "
            "שמר על מבנה ה-Markdown: כותרות '## ', מונחים **מודגשים**, ציטוטי "
            "[@key] ושורת '> ' המסכמת. החזר את הגרסה המלאה והמלוטשת."
        ),
        expected_output="פרקים מלוטשים ומורחבים ב-Markdown (לפחות 450 מילים לפרק).",
        agent=agents["reviewer"],
        context=[write],
    )
    latex = Task(
        description=(
            "מפה את הפרקים המלוטשים למבנה BookContent: לכל פרק id, heading, "
            "body_markdown ו-language ('he' או 'mixed'). שמר ב-body_markdown את "
            "כל סימוני ה-Markdown כפי שהם (## כותרות-משנה, **מודגש**, [@key] "
            "לציטוטים, '> ' לשורה תחתונה) — אל תמיר אותם לטקסט שטוח. רכז את "
            "המקורות לביבליוגרפיה (key, title, author, year), כאשר ה-key תואם "
            "למפתחות הציטוט שבפרוזה."
        ),
        expected_output=(
            "אובייקט BookContent תקין עם כל הפרקים (body_markdown עשיר) והמקורות."
        ),
        agent=agents["latex"],
        context=[review],
        output_pydantic=BookContent,
    )
    return [research, write, review, latex]
