"""Token estimation and budget enforcement.

No tokenizer dependency is bundled (keeping Luna zero-dependency), so this
uses a documented heuristic: ~4 characters per token for Latin text, ~1.5
characters per token for CJK text. It is intentionally conservative for
mixed-language codebases — treat it as an estimate, not a bill.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_CJK_RE = re.compile(
    r"[\u2e80-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]"
)


def estimate_tokens(text: str) -> int:
    """Rough token count for a piece of text."""
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    rest = len(text) - cjk
    return max(1, int(cjk / 1.5 + rest / 4))


@dataclass
class BudgetResult:
    kept: list          # items that fit
    skipped: list        # (item, tokens) pairs that did not fit
    used: int
    budget: int | None


def fit_budget(items: list, budget: int | None,
               token_fn=estimate_tokens) -> BudgetResult:
    """Greedily keep items in order until the budget is exhausted.

    ``items`` are (key, text) pairs. Returns what fit and what was cut.
    """
    kept, skipped = [], []
    used = 0
    for key, text in items:
        tokens = token_fn(text)
        if budget is not None and used + tokens > budget and kept:
            skipped.append((key, tokens))
            continue
        kept.append((key, text, tokens))
        used += tokens
    return BudgetResult(kept=kept, skipped=skipped, used=used, budget=budget)
