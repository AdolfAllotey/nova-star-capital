"""
NSC - Worst trades LLM summary helper (PREPROD-safe).

This module MUST remain import-safe even when NSC_LLM_ENABLED=0:
- No OpenAI import at module import time.
- Runtime guarded calls only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _llm_enabled() -> bool:
    v = os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def fallback_summary(worst_trades: List[dict], env: str = "PREPROD", model: str = "gpt-4o-mini") -> Dict[str, Any]:
    tokens = sorted({(t.get("token") or "UNKNOWN").upper() for t in worst_trades if isinstance(t, dict)})
    exchanges = sorted({(t.get("exchange") or "unknown").lower() for t in worst_trades if isinstance(t, dict)})
    strategies = sorted({(t.get("strategy") or "unknown") for t in worst_trades if isinstance(t, dict)})

    return {
        "summary": "LLM disabled; using fallback summary.",
        "root_causes": [],
        "tokens_to_blacklist": [],
        "suggested_rules": [],
        "metrics": {
            "n_worst": len(worst_trades),
            "tokens_in_worst": tokens,
            "top_exchanges": [[e, None] for e in exchanges],
            "top_strategies": [[s, None] for s in strategies],
        },
        "context": {
            "env": env,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
        },
        "llm_status": "disabled",
        "llm_error": None,
    }


def llm_summary(worst_trades: List[dict], env: str = "PREPROD", model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Generate a summary via OpenAI *only* if enabled.
    If disabled or any exception occurs, return fallback summary.
    """
    if not _llm_enabled():
        return fallback_summary(worst_trades, env=env, model=model)

    try:
        # Import OpenAI ONLY here
        from openai import OpenAI

        # NSC: hard-disable LLM calls in PREPROD when NSC_LLM_ENABLED=0
        import os
        if os.getenv('NSC_LLM_ENABLED','1').strip().lower() in ('0','false','no','n','off'):
            raise RuntimeError('LLM disabled (NSC_LLM_ENABLED=0)')
        client = OpenAI()

        prompt = {
            "env": env,
            "task": "Summarize worst trades and propose risk rules/blacklist candidates.",
            "worst_trades": worst_trades,
        }

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a risk analyst. Return JSON only."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.2,
        )

        content = (resp.choices[0].message.content or "").strip()
        # Try parse JSON, else wrap
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed.setdefault("context", {})
                parsed["context"].update({
                    "env": env,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "model": model,
                })
                parsed["llm_status"] = "ok"
                parsed["llm_error"] = None
                return parsed
        except Exception:
            pass

        out = fallback_summary(worst_trades, env=env, model=model)
        out["summary"] = content[:800] if content else out["summary"]
        out["llm_status"] = "ok_text"
        return out

    except Exception as e:
        out = fallback_summary(worst_trades, env=env, model=model)
        out["llm_status"] = "error"
        out["llm_error"] = {"message": str(e), "type": type(e).__name__}
        out["summary"] = "LLM failed; using fallback summary."
        return out
