from __future__ import annotations
from typing import Dict, List

def combine_scores(momentum: Dict[str, float],
                   whale: Dict[str, float],
                   sentiment: Dict[str, float],
                   w_mom: float = 0.5,
                   w_whale: float = 0.3,
                   w_sent: float = 0.2) -> Dict[str, float]:
    all_syms = set(momentum) | set(whale) | set(sentiment)
    out = {}
    for s in all_syms:
        m = momentum.get(s, 0.0)
        w = whale.get(s, 0.0)
        se = sentiment.get(s, 0.0)
        out[s] = w_mom*m + w_whale*w + w_sent*se
    return out

def top_n(scores: Dict[str, float], n: int = 5) -> List[str]:
    return [s for s,_ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:n]]
