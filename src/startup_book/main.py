"""Thin command-line entry point (no business logic — guidelines §4).

Why: the CLI only parses arguments and delegates to :class:`BookBuilderSDK`. All
logic lives behind the SDK so the same behaviour is reachable from tests or any
future interface. This module is excluded from coverage (it is an adapter).
"""

from __future__ import annotations

import argparse
import logging
import sys

from startup_book import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser with the available subcommands."""
    parser = argparse.ArgumentParser(
        prog="startup-book",
        description="Generate and typeset a Hebrew/English startup mini-book.",
    )
    parser.add_argument("--version", action="version", version=f"startup-book {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="run the full pipeline and compile the PDF")
    build.add_argument("--topic", default=None, help="override the book topic")

    sub.add_parser("figures", help="(re)generate the Python figures only")
    sub.add_parser("content", help="run the crew and print chapter headings only")

    audit = sub.add_parser("audit", help="report LaTeX build health from the compiler log")
    audit.add_argument("--log", default=None, help="path to a .log (defaults to latex/main.log)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code.

    Args:
        argv: Optional argument list (defaults to ``sys.argv``).
    """
    from startup_book.shared.logging_setup import configure_logging

    try:
        configure_logging()  # JSON-line logs + secret redaction (§7.4)
    except Exception:  # pragma: no cover - never let logging setup crash the CLI
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)

    from startup_book import BookBuilderSDK

    sdk = BookBuilderSDK()
    if args.command == "figures":
        paths = sdk.make_figures()
        print(f"Generated {len(paths)} figure(s).")
        return 0
    if args.command == "content":
        content = sdk.generate_content(args.topic)
        for chapter in content.chapters:
            print(f"- {chapter.heading}")
        return 0
    if args.command == "audit":
        from pathlib import Path

        report = sdk.audit(Path(args.log) if args.log else None)
        print(f"Log:                 {report.log_path}")
        print(f"Pages:               {report.pages}")
        print(f"Overfull boxes:      {report.overfull}")
        print(f"Missing glyphs:      {report.missing_glyphs}")
        print(f"Undefined citations: {report.undefined_citations}")
        print("Health: OK" if report.healthy else "Health: ISSUES FOUND")
        return 0 if report.healthy else 1
    result = sdk.build(args.topic)
    print(f"PDF: {result.pdf_path} ({result.pages} pages)")
    print(f"Tokens: {result.token_usage.total_tokens} · est. ${result.estimated_cost_usd}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
