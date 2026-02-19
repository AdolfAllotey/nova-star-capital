from __future__ import annotations



def _llm_enabled() -> bool:
    import os
    v = os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    return v in ("1","true","yes","y","on")

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.file_utils import load_json_file, save_json_file
from src.v2.utils.logger import get_logger

logger = get_logger("worst_trade_analyzer")

# DATA_DIR is injected by systemd env in PREPROD
DATA_DIR = os.getenv("DATA_DIR", "/opt/nsc/data/preprod")

# Trade simulation input (fallbacks)
TRADE_SIM_FALLBACKS = [
    str(Path(DATA_DIR) / "trading" / "trade_simulation.json"),
    str(Path(DATA_DIR) / "reports" / "trade_simulation.json"),
    str(Path(DATA_DIR) / "trading" / "trades.json"),
    str(Path(DATA_DIR) / "reports" / "trades.json"),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_flag(name: str, default: str = "0") -> bool:
    v = str(os.getenv(name, default)).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _safe_exc_payload(exc: Exception) -> dict:
    payload: dict = {"message": str(exc), "type": exc.__class__.__name__}
    for attr in ("status_code", "code", "type"):
        try:
            val = getattr(exc, attr, None)
        except Exception:
            val = None
        if val is not None and val != "":
            payload[attr] = val
    return payload


def _load_trades() -> List[dict]:
    """Load trades from multiple schemas/locations (PREPROD-safe)."""
    candidates = [
        # canonical
        Path(DATA_DIR) / "trading" / "trades.json",
        Path(DATA_DIR) / "reports" / "trades.json",
        Path(DATA_DIR) / "trades.json",

        # alternate naming
        Path(DATA_DIR) / "trading" / "trade_simulation.json",
        Path(DATA_DIR) / "reports" / "trade_simulation.json",
        Path(DATA_DIR) / "trade_simulation.json",
    ]

    # include declared fallbacks too
    for fp in TRADE_SIM_FALLBACKS:
        try:
            candidates.append(Path(fp))
        except Exception:
            pass

    for c in candidates:
        data = load_json_file(str(c), default=None)

        # schema A: list[dict]
        if isinstance(data, list):
            return data

        # schema B: {"trades": [...]}
        if isinstance(data, dict) and isinstance(data.get("trades"), list):
            return data["trades"]

        # schema C: {"data": {"trades": [...]}}
        if isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, dict) and isinstance(inner.get("trades"), list):
                return inner["trades"]

    return []


def _pnl_eur(trade: dict) -> float:
    # Best effort: handle multiple schemas
    for k in ("pnl_eur", "pnl", "pnlEUR", "profit_eur", "profit"):
        v = trade.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


def _token(trade: dict) -> str:
    for k in ("token", "symbol", "base", "asset"):
        v = trade.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().upper()
    return "UNKNOWN"


def _exchange(trade: dict) -> str:
    v = trade.get("exchange") or trade.get("venue") or ""
    if isinstance(v, str) and v.strip():
        return v.strip().lower()
    return "unknown"


def _strategy(trade: dict) -> str:
    v = trade.get("strategy") or trade.get("strategy_name") or ""
    if isinstance(v, str) and v.strip():
        return v.strip()
    return "unknown"


def _risk_mode(trade: dict) -> str:
    v = trade.get("risk_mode") or trade.get("risk") or ""
    if isinstance(v, str) and v.strip():
        return v.strip()
    return "unknown"


def _select_worst(trades: List[dict], n: int = 5) -> List[dict]:
    # Sort by lowest pnl_eur
    return sorted(trades, key=_pnl_eur)[:n]


def _metrics(worst: List[dict]) -> dict:
    pnls = [_pnl_eur(t) for t in worst]
    tokens = [_token(t) for t in worst]
    exchanges = [_exchange(t) for t in worst]
    strategies = [_strategy(t) for t in worst]
    risk_modes = [_risk_mode(t) for t in worst]

    exch_counts: Dict[str, int] = {}
    for e in exchanges:
        exch_counts[e] = exch_counts.get(e, 0) + 1
    top_exchanges = sorted(exch_counts.items(), key=lambda x: x[1], reverse=True)

    strat_counts: Dict[str, int] = {}
    for s in strategies:
        strat_counts[s] = strat_counts.get(s, 0) + 1
    top_strategies = sorted(strat_counts.items(), key=lambda x: x[1], reverse=True)

    total = float(sum(pnls)) if pnls else 0.0
    avg = float(total / len(pnls)) if pnls else 0.0

    return {
        "n_worst": len(worst),
        "total_pnl_eur": total,
        "avg_pnl_eur": avg,
        "tokens_in_worst": sorted(list({t for t in tokens if t and t != "UNKNOWN"})),
        "top_strategies": top_strategies[:5],
        "top_exchanges": top_exchanges[:5],
        "risk_modes_in_worst": risk_modes,
    }


