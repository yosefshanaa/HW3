"""CrewAI agent factory (the four role-specialised workers).

Why: per the lecture's article-writing pattern and ``PRD_crewai_pipeline.md``,
the crew is a Researcher -> Writer -> Reviewer -> LaTeX Engineer team. Each agent
carries a role/goal/backstory (its system prompt) and the shared LLM. Definitions
live here, separate from task wiring (``tasks.py``), to respect the 150-LOC rule
and single-responsibility.
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

# The book is Hebrew-first; this reminder is appended to every backstory so the
# whole crew stays consistent about language and BiDi conventions.
_HE = (
    "כתוב בעברית תקנית וברורה. השאר מונחים טכניים באנגלית (כגון "
    "MVP, Product-Market Fit, CAC) באנגלית, ושלב אותם באופן טבעי בתוך הטקסט."
)


def build_agents(llm: Any) -> dict[str, Agent]:
    """Construct the four crew agents bound to a shared LLM.

    Args:
        llm: The LLM the agents use (a ``crewai.LLM`` or a model-name string).

    Returns:
        Mapping of ``researcher``/``writer``/``reviewer``/``latex`` to agents.
    """
    researcher = Agent(
        role="Startup Research Analyst",
        goal="Extract accurate, structured key facts for each requested chapter topic",
        backstory=(
            "אתה אנליסט מחקר קפדן המתמחה בבניית סטארט-אפים. אתה מזקק עובדות "
            "מדויקות ומקורות אמינים מתוך חומרי הרקע שניתנו לך. " + _HE
        ),
        llm=llm,
        verbose=True,
    )
    writer = Agent(
        role="Senior Startup Author",
        goal="Turn research into clear, well-structured Hebrew book chapters",
        backstory=(
            "אתה סופר טכני בכיר שהופך מחקר גולמי לפרקי ספר נגישים וזורמים. "
            "אתה כותב מתוך ההקשר שמספק החוקר, בלי להמציא עובדות. " + _HE
        ),
        llm=llm,
        verbose=True,
    )
    reviewer = Agent(
        role="Senior Editor",
        goal="Improve factual accuracy, clarity and structure without changing meaning",
        backstory=(
            "אתה עורך בכיר. אתה בודק דיוק עובדתי, משפר בהירות ומבנה, ולעולם "
            "אינך משנה את המשמעות המקורית. " + _HE
        ),
        llm=llm,
        verbose=True,
    )
    latex = Agent(
        role="LaTeX Typesetter",
        goal="Map the reviewed chapters into a structured BookContent payload",
        backstory=(
            "אתה מומחה LaTeX. אתה ממפה פרקים ערוכים למבנה נתונים מסודר "
            "(כותרת, גוף, שפה) ומרכז את רשימת המקורות לביבליוגרפיה. " + _HE
        ),
        llm=llm,
        verbose=True,
    )
    return {"researcher": researcher, "writer": writer, "reviewer": reviewer, "latex": latex}
