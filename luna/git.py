"""Git awareness: focus context on what actually changed.

``--changed``  -> files differing from HEAD (worktree + index).
``--staged``   -> only staged changes (``git diff --cached``).
``--ref A``    -> files differing from another ref (e.g. ``main``).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitError(f"git failed: {e}") from e
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def is_git_repo(root: Path) -> bool:
    try:
        _run(root, "rev-parse", "--git-dir")
        return True
    except GitError:
        return False


@dataclass
class ChangeSet:
    files: list[str]          # changed paths, repo-relative posix
    diffs: dict[str, str]     # path -> unified diff text


def changed_files(root: Path, staged: bool = False,
                  ref: str | None = None) -> ChangeSet:
    """Collect changed files and their diffs."""
    if ref:
        base = ["diff", "--name-only", ref]
        diff_base = ["diff", ref, "--"]
    elif staged:
        base = ["diff", "--cached", "--name-only"]
        diff_base = ["diff", "--cached", "--"]
    else:
        base = ["diff", "--name-only", "HEAD"]
        diff_base = ["diff", "HEAD", "--"]

    names = [ln for ln in _run(root, *base).splitlines() if ln.strip()]
    diffs: dict[str, str] = {}
    for name in names:
        try:
            diffs[name] = _run(root, *diff_base, name)
        except GitError:
            diffs[name] = ""
    return ChangeSet(files=names, diffs=diffs)