def _base_payload(worst: List[dict], metrics: dict) -> dict:
    return {
        "summary": "No worst trades to analyze." if not worst else "Worst trades analyzed (LLM pending).",
        "root_causes": [],
        "tokens_to_blacklist": [],
        "suggested_rules": [],
        "metrics": metrics or {},
        "context": {
            "env": os.getenv("NSC_ENV", "PREPROD"),
            "generated_at": _utc_now_iso(),
            "model": os.getenv("NSC_LLM_MODEL", "gpt-4o-mini"),
        },
        "llm_status": "disabled",
        "llm_error": None,
    }


def _generate_llm_summary(worst: List[dict], metrics: dict) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Returns (llm_result, llm_error_payload)
    llm_result is a dict with summary/root_causes/tokens_to_blacklist/suggested_rules (best-effort).
    """
    try:
        if not _llm_enabled():
            raise RuntimeError('NSC_LLM_ENABLED=0 (skip OpenAI)')
        from openai import OpenAI  # SDK v1+

        # NSC PREPROD: skip any OpenAI call when NSC_LLM_ENABLED=0
        import os
        if os.getenv('NSC_LLM_ENABLED','1').strip().lower() in ('0','false','no','n','off'):
            raise RuntimeError('LLM disabled (NSC_LLM_ENABLED=0)')
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("NSC_LLM_MODEL", "gpt-4o-mini")

        # Keep prompt short and deterministic (avoid blowing tokens)
        prompt = {
            "worst_trades": [
                {
                    "token": _token(t),
                    "exchange": _exchange(t),
                    "strategy": _strategy(t),
                    "risk_mode": _risk_mode(t),
                    "pnl_eur": _pnl_eur(t),
                }
                for t in worst
            ],
            "metrics": metrics,
        }

        system = (
            "You are a trading risk analyst. "
            "Return ONLY valid JSON with keys: summary (string), root_causes (list of strings), "
            "tokens_to_blacklist (list of strings), suggested_rules (list of strings). "
            "Be concise and actionable."
        )

        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            return None, {"message": "Empty LLM response", "type": "empty_response"}

        # Try parse JSON strictly
        try:
            data = json.loads(content)
        except Exception:
            # If model wrapped JSON in text, try extract first {...}
            import re
            m = re.search(r"\{[\s\S]*\}", content)
            if not m:
                return None, {"message": "LLM response not JSON", "type": "invalid_json", "raw": content[:500]}
            data = json.loads(m.group(0))

        if not isinstance(data, dict):
            return None, {"message": "LLM JSON is not an object", "type": "invalid_shape"}

        out = {
            "summary": str(data.get("summary") or "").strip(),
            "root_causes": data.get("root_causes") if isinstance(data.get("root_causes"), list) else [],
            "tokens_to_blacklist": data.get("tokens_to_blacklist") if isinstance(data.get("tokens_to_blacklist"), list) else [],
            "suggested_rules": data.get("suggested_rules") if isinstance(data.get("suggested_rules"), list) else [],
        }
        if not out["summary"]:
            out["summary"] = "LLM produced no summary."
        return out, None

    except Exception as e:
        return None, _safe_exc_payload(e)


def analyze_worst_trades_and_generate_summary() -> None:
    logger.info("📉 Risk: analyse des pires trades...")

    trades = _load_trades()
    logger.info("📊 Trades chargés: %s", len(trades))

    worst = _select_worst(trades, n=5)
    metrics = _metrics(worst)

    # Always write worst_trades.json (even empty list)
    worst_path = Path(DATA_DIR) / "risk" / "worst_trades.json"
    worst_path.parent.mkdir(parents=True, exist_ok=True)
    save_json_file(str(worst_path), worst)
    logger.info("✅ worst_trades.json écrit: %s (n=%s)", str(worst_path), len(worst))

    payload = _base_payload(worst, metrics)

    llm_enabled = _env_flag("NSC_LLM_ENABLED", default="1")
    if not llm_enabled:
        payload["summary"] = "LLM disabled (NSC_LLM_ENABLED=0)."
        payload["llm_status"] = "disabled"
    else:
        llm_result, llm_err = _generate_llm_summary(worst, metrics)
        if llm_result:
            payload["summary"] = llm_result.get("summary") or payload["summary"]
            payload["root_causes"] = llm_result.get("root_causes") or []
            payload["tokens_to_blacklist"] = llm_result.get("tokens_to_blacklist") or []
            payload["suggested_rules"] = llm_result.get("suggested_rules") or []
            payload["llm_status"] = "ok"
            payload["llm_error"] = None
        else:
            # Critical: even on error we keep a VALID payload (never {} / null)
            payload["summary"] = "LLM failed; using fallback summary."
            payload["llm_status"] = "error"
            payload["llm_error"] = llm_err

    # Finally write worst_trades_summary.json (never {}, never null)
    summary_path = Path(DATA_DIR) / "risk" / "worst_trades_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    save_json_file(str(summary_path), payload)
    logger.info("✅ worst_trades_summary.json écrit: %s", str(summary_path))



def analyze_and_notify() -> None:
    """Backward-compatible entrypoint expected by nsc.pipeline."""
    analyze_worst_trades_and_generate_summary()

def main() -> None:
    analyze_worst_trades_and_generate_summary()


if __name__ == "__main__":
    main()
