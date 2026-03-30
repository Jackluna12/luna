# 🌙 Luna - Intelligent AI Context Compressor

**Luna** is a lightweight tool designed to bridge the gap between complex local codebases and Large Language Models (LLMs). 

In the era of AI-driven development (using agents like OpenClaw or Claude Code), feeding an entire repository into an LLM is often redundant. Luna solves this by intelligently scanning and summarizing your project into a single, LLM-ready context file.

---

## 🚀 Key Features

- **Smart Filtering:** Automatically ignores `.git`, `node_modules`, `__pycache__`, and env files.
- **Context Extraction:** Captures directory structures and core code snippets.
- **LLM-Ready Output:** Generates a structured `luna_context.txt` for GPT-4o, Claude 3.5, and Codex.
- **Lightweight:** Zero heavy dependencies. Optimized for local environments (macOS/Mac Mini).

---

## 🛠️ Usage

1. **Clone the repository:**
```bash
git clone [https://github.com/Jackluna12/luna.git](https://github.com/Jackluna12/luna.git)
cd luna
