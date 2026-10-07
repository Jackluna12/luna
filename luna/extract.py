"""Content extraction.

- Python files: real AST parsing — module docstring, condensed imports,
  and class/function signatures with docstring first-lines. Bodies are
  dropped, which is far denser than grabbing the first N lines.
- Other code: heuristic signature harvesting (definition-looking lines).
- Docs and configs: full content (they are usually small and every line
  matters), truncated only by the token budget downstream.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

# Lines that usually define the "shape" of a file, per language family.
HEURISTIC_PATTERNS: dict[str, list[str]] = {
    "javascript": [
        r"^\s*(export\s+)?(async\s+)?function\s+[\w$]+\s*\(",
        r"^\s*(export\s+)?(const|let|var)\s+[\w$]+\s*=\s*(\(|async|function|\()",
        r"^\s*(export\s+)?(default\s+)?class\s+\w+",
        r"^\s*(export\s+)?(interface|type|enum)\s+\w+",
        r"^\s*import\s+.+",
    ],
    "typescript": [
        r"^\s*(export\s+)?(async\s+)?function\s+[\w$]+\s*\(",
        r"^\s*(export\s+)?(const|let|var)\s+[\w$]+\s*[:=]",
        r"^\s*(export\s+)?(default\s+)?(abstract\s+)?class\s+\w+",
        r"^\s*(export\s+)?(interface|type|enum|namespace)\s+\w+",
        r"^\s*import\s+.+",
    ],
    "go": [
        r"^\s*func\s+(\(\w+[\w\s\*]+\))?\s*\w+\s*\(",
        r"^\s*type\s+\w+\s+(struct|interface|\w+)",
        r"^\s*package\s+\w+",
        r"^\s*import\s*[\(\"]",
    ],
    "rust": [
        r"^\s*(pub(\(.*\))?\s+)?(async\s+)?fn\s+\w+",
        r"^\s*(pub(\(.*\))?\s+)?(struct|enum|trait|impl|mod)\s+\w+",
        r"^\s*use\s+.+;",
    ],
    "java": [
        r"^\s*(public|private|protected)?\s*(static\s+)?(class|interface|enum|record)\s+\w+",
        r"^\s*(public|private|protected)?\s*(static\s+)?[\w<>\[\]]+\s+\w+\s*\(",
        r"^\s*import\s+.+;",
        r"^\s*package\s+.+;",
    ],
    "kotlin": [
        r"^\s*(public|private|protected|internal)?\s*(data\s+|sealed\s+|abstract\s+)?class\s+\w+",
        r"^\s*(public|private|protected|internal)?\s*fun\s+[\w<>\.]+\s*\w*\s*\(",
        r"^\s*import\s+.+",
        r"^\s*package\s+.+",
    ],
    "c": [
        r"^\s*#include\s+[<\"]",
        r"^\s*(static\s+)?[\w\*\s]+\s+\w+\s*\([^;]*\)\s*(\{|$)",
        r"^\s*(typedef\s+)?(struct|enum|union)\s+\w*",
    ],
    "cpp": [
        r"^\s*#include\s+[<\"]",
        r"^\s*(class|struct)\s+\w+",
        r"^\s*[\w:<>~\*\s]+\s+\w+\s*\([^;]*\)\s*(const)?\s*(\{|$)",
        r"^\s*namespace\s+\w+",
    ],
    "ruby": [
        r"^\s*(class|module)\s+\w+",
        r"^\s*def\s+\w+",
        r"^\s*require\s+['\"]",
    ],
    "php": [
        r"^\s*(class|interface|trait)\s+\w+",
        r"^\s*(public|private|protected)?\s*function\s+\w+\s*\(",
        r"^\s*namespace\s+.+;",
        r"^\s*use\s+.+;",
    ],
    "swift": [
        r"^\s*(public|private|internal|fileprivate)?\s*(class|struct|enum|protocol|extension)\s+\w+",
        r"^\s*(public|private|internal|fileprivate)?\s*func\s+\w+",
        r"^\s*import\s+\w+",
    ],
    "shell": [
        r"^\s*\w+\s*\(\)\s*\{",
        r"^\s*function\s+\w+",
    ],
    "sql": [
        r"^\s*CREATE\s+(TABLE|VIEW|INDEX|PROCEDURE|FUNCTION)",
        r"^\s*ALTER\s+TABLE",
    ],
    "html": [
        r"^\s*<(html|head|body|title|script|link|meta)",
    ],
    "css": [
        r"^[.#\w][^{]*\{",
    ],
    "vue": [
        r"^\s*(export\s+)?(default\s+)?(function|class|const|interface)\s*\w*",
        r"^\s*import\s+.+",
    ],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    lang: [re.compile(p) for p in pats]
    for lang, pats in HEURISTIC_PATTERNS.items()
}


def _first_doc_line(doc: str | None) -> str:
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    return line[:160]


def _format_args(node: ast.arguments) -> str:
    try:
        return ast.unparse(node)  # Python 3.9+
    except Exception:
        names = [a.arg for a in node.args]
        return ", ".join(names)


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef,
                      indent: str) -> list[str]:
    kw = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = ""
    if node.returns is not None:
        try:
            ret = f" -> {ast.unparse(node.returns)}"
        except Exception:
            ret = ""
    lines = [f"{indent}{kw} {node.name}({_format_args(node.args)}){ret}:"]
    doc = _first_doc_line(ast.get_docstring(node))
    if doc:
        lines.append(f'{indent}    """{doc}"""')
    return lines


def extract_python(source: str) -> str:
    """AST-based structural summary of a Python module."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"# [unparseable: {e}]\n" + _head_fallback(source, 15)

    out: list[str] = []
    module_doc = _first_doc_line(ast.get_docstring(tree))
    if module_doc:
        out.append(f'"""{module_doc}"""\n')

    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.append("import " + ", ".join(
                a.asname and f"{a.name} as {a.asname}" or a.name
                for a in node.names))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = ", ".join(
                a.asname and f"{a.name} as {a.asname}" or a.name
                for a in node.names)
            imports.append(f"from {mod} import {names}")
    if imports:
        out.extend(imports)
        out.append("")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.extend(_format_signature(node, ""))
            out.append("")
        elif isinstance(node, ast.ClassDef):
            bases = ""
            if node.bases:
                try:
                    bases = "(" + ", ".join(ast.unparse(b) for b in node.bases) + ")"
                except Exception:
                    bases = "(...)"
            out.append(f"class {node.name}{bases}:")
            doc = _first_doc_line(ast.get_docstring(node))
            if doc:
                out.append(f'    """{doc}"""')
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.extend(_format_signature(sub, "    "))
            out.append("")
        elif isinstance(node, ast.Assign):
            try:
                targets = ", ".join(ast.unparse(t) for t in node.targets)
                out.append(f"{targets} = ...")
            except Exception:
                pass
    return "\n".join(out).rstrip() + "\n"


