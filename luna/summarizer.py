"""Luna 2.0 orchestrator: scan -> extract -> budget -> render."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import git as gitmod
from .extract import extract_file
from .formats import RENDERERS, render_tree
from .scanner import FileEntry, Scanner
from .tokens import estimate_tokens, fit_budget


@dataclass
class LunaStats:
    files: int = 0
    tokens: int = 0
    budget: int | None = None
    skipped: int = 0
    mode: str = "signatures"
    git_mode: str | None = None


@dataclass
class Luna:
    """Builds LLM-ready context for a codebase."""
    root: str | Path = "."
    output_format: str = "txt"          # txt | xml | json
    mode: str = "signatures"            # signatures | full
    budget: int | None = None           # max estimated tokens
    head_lines: int = 10
    extra_exts: set[str] = field(default_factory=set)
    extra_ignore: set[str] = field(default_factory=set)
    max_size: int = 256 * 1024
    follow_gitignore: bool = True
    include_tree: bool = True
    git_mode: str | None = None         # None | "changed" | "staged"
    git_ref: str | None = None

    def __post_init__(self):
        self.root = Path(self.root).resolve()
        if self.output_format not in RENDERERS:
            raise ValueError(f"unknown format: {self.output_format}")

    # -- pipeline ------------------------------------------------------
    def _collect_entries(self) -> list[FileEntry]:
        scanner = Scanner(
            root=self.root,
            extra_ignore=self.extra_ignore,
            extra_exts=self.extra_exts,
            max_size=self.max_size,
            follow_gitignore=self.follow_gitignore,
        )
        entries = scanner.scan()
        if self.git_mode or self.git_ref:
            staged = self.git_mode == "staged"
            changes = gitmod.changed_files(
                self.root, staged=staged, ref=self.git_ref)
            wanted = set(changes.files)
            entries = [e for e in entries if e.rel in wanted]
            self._diffs = changes.diffs
        else:
            self._diffs = {}
        # Prioritise docs, then smaller files first — deterministic and
        # budget-friendly.
        entries.sort(key=lambda e: (0 if e.kind == "doc" else 1, e.size))
        return entries

    def _extract(self, entry: FileEntry) -> str:
        if self._diffs.get(entry.rel):
            return ("# --- git diff ---\n" + self._diffs[entry.rel]).rstrip()
        if entry.size > self.max_size:
            return (f"# [file too large: {entry.size} bytes, "
                    f"limit {self.max_size} — listed in tree only]\n")
        return extract_file(entry.path, entry.language, entry.kind,
                            mode=self.mode, head_lines=self.head_lines)

    def build(self) -> tuple[str, LunaStats]:
        """Returns (rendered_output, stats)."""
        entries = self._collect_entries()
        items = [(e.rel, self._extract(e)) for e in entries]
        result = fit_budget(items, self.budget)
        sections = result.kept  # (rel, content, tokens)
        skipped = result.skipped

        stats = LunaStats(
            files=len(sections), tokens=result.used, budget=self.budget,
            skipped=len(skipped), mode=self.mode,
            git_mode=self.git_mode or (f"ref:{self.git_ref}" if self.git_ref else None),
        )
        stats_dict = {
            "files": stats.files, "tokens": stats.tokens,
            "budget": stats.budget, "mode": stats.mode,
            "git_mode": stats.git_mode,
        }
        tree = render_tree([e.rel for e in entries]) if self.include_tree else ""
        skipped_pairs = [(rel, tok) for rel, tok in skipped]

        renderer = RENDERERS[self.output_format]
        if self.output_format == "txt":
            output = renderer(tree, sections, stats_dict, skipped_pairs)
        else:
            output = renderer(sections, stats_dict, skipped_pairs)
        return output, stats

    def export(self, output_path: str | Path) -> LunaStats:
        output, stats = self.build()
        output_path = Path(output_path)
        output_path.write_text(output, encoding="utf-8")
        return stats
