"""File discovery with .gitignore awareness.

Walks a project tree, applies .gitignore-style rules (a practical subset:
``*`` / ``?`` / ``[...]`` / ``**``, trailing-``/`` directory rules, and ``!``
negations), skips binaries and oversized files, and returns an ordered list
of candidate files with metadata.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Always-on ignores: VCS, dependency and build output, secrets.
DEFAULT_IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", ".tox",
    "dist", "build", "out", "target",
    ".idea", ".vscode",
}
DEFAULT_IGNORE_FILES = {
    ".env", ".env.local", ".env.production",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
}
# Extensions that are never useful as LLM context.
DEFAULT_IGNORE_EXTS = {
    ".pyc", ".pyo", ".so", ".o", ".a", ".dll", ".dylib",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".mp3", ".mp4", ".mov", ".avi", ".pdf",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".sqlite", ".db", ".bin", ".dat", ".exe",
}

# Extension -> language family, used to pick the extractor.
EXTENSION_LANGUAGE = {
    ".py": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".sql": "sql", ".html": "html", ".css": "css", ".vue": "vue",
}
DOC_EXTENSIONS = {".md", ".txt", ".rst"}
CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml",
    ".env", ".example",
}


@dataclass
class FileEntry:
    """A single file selected for context extraction."""
    path: Path            # absolute path on disk
    rel: str              # posix-style path relative to the project root
    size: int             # bytes on disk
    language: str | None  # language family, or None for docs/config/unknown
    kind: str             # "code" | "doc" | "config" | "other"


@dataclass
class _Rule:
    regex: re.Pattern
    dir_only: bool
    anchored: bool
    negated: bool


def _translate_glob(pattern: str) -> str:
    """Translate a gitignore-style glob into a regex body."""
    i, n = 0, len(pattern)
    out: list[str] = []
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 2] == "**":
                if pattern[i + 2:i + 3] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            j = pattern.find("]", i + 1)
            if j == -1:
                out.append("\\[")
                i += 1
            else:
                out.append(pattern[i:j + 1])
                i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return "".join(out)


class GitignoreMatcher:
    """Applies .gitignore-style rules found under a project root."""

    def __init__(self, root: Path):
        self.root = root
        self.rules: list[_Rule] = []
        for gi in sorted(root.rglob(".gitignore")):
            # Rules are relative to the directory containing the .gitignore.
            prefix = gi.parent.relative_to(root).as_posix()
            prefix = "" if prefix == "." else prefix + "/"
            self._load(gi, prefix)

    def _load(self, path: Path, prefix: str) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negated = line.startswith("!")
            if negated:
                line = line[1:]
            dir_only = line.endswith("/")
            line = line.rstrip("/")
            if line.startswith("/"):
                line = line[1:]
                anchored = True
            else:
                anchored = "/" in line
            body = _translate_glob(prefix + line)
            if anchored:
                regex = re.compile(body + r"(?:/.*)?$")
            else:
                # Unanchored patterns match any path component.
                regex = re.compile(r"(?:.*/)?" + body + r"(?:/.*)?$")
            self.rules.append(_Rule(regex, dir_only, anchored, negated))

    def is_ignored(self, rel_posix: str, is_dir: bool) -> bool:
        ignored = False
        for rule in self.rules:
            if rule.dir_only and not is_dir:
                continue
            if rule.regex.match(rel_posix):
                ignored = not rule.negated
        return ignored


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def _classify(path: Path) -> tuple[str, str | None]:
    ext = path.suffix.lower()
    if ext in DOC_EXTENSIONS:
        return "doc", None
    if ext in CONFIG_EXTENSIONS:
        return "config", None
    if ext in EXTENSION_LANGUAGE:
        return "code", EXTENSION_LANGUAGE[ext]
    if not ext and path.name.lower() in {
        "dockerfile", "makefile", "rakefile", "gemfile",
    }:
        return "config", None
    return "other", None


@dataclass
class Scanner:
    """Discovers files worth turning into LLM context."""
    root: Path
    extra_ignore: set[str] = field(default_factory=set)
    extra_exts: set[str] = field(default_factory=set)
    max_size: int = 256 * 1024  # files larger than this are listed, not read
    follow_gitignore: bool = True

    def scan(self) -> list[FileEntry]:
        matcher = GitignoreMatcher(self.root) if self.follow_gitignore else None
        entries: list[FileEntry] = []
        ignore_names = set(self.extra_ignore)

        for dirpath, dirnames, filenames in os.walk(self.root):
            dir_path = Path(dirpath)
            rel_dir = dir_path.relative_to(self.root).as_posix()
            rel_dir = "" if rel_dir == "." else rel_dir

            # Prune ignored directories first (matches git semantics:
            # you cannot re-include files under an excluded directory).
            kept: list[str] = []
            for d in sorted(dirnames):
                if d in DEFAULT_IGNORE_DIRS or d in ignore_names:
                    continue
                rel = f"{rel_dir}/{d}" if rel_dir else d
                if matcher and matcher.is_ignored(rel, is_dir=True):
                    continue
                kept.append(d)
            dirnames[:] = kept

            for name in sorted(filenames):
                if name in DEFAULT_IGNORE_FILES or name in ignore_names:
                    continue
                p = dir_path / name
                rel = f"{rel_dir}/{name}" if rel_dir else name
                if matcher and matcher.is_ignored(rel, is_dir=False):
                    continue
                ext = p.suffix.lower()
                if ext in DEFAULT_IGNORE_EXTS and ext not in self.extra_exts:
                    continue
                try:
                    size = p.stat().st_size
                except OSError:
                    continue
                if size == 0 or _is_binary(p):
                    continue
                kind, language = _classify(p)
                if kind == "other" and ext and ext not in self.extra_exts:
                    continue
                entries.append(FileEntry(
                    path=p, rel=rel, size=size,
                    language=language, kind=kind,
                ))
        return entries