def _head_fallback(source: str, lines: int) -> str:
    kept = [ln for ln in source.splitlines() if ln.strip()][:lines]
    return "\n".join(kept) + ("\n" if kept else "")


def extract_heuristic(source: str, language: str,
                      head_lines: int = 8) -> str:
    """Best-effort structural summary for non-Python code."""
    patterns = _COMPILED.get(language, [])
    sig_lines: list[str] = []
    seen: set[str] = set()
    for line in source.splitlines():
        stripped = line.rstrip()
        if not stripped.strip():
            continue
        if any(p.search(stripped) for p in patterns):
            key = stripped.strip()
            if key not in seen:
                seen.add(key)
                sig_lines.append(stripped)
    head = [ln for ln in source.splitlines() if ln.strip()][:head_lines]
    parts: list[str] = []
    if head:
        parts.append("# --- file head ---")
        parts.extend(head)
    if sig_lines:
        parts.append("# --- detected definitions ---")
        parts.extend(sig_lines)
    return "\n".join(parts) + ("\n" if parts else "")


def extract_file(path: Path, language: str | None, kind: str,
                 mode: str = "signatures", head_lines: int = 10) -> str:
    """Extract LLM-ready content from one file.

    mode="signatures": structural summary for code, full text for docs/config.
    mode="full":       first ``head_lines`` non-empty lines of everything
                       (the legacy Luna 1.x behavior, minus the noise).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"# [unreadable: {e}]\n"
    if mode == "full" or kind in ("doc", "config"):
        return _head_fallback(text, head_lines if mode == "full" else 400)
    if language == "python":
        return extract_python(text)
    if language:
        return extract_heuristic(text, language, head_lines=6)
    return _head_fallback(text, head_lines)
