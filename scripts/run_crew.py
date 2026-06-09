"""One-off: run the CrewAI pipeline, render generated LaTeX, save evidence.

Regenerates ``latex/generated/`` from a live crew run and records the raw output
under ``results/`` as evidence that the agents really produced the book. After
running this, compile the agent book with ``cd latex && ./build.sh main_generated``.
"""

from __future__ import annotations

import time

from startup_book import BookBuilderSDK
from startup_book.constants import REPO_ROOT


def main() -> None:
    sdk = BookBuilderSDK()
    content = sdk.generate_content()
    sdk.render_latex(content)

    print(f"chapters: {len(content.chapters)}  sources: {len(content.sources)}")
    for i, ch in enumerate(content.chapters, 1):
        words = len(ch.body_markdown.split())
        sections = ch.body_markdown.count("\n## ") + ch.body_markdown.startswith("## ")
        print(f"  {i:02d}-{i}: {words:4d} words · {sections} sections · {ch.heading[:40]}")

    out = REPO_ROOT / "results" / f"crew_output_{int(time.time())}.json"
    out.write_text(content.model_dump_json(indent=2), encoding="utf-8")
    print(f"evidence: {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
