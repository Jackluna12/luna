# 🌙 Luna - Intelligent AI Context Compressor

**Luna** is a lightweight tool designed to bridge the gap between complex local codebases and Large Language Models (LLMs).

In the era of AI-driven development (using agents like OpenClaw or Claude Code), feeding an entire repository into an LLM is often redundant. Luna solves this by intelligently scanning and summarizing your project into a single, LLM-ready context file.

---

## 🚀 Key Features

- **Smart Filtering:** Automatically ignores `.git`, `node_modules`, `__pycache__`, `venv`, and env files.
- **Context Extraction:** Captures directory structures and core code snippets (first N lines per file).
- **Broad Language Support:** Python, JS/TS, Go, Java, Rust, C/C++, Ruby, PHP, Shell, SQL, plus docs and config formats.
- **CLI:** Scan any directory, choose output path, snippet length, extra extensions and ignore rules.
- **LLM-Ready Output:** Generates a structured `luna_context.txt` for GPT-4o, Claude 3.5, and Codex.
- **Lightweight:** Zero third-party dependencies.

---

## 🛠️ Usage

1. **Clone the repository:**
```bash
git clone https://github.com/Jackluna12/luna.git
cd luna
```

2. **Summarize the current directory:**
```bash
python main.py
```

3. **Common options:**
```bash
# Scan another project, write output elsewhere
python main.py /path/to/project -o /tmp/context.txt

# Capture 20 lines per file instead of 10
python main.py --lines 20

# Include extra extensions / ignore extra names
python main.py --ext .vue --ext .svelte --ignore target
```

4. **Run the demo:**
```bash
python demo.py
```

5. **Run the tests (no dependencies needed):**
```bash
python test_luna.py
```

---

## ⚙️ Defaults

| Setting | Default |
|---|---|
| Snippet lines per file | 10 |
| Output file | `luna_context.txt` |
| Ignored | `.git`, `__pycache__`, `.vscode`, `.idea`, `node_modules`, `venv`, `.venv`, `dist`, `build`, `.env`, `LICENSE` |
| Extensions | `.py .md .txt .json .yaml .yml .toml .ini .cfg .xml .js .ts .tsx .jsx .mjs .cjs .go .java .rb .php .c .h .cpp .hpp .rs .sh .bash .sql .html .css` |
