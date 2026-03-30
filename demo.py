import os
import shutil
import stat
from pathlib import Path
from main import LunaSummarizer

# ==========================================================
# 🚀 Luna: Demonstration Script
# This script creates a temporary project structure to show 
# how Luna extracts AI-ready context from a codebase.
# ==========================================================

# 1. Setup a temporary test environment
# This simulates a real project with diverse file types.
test_project_name = "demo_project"
test_dir = Path(test_project_name)

# Define a function for simple cross-platform cleanup
def cleanup_test_dir(path):
    if path.exists():
        # Handle read-only files on some systems
        def onerror(func, p, exc_info):
            if func in (os.rmdir, os.remove):
                os.chmod(p, stat.S_IWRITE)
                func(p)
            else:
                raise
        shutil.rmtree(path, onerror=onerror)

cleanup_test_dir(test_dir) # Ensure clean start
test_dir.mkdir()

# Create dummy subdirectories and files
print("--- 1. Set up temporary demo project at '{test_project_name}' ---")
(test_dir / "src").mkdir()
(test_dir / "src" / "api.py").write_text("def fetch_data(): pass\ndef save_data(): pass", encoding='utf-8')
(test_dir / "src" / "utils.py").write_text("import time\ndef get_timestamp(): return time.time()", encoding='utf-8')

(test_dir / "docs").mkdir()
(test_dir / "docs" / "README.md").write_text("# API Documentation\nThis is a readme for the API.\nHow to install: npm install api-lib", encoding='utf-8')

(test_dir / "config.yaml").write_text("settings:\n  api_key: 'secret_key_123'\n  debug: false", encoding='utf-8')

# Create files that should be ignored
(test_dir / ".git").mkdir() # A directory to be ignored
(test_dir / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding='utf-8')
(test_dir / ".env").write_text("DATABASE_URL=postgres://user:pass@localhost/db", encoding='utf-8') # A file to be ignored

print(f"   Structure:\n   {test_project_name}/src/api.py\n   {test_project_name}/src/utils.py\n   {test_project_name}/docs/README.md\n   {test_project_name}/config.yaml\n   (Ignored: .git, .env)")
print("-" * 40)


# 2. Instantiate Luna to scan the test project
# This uses default settings from main.py, which include standard ignore rules.
print("--- 2. Instantiating Luna with default settings ---")
print(f"Scan Directory: {test_dir.absolute()}")
# Points Luna at our temp project, so it doesn't scan the 'luna' repo itself.
luna = LunaSummarizer(root_dir=test_project_name)

# 3. Generate the context summary
# This is the core workflow: scanning, filtering, and summarizing.
print("--- 3. Running export_summary() ---")
# Specify the output file path in the test directory
output_filepath = test_dir / "luna_context.txt"
luna.export_summary(output_file=str(output_filepath))

# 4. Verify and preview results
# Show the AI-ready context that Luna just generated.
print("--- 4. Verifying and Previewing generated context file ---")
if output_filepath.exists():
    print(f"✅ Success: '{output_filepath.name}' generated in '{test_project_name}'.")
    # Read first few lines of the output for a preview
    try:
        with open(output_filepath, 'r', encoding='utf-8') as f:
            print("\nPreview of generated context (first 10 lines):")
            print("------------------------------------------")
            for _ in range(10):
                line = f.readline()
                if not line: break
                print(line.rstrip())
            print("------------------------------------------")
    except Exception as e:
        print(f"❌ Error reading context file: {e}")
else:
    print(f"❌ Error: '{output_filepath.name}' was not generated.")

# 5. Clean up temporary test files
# We leave the demonstration tidy, optimized for local Mac Mini environments.
print("--- 5. Cleaning up temporary demo files ---")
cleanup_test_dir(test_dir)
print(f"✅ Done: Temporary directory '{test_project_name}' removed.")
