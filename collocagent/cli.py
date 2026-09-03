"""Command-line interface for the standalone CollocAgent."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agents import CollocAgent
from .corpus import CorpusIndex

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "data" / "rules.json"
DEFAULT_INDEX = ROOT / "data" / "collocagent.sqlite3"
DEFAULT_DEMO = ROOT / "data" / "demo_corpus.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="collocagent")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-index", help="Index plain-text corpus files")
    build.add_argument("files", nargs="+", type=Path)
    build.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    build.add_argument("--name", default="User-supplied corpus")
    build.add_argument("--window", type=int, default=4)

    demo = sub.add_parser("build-demo", help="Build the bundled synthetic demo index")
    demo.add_argument("--index", type=Path, default=DEFAULT_INDEX)

    analyze = sub.add_parser("analyze", help="Analyze a sentence or paragraph")
    analyze.add_argument("text")
    analyze.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    analyze.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    analyze.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-index":
        meta = CorpusIndex(args.index).build(
            args.files, corpus_name=args.name, window=args.window
        )
        print(json.dumps(meta, indent=2))
        return 0
    if args.command == "build-demo":
        meta = CorpusIndex(args.index).build(
            [DEFAULT_DEMO],
            corpus_name="Bundled synthetic demo corpus (not research evidence)",
            window=4,
        )
        print(json.dumps(meta, indent=2))
        return 0
    if args.command == "analyze":
        result = CollocAgent(args.rules, args.index).analyze(args.text)
        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
