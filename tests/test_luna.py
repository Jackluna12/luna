"""Luna 2.0 test suite — zero dependencies, run with:  python -m unittest discover -s tests"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from luna import Luna
from luna.extract import extract_file, extract_heuristic, extract_python
from luna.formats import render_json, render_tree, render_xml
from luna.git import changed_files, is_git_repo
from luna.scanner import GitignoreMatcher, Scanner
from luna.tokens import estimate_tokens, fit_budget


class TestTokens(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_ascii_heuristic(self):
        # ~4 chars per token
        self.assertEqual(estimate_tokens("a" * 400), 100)

    def test_cjk_costs_more(self):
        latin = estimate_tokens("a" * 150)
        cjk = estimate_tokens("中" * 150)
        self.assertGreater(cjk, latin)

    def test_fit_budget_keeps_order(self):
        items = [("a", "x" * 400), ("b", "y" * 400), ("c", "z" * 400)]
        r = fit_budget(items, budget=250)
        self.assertEqual([k for k, _, _ in r.kept], ["a", "b"])
        self.assertEqual([k for k, _ in r.skipped], ["c"])
        self.assertEqual(r.used, 200)

    def test_fit_budget_none_keeps_all(self):
        items = [("a", "x" * 4000)]
        r = fit_budget(items, None)
        self.assertEqual(len(r.kept), 1)
        self.assertEqual(r.skipped, [])


class TestExtractPython(unittest.TestCase):
    SRC = '''"""Module doc."""

import os
from sys import path as sp

CONSTANT = 42

def greet(name, greeting="hi"):
    """Say hi."""
    return f"{greeting} {name}"

class Worker:
    """Does work."""

    def run(self, fast=True):
        """Run it."""
        pass
'''

    def test_signatures_present_bodies_dropped(self):
        out = extract_python(self.SRC)
        self.assertIn("def greet(name, greeting='hi'):", out)
        self.assertIn("class Worker:", out)
        self.assertIn("def run(self, fast=True):", out)
        self.assertIn("Say hi.", out)
        self.assertNotIn("return f", out)  # body dropped

    def test_imports_condensed(self):
        out = extract_python(self.SRC)
        self.assertIn("import os", out)
        self.assertIn("from sys import path as sp", out)

    def test_syntax_error_falls_back(self):
        out = extract_python("def broken(:\n")
        self.assertIn("unparseable", out)


class TestExtractHeuristic(unittest.TestCase):
    def test_js_signatures(self):
        src = ("import x from 'y';\n\nexport async function run(a) {\n"
               "  return 1;\n}\nexport class Runner {}\n")
        out = extract_heuristic(src, "javascript")
        defs = out.split("# --- detected definitions ---")[1]
        self.assertIn("export async function run(a)", defs)
        self.assertIn("export class Runner", defs)
        self.assertNotIn("return 1;", defs)  # bodies stay out of definitions

    def test_go_signatures(self):
        src = "package main\n\nfunc DoWork(n int) int {\n\treturn n\n}\n"
        out = extract_heuristic(src, "go")
        self.assertIn("func DoWork(n int) int", out)


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "a.py").write_text("x = 1\n")
        (self.tmp / "src" / "b.pyc").write_bytes(b"\x00\x01")
        (self.tmp / ".git").mkdir()
        (self.tmp / "node_modules").mkdir()
        (self.tmp / "node_modules" / "x.js").write_text("1\n")
        (self.tmp / ".gitignore").write_text("node_modules/\nsecret.txt\n")
        (self.tmp / "secret.txt").write_text("nope\n")
        (self.tmp / "keep.txt").write_text("yes\n")
        (self.tmp / "README.md").write_text("# hi\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_defaults_pruned(self):
        entries = Scanner(root=self.tmp).scan()
        rels = {e.rel for e in entries}
        self.assertIn("src/a.py", rels)
        self.assertIn("README.md", rels)
        self.assertIn("keep.txt", rels)  # .txt is a doc ext
        self.assertNotIn("node_modules/x.js", rels)  # gitignore dir rule
        self.assertNotIn("secret.txt", rels)          # gitignore file rule
        self.assertNotIn("src/b.pyc", rels)          # binary + ignored ext

    def test_gitignore_matcher_negation(self):
        (self.tmp / ".gitignore").write_text("*.log\n!important.log\n")
        m = GitignoreMatcher(self.tmp)
        self.assertTrue(m.is_ignored("a.log", False))
        self.assertFalse(m.is_ignored("important.log", False))

    def test_kinds(self):
        entries = Scanner(root=self.tmp).scan()
        by_rel = {e.rel: e for e in entries}
        self.assertEqual(by_rel["src/a.py"].kind, "code")
        self.assertEqual(by_rel["src/a.py"].language, "python")
        self.assertEqual(by_rel["README.md"].kind, "doc")


class TestFormats(unittest.TestCase):
    def test_tree(self):
        tree = render_tree(["b.py", "src/a.py"])
        self.assertIn("src", tree)
        self.assertIn("a.py", tree)
        self.assertIn("b.py", tree)

    def test_xml_escapes(self):
        out = render_xml([("a.py", "x < y & z", 3)], {}, [])
        self.assertIn("<source>a.py</source>", out)
        self.assertIn("x &lt; y &amp; z", out)

    def test_json_shape(self):
        import json
        out = render_json([("a.py", "hi", 1)], {"files": 1}, [])
        data = json.loads(out)
        self.assertEqual(data["files"][0]["path"], "a.py")


class TestGit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp, check=True)
        (self.tmp / "a.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.tmp, check=True)
        (self.tmp / "a.py").write_text("x = 2\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_is_git_repo(self):
        self.assertTrue(is_git_repo(self.tmp))
        self.assertFalse(is_git_repo(Path(tempfile.mkdtemp())))

    def test_changed_files(self):
        cs = changed_files(self.tmp)
        self.assertIn("a.py", cs.files)
        self.assertIn("x = 2", cs.diffs["a.py"])


class TestLunaEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "main.py").write_text(
            '"""Doc."""\ndef f(a):\n    """F."""\n    return a\n')
        (self.tmp / "README.md").write_text("# t\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_txt(self):
        luna = Luna(root=self.tmp, output_format="txt")
        out, stats = luna.build()
        self.assertIn("def f(a):", out)
        self.assertIn("Project tree", out)
        self.assertGreater(stats.files, 0)

    def test_budget_skips(self):
        luna = Luna(root=self.tmp, output_format="txt", budget=5)
        out, stats = luna.build()
        self.assertGreater(stats.skipped, 0)
        self.assertIn("Skipped", out)

    def test_export_writes_file(self):
        target = self.tmp / "out.txt"
        stats = Luna(root=self.tmp).export(target)
        self.assertTrue(target.exists())
        self.assertGreater(stats.tokens, 0)


if __name__ == "__main__":
    unittest.main()
