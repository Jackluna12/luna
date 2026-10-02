import argparse
import time
from pathlib import Path


class LunaSummarizer:
    """
    Luna: A lightweight tool to prepare local codebase context for LLMs.
    Designed for AI-driven development workflows.
    """

    DEFAULT_IGNORE = {
        ".git", "__pycache__", ".vscode", ".idea",
        "node_modules", "venv", ".venv", "dist", "build",
        ".env", "LICENSE",
    }

    DEFAULT_EXTENSIONS = {
        # docs & data
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
        ".ini", ".cfg", ".xml",
        # python
        ".py",
        # js/ts
        ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
        # other languages
        ".go", ".java", ".rb", ".php", ".c", ".h",
        ".cpp", ".hpp", ".rs", ".sh", ".bash", ".sql",
        ".html", ".css",
    }

    def __init__(self, root_dir=".", ignore_list=None, extensions=None,
                 snippet_lines=10):
        self.root_dir = Path(root_dir)
        self.ignore_list = set(ignore_list) if ignore_list is not None \
            else set(self.DEFAULT_IGNORE)
        self.supported_extensions = set(extensions) if extensions is not None \
            else set(self.DEFAULT_EXTENSIONS)
        self.snippet_lines = snippet_lines

    def should_ignore(self, path):
        """Check if the file or directory should be ignored.

        Matches path parts by exact name only, so dotfiles with a
        supported extension (e.g. ``.config.json``) are still scanned.
        """
        return any(part in self.ignore_list for part in path.parts)

    def scan_project(self):
        """Scans the project directory and extracts core metadata."""
        print(f"\U0001f680 Luna is analyzing project structure at: "
              f"{self.root_dir.absolute()}")
        summary = []
        file_count = 0

        for path in self.root_dir.rglob("*"):
            if path.is_file() and path.suffix in self.supported_extensions:
                if not self.should_ignore(path):
                    file_count += 1
                    relative_path = path.relative_to(self.root_dir)
                    summary.append(f"--- File: {relative_path} ---")

                    # Read the first N lines as a context snippet
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as f:
                            lines = [f.readline().strip()
                                     for _ in range(self.snippet_lines)]
                            summary.append("\n".join(l for l in lines if l))
                    except Exception as e:
                        summary.append(f"[Error reading file: {e}]")

                    summary.append("\n")

        return "\n".join(summary), file_count

    def export_summary(self, output_file="luna_context.txt"):
        """Exports the context summary to a text file for LLM input."""
        content, count = self.scan_project()
        header = f"Luna AI Context Summary - Generated on {time.ctime()}\n"
        header += f"Total files analyzed: {count}\n"
        header += "=" * 40 + "\n\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header + content)

        print(f"\u2705 Success! Context summary exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Luna: summarize a codebase into an LLM-ready context file."
    )
    parser.add_argument("root", nargs="?", default=".",
                        help="Project root directory to scan (default: .)")
    parser.add_argument("-o", "--output", default="luna_context.txt",
                        help="Output file path (default: luna_context.txt)")
    parser.add_argument("--lines", type=int, default=10,
                        help="Snippet lines captured per file (default: 10)")
    parser.add_argument("--ext", action="append", default=None,
                        help="Extra file extension to include, e.g. --ext .vue "
                             "(repeatable)")
    parser.add_argument("--ignore", action="append", default=None,
                        help="Extra directory/file name to ignore (repeatable)")
    args = parser.parse_args()

    extensions = set(LunaSummarizer.DEFAULT_EXTENSIONS)
    if args.ext:
        extensions.update(e if e.startswith(".") else "." + e for e in args.ext)
    ignore = set(LunaSummarizer.DEFAULT_IGNORE)
    if args.ignore:
        ignore.update(args.ignore)

    luna = LunaSummarizer(root_dir=args.root, ignore_list=ignore,
                          extensions=extensions, snippet_lines=args.lines)
    luna.export_summary(output_file=args.output)


if __name__ == "__main__":
    main()
