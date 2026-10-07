"""Luna 2.0 demo: builds a fake project and shows what Luna extracts.

Run:  python demo.py
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from luna import Luna  # noqa: E402

TEST_DIR = Path("demo_project")


def cleanup(path: Path) -> None:
    if path.exists():
        def onerror(func, p, exc_info):
            if func in (os.rmdir, os.remove):
                os.chmod(p, stat.S_IWRITE)
                func(p)
            else:
                raise
        shutil.rmtree(path, onerror=onerror)


def build_fake_project() -> None:
    cleanup(TEST_DIR)
    (TEST_DIR / "src").mkdir(parents=True)
    (TEST_DIR / "src" / "api.py").write_text(
        '"""API client."""\nimport requests\n\n'
        'API_URL = "https://example.com"\n\n'
        'def fetch_data(endpoint):\n    """Fetch JSON from an endpoint."""\n'
        '    return requests.get(API_URL + endpoint).json()\n\n'
        'class Client:\n    """Thin API wrapper."""\n'
        '    def __init__(self, key):\n        """Store the API key."""\n'
        '        self.key = key\n\n'
        '    def save_data(self, payload):\n        """POST payload."""\n'
        '        return requests.post(API_URL, json=payload)\n',
        encoding="utf-8")
    (TEST_DIR / "src" / "app.js").write_text(
        "import { fetchData } from './api.js';\n\n"
        "export async function run(endpoint) {\n"
        "  const data = await fetchData(endpoint);\n"
        "  console.log(data);\n"
        "}\n"
        "export class Runner {\n"
        "  start() { run('/v1'); }\n"
        "}\n",
        encoding="utf-8")
    (TEST_DIR / "docs").mkdir()
    (TEST_DIR / "docs" / "README.md").write_text(
        "# Demo\n\nThis is a demo project for Luna.\n", encoding="utf-8")
    (TEST_DIR / "config.yaml").write_text(
        "settings:\n  debug: false\n", encoding="utf-8")
    # Noise that Luna must ignore:
    (TEST_DIR / ".git").mkdir()
    (TEST_DIR / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    (TEST_DIR / "node_modules").mkdir()
    (TEST_DIR / "node_modules" / "huge.js").write_text("x" * 10000, encoding="utf-8")
    (TEST_DIR / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
    (TEST_DIR / "debug.log").write_text("noise", encoding="utf-8")


def main() -> None:
    print("--- 1. building fake project ---")
    build_fake_project()

    print("--- 2. signatures mode (default) ---")
    luna = Luna(root=TEST_DIR, output_format="txt")
    stats = luna.export(TEST_DIR / "ctx_signatures.txt")
    print(f"    {stats.files} files, ~{stats.tokens} tokens")

    print("--- 3. xml format + tight budget ---")
    luna = Luna(root=TEST_DIR, output_format="xml", budget=500)
    stats = luna.export(TEST_DIR / "ctx_small.xml")
    print(f"    {stats.files} files, ~{stats.tokens} tokens, "
          f"{stats.skipped} skipped over budget")

    print("--- 4. preview (signatures output) ---")
    text = (TEST_DIR / "ctx_signatures.txt").read_text(encoding="utf-8")
    print(text[:1500])
    print("    ...")

    print("--- 5. cleanup ---")
    cleanup(TEST_DIR)
    print("✅ demo done")


if __name__ == "__main__":
    main()
