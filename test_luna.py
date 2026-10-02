"""Dependency-free tests for Luna. Run with: python test_luna.py"""
import shutil
import tempfile
from pathlib import Path

from main import LunaSummarizer


def make_project(files):
    """Create a temp project. files: {relative_path: content}; content=None -> dir."""
    root = Path(tempfile.mkdtemp())
    for rel, content in files.items():
        p = root / rel
        if content is None:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return root


def test_scan_includes_supported_files():
    root = make_project({"a.py": "print('hi')\n", "b.md": "# title\n"})
    try:
        content, count = LunaSummarizer(root_dir=root).scan_project()
        assert count == 2, f"expected 2 files, got {count}"
        assert "a.py" in content and "b.md" in content
    finally:
        shutil.rmtree(root)


def test_ignores_vcs_and_venv():
    root = make_project({"a.py": "x = 1\n", ".git": None, "venv": None})
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    (root / "venv" / "lib.py").write_text("y = 2\n", encoding="utf-8")
    try:
        content, count = LunaSummarizer(root_dir=root).scan_project()
        assert count == 1, f"expected 1 file, got {count}"
        assert "HEAD" not in content and "lib.py" not in content
    finally:
        shutil.rmtree(root)


def test_dotfile_with_supported_extension_is_included():
    # Regression test: old should_ignore() skipped every dotfile via
    # part.startswith('.'), hiding legit config files like .config.json.
    root = make_project({".config.json": '{"a": 1}\n'})
    try:
        content, count = LunaSummarizer(root_dir=root).scan_project()
        assert count == 1, f"expected 1 file, got {count}"
        assert ".config.json" in content
    finally:
        shutil.rmtree(root)


def test_export_summary_writes_file():
    root = make_project({"a.py": "x = 1\n"})
    out = root / "out.txt"
    try:
        LunaSummarizer(root_dir=root).export_summary(output_file=str(out))
        text = out.read_text(encoding="utf-8")
        assert "Total files analyzed: 1" in text
        assert "a.py" in text
    finally:
        shutil.rmtree(root)


def test_custom_snippet_lines():
    body = "\n".join(f"line{i}" for i in range(20)) + "\n"
    root = make_project({"a.py": body})
    try:
        content, _ = LunaSummarizer(root_dir=root, snippet_lines=3).scan_project()
        assert "line0" in content and "line2" in content
        assert "line3" not in content
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} tests passed.")
