# 🌙 Luna 2.0 — Intelligent AI Context Engine

Turn any codebase into LLM-ready context. Zero dependencies, Python 3.9+.

**1.x** grabbed the first N lines of every file. **2.0** understands structure:

| Feature | What it does |
|---|---|
| 🧠 AST extraction | Python files → module docstring, condensed imports, class/function signatures with docstring summaries. Bodies dropped. |
| 🔍 Heuristic signatures | JS/TS, Go, Rust, Java, C/C++, Ruby, PHP, Swift, shell, SQL… definition-looking lines harvested per language. |
| 🙈 .gitignore aware | Real `.gitignore` parsing (`*`/`?`/`[]`/`**`, dir rules, `!` negations) instead of a hardcoded blocklist. |
| 💰 Token budget | `--budget 8000`: greedy fit, docs first, reports exactly what got cut. |
| 🌿 Git aware | `--changed` / `--staged` / `--ref main`: context of only what changed, with diffs. |
| 📦 Formats | `txt` (human), `xml` (Claude-style `<documents>`), `json` (machines). |

## Quick start

```bash
python main.py                        # scan ., write luna_context.txt
python main.py -o ctx.xml -f xml      # Claude-ready XML
python main.py --budget 8000          # cap at ~8k tokens
python main.py --changed              # only diffs vs HEAD
python main.py --staged -f json       # staged changes as JSON
python demo.py                        # see it work on a fake project
python -m unittest discover -s tests  # run the test suite
```

## CLI reference

```
usage: main.py [root] [-o OUT] [-f {txt,xml,json}]
               [--mode {signatures,full}] [--budget TOKENS]
               [--lines N] [--ext .vue] [--ignore NAME]
               [--max-size KB] [--changed | --staged] [--ref REF]
               [--no-tree] [--no-gitignore]
```

## How the token estimate works

No tokenizer is bundled (zero-dependency promise). Estimation: ~4 chars/token
for Latin text, ~1.5 chars/token for CJK. Conservative by design — treat it
as a guardrail, not a bill.

## License

MIT
