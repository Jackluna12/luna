#!/usr/bin/env python3
"""Luna 2.0 — intelligent codebase context engine for LLM workflows.

Examples:
    python main.py                          # signatures mode, txt output
    python main.py -o ctx.xml -f xml         # Claude-style XML
    python main.py --budget 8000             # stay under ~8k tokens
    python main.py --changed                 # only files changed vs HEAD
    python main.py --staged -o staged.json -f json
    python main.py --mode full --lines 20    # legacy full-head mode
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from luna import Luna  # noqa: E402
from luna import __version__  # noqa: E402
from luna.git import GitError, is_git_repo  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=f"Luna {__version__}: turn a codebase into LLM-ready context.")
    p.add_argument("root", nargs="?", default=".",
                   help="project root to scan (default: .)")
    p.add_argument("-o", "--output", default="luna_context.txt",
                   help="output file (default: luna_context.txt)")
    p.add_argument("-f", "--format", default="txt",
                   choices=["txt", "xml", "json"],
                   help="output format (default: txt)")
    p.add_argument("--mode", default="signatures",
                   choices=["signatures", "full"],
                   help="signatures: AST/heuristic summaries (default); "
                        "full: first N lines of every file")
    p.add_argument("--budget", type=int, default=None, metavar="TOKENS",
                   help="max estimated tokens; files beyond budget are skipped")
    p.add_argument("--lines", type=int, default=10,
                   help="head lines per file in full mode (default: 10)")
    p.add_argument("--ext", action="append", default=[],
                   help="extra extension to include, e.g. --ext .vue (repeatable)")
    p.add_argument("--ignore", action="append", default=[],
                   help="extra name to ignore (repeatable)")
    p.add_argument("--max-size", type=int, default=256, metavar="KB",
                   help="skip reading files larger than this (default: 256 KB)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--changed", action="store_true",
                   help="only include files changed vs HEAD (with diffs)")
    g.add_argument("--staged", action="store_true",
                   help="only include staged changes (with diffs)")
    p.add_argument("--ref", default=None, metavar="REF",
                   help="only include files changed vs another ref, e.g. main")
    p.add_argument("--no-tree", action="store_true",
                   help="omit the project tree from txt output")
    p.add_argument("--no-gitignore", action="store_true",
                   help="ignore .gitignore files while scanning")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main() -> int:
    args = build_parser().parse_args()

    git_mode = "changed" if args.changed else ("staged" if args.staged else None)
    if (git_mode or args.ref) and not is_git_repo(Path(args.root)):
        print(f"error: '{args.root}' is not a git repository", file=sys.stderr)
        return 1

    exts = {e if e.startswith(".") else "." + e for e in args.ext}
    luna = Luna(
        root=args.root,
        output_format=args.format,
        mode=args.mode,
        budget=args.budget,
        head_lines=args.lines,
        extra_exts=exts,
        extra_ignore=set(args.ignore),
        max_size=args.max_size * 1024,
        follow_gitignore=not args.no_gitignore,
        include_tree=not args.no_tree,
        git_mode=git_mode,
        git_ref=args.ref,
    )
    try:
        stats = luna.export(args.output)
    except GitError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    budget_note = f" / {stats.budget}" if stats.budget else ""
    print(f"✅ Luna context written to {args.output}")
    print(f"   {stats.files} files, ~{stats.tokens} tokens{budget_note}, "
          f"{stats.skipped} skipped over budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
