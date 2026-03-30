# 🌙 Luna - Intelligent AI Context Compressor

**Luna** is a lightweight, high-efficiency tool designed to bridge the gap between complex local codebases and Large Language Models (LLMs). 

In the era of AI-driven development (using agents like OpenClaw or Claude Code), feeding an entire repository into an LLM is often expensive, redundant, or exceeds context limits. Luna solves this by intelligently scanning, filtering, and summarizing your project into a single, LLM-ready context file.

---

## 🚀 Key Features

- **Smart Filtering:** Automatically ignores non-essential directories like `.git`, `node_modules`, `__pycache__`, and environment files.
- **Context Extraction:** Captures directory structures and core code snippets (metadata) to give the AI a bird's-eye view of your project.
- **LLM-Ready Output:** Generates a clean, structured `luna_context.txt` designed for easy consumption by GPT-4o, Claude 3.5, and Codex.
- **Lightweight & Fast:** Zero heavy dependencies. Runs directly on local environments (optimized for macOS/Mac Mini).

---

## 🛠️ Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Jackluna12/luna.git](https://github.com/Jackluna12/luna.git)
   cd luna
