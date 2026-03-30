import os
from pathlib import Path
import time

class LunaSummarizer:
    """
    Luna: A lightweight tool to prepare local codebase context for LLMs.
    Designed for AI-driven development workflows.
    """
    def __init__(self, root_dir=".", ignore_list=None):
        self.root_dir = Path(root_dir)
        self.ignore_list = ignore_list or {
            '.git', '__pycache__', '.vscode', '.idea', 
            'node_modules', 'venv', '.env', 'LICENSE'
        }
        self.supported_extensions = {'.py', '.md', '.txt', '.json', '.yaml', '.yml'}

    def should_ignore(self, path):
        """Check if the file or directory should be ignored."""
        return any(part in self.ignore_list or part.startswith('.') for part in path.parts)

    def scan_project(self):
        """Scans the project directory and extracts core metadata."""
        print(f"🚀 Luna is analyzing project structure at: {self.root_dir.absolute()}")
        summary = []
        file_count = 0

        for path in self.root_dir.rglob('*'):
            if path.is_file() and path.suffix in self.supported_extensions:
                if not self.should_ignore(path):
                    file_count += 1
                    relative_path = path.relative_to(self.root_dir)
                    summary.append(f"--- File: {relative_path} ---")
                    
                    # Read first 10 lines as context snippet
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            lines = [f.readline().strip() for _ in range(10)]
                            summary.append("\n".join([l for l in lines if l]))
                    except Exception as e:
                        summary.append(f"[Error reading file: {e}]")
                    
                    summary.append("\n")

        return "\n".join(summary), file_count

    def export_summary(self, output_file="luna_context.txt"):
        """Exports the context summary to a text file for LLM input."""
        content, count = self.scan_project()
        header = f"Luna AI Context Summary - Generated on {time.ctime()}\n"
        header += f"Total files analyzed: {count}\n"
        header += "="*40 + "\n\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header + content)
        
        print(f"✅ Success! Context summary exported to: {output_file}")

if __name__ == "__main__":
    # Initialize Luna and run a local scan
    luna = LunaSummarizer()
    luna.export_summary()
