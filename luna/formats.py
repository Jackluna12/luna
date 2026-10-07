"""Output renderers: txt, xml (Claude-style), and json."""
from __future__ import annotations

import json
import time
from html import escape as _escape


def render_tree(paths: list[str]) -> str:
    """Render an ASCII directory tree from repo-relative paths."""
    tree: dict = {}
    for p in sorted(paths):
        node = tree
        for part in p.split("/"):
            node = node.setdefault(part, {})
    lines: list[str] = []

    def walk(node: dict, prefix: str) -> None:
        items = sorted(node.items())
        for i, (name, children) in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{name}")
            walk(children, prefix + ("    " if last else "│   "))

    walk(tree, "")
    return "\n".join(lines)


def render_txt(tree: str, sections: list[tuple[str, str, int]],
               stats: dict, skipped: list[tuple[str, int]]) -> str:
    out = [
        f"Luna context — generated {time.strftime('%Y-%m-%d %H:%M')}",
        f"Files: {stats['files']} kept, {len(skipped)} skipped | "
        f"Tokens: ~{stats['tokens']}"
        + (f" / {stats['budget']} budget" if stats.get("budget") else ""),
        "=" * 60,
        "",
        "## Project tree",
        tree,
        "",
    ]
    for rel, content, tokens in sections:
        out.append(f"## File: {rel} (~{tokens} tokens)")
        out.append(content.rstrip())
        out.append("")
    if skipped:
        out.append("## Skipped (over budget)")
        out.extend(f"- {rel} (~{tok} tokens)" for rel, tok in skipped)
    return "\n".join(out)


def render_xml(sections: list[tuple[str, str, int]], stats: dict,
               skipped: list[tuple[str, int]]) -> str:
    out = ["<documents>"]
    for i, (rel, content, _tokens) in enumerate(sections, 1):
        out.append(f'<document index="{i}">')
        out.append(f"<source>{_escape(rel)}</source>")
        out.append("<document_content>")
        out.append(_escape(content.rstrip()))
        out.append("</document_content>")
        out.append("</document>")
    out.append("</documents>")
    if skipped:
        names = ", ".join(rel for rel, _ in skipped)
        out.append(f"<!-- skipped over budget: {_escape(names)} -->")
    return "\n".join(out)


def render_json(sections: list[tuple[str, str, int]], stats: dict,
                skipped: list[tuple[str, int]]) -> str:
    return json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "stats": stats,
        "files": [
            {"path": rel, "tokens": tokens, "content": content.rstrip()}
            for rel, content, tokens in sections
        ],
        "skipped": [
            {"path": rel, "tokens": tokens} for rel, tokens in skipped
        ],
    }, ensure_ascii=False, indent=2)


RENDERERS = {"txt": render_txt, "xml": render_xml, "json": render_json}
