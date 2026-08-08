from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter(tags=["signal-board"])

SIGNAL_CANDIDATES_PATH = Path("/opt/nsc/data/preprod/analysis/signal_candidates.json")
SIGNAL_VOTES_PATH = Path("/opt/nsc/data/preprod/analysis/signal_votes.json")
SIZED_SIGNALS_PATH = Path("/opt/nsc/data/preprod/trading/sized_signals.json")
OFFENSIVE_VOTED_PATH = Path("/opt/nsc/data/preprod/equities_offensive/voting/voted_signals.json")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_list(data: Any, key: str | None = None) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and key and isinstance(data.get(key), list):
        return [x for x in data.get(key, []) if isinstance(x, dict)]
    return []


def norm_side(v: Any) -> str:
    s = str(v or "").lower()
    if s in {"buy", "long", "bullish"}:
        return "BUY"
    if s in {"sell", "short", "bearish"}:
        return "SELL"
    return str(v or "—").upper()


def norm_score(item: Dict[str, Any]) -> Any:
    return (
        item.get("score")
        if item.get("score") is not None
        else item.get("meta_score")
        if item.get("meta_score") is not None
        else item.get("meta_score_pro")
        if item.get("meta_score_pro") is not None
        else item.get("engine_score")
    )


def make_row(item: Dict[str, Any], idx: int, source: str, status: str) -> Dict[str, Any]:
    symbol = item.get("symbol") or item.get("ticker") or item.get("token") or "—"
    side = item.get("side") or item.get("direction") or item.get("action") or "—"
    reason = item.get("reason") or item.get("setup") or item.get("notes") or item.get("reasons") or "—"
    if isinstance(reason, list):
        reason = " · ".join(str(x) for x in reason[:4])

    return {
        "id": f"{source}-{idx}",
        "symbol": str(symbol).upper(),
        "side": norm_side(side),
        "qty": item.get("qty") or item.get("quantity") or item.get("target_notional_eur") or item.get("notional_eur") or "—",
        "score": norm_score(item),
        "reason": reason,
        "status": status,
        "source": source,
        "strategy": item.get("strategy") or item.get("setup") or item.get("engine") or "—",
    }


@router.get("/api/signals/board")
def signals_board() -> Dict[str, Any]:
    candidates = safe_list(load_json(SIGNAL_CANDIDATES_PATH, []))
    votes = safe_list(load_json(SIGNAL_VOTES_PATH, []))
    sized = safe_list(load_json(SIZED_SIGNALS_PATH, []))
    offensive_doc = load_json(OFFENSIVE_VOTED_PATH, {}) or {}
    offensive = safe_list(offensive_doc, "voted")

    rows: List[Dict[str, Any]] = []

    for i, item in enumerate(candidates):
        rows.append(make_row(item, i, "crypto_candidates", "CANDIDATE"))

    for i, item in enumerate(votes):
        rows.append(make_row(item, i, "crypto_votes", "VOTED"))

    for i, item in enumerate(sized):
        status = "SIZED"
        if item.get("hard_veto"):
            status = "BLOCKED"
        elif item.get("soft_veto"):
            status = "SOFT_VETO"
        rows.append(make_row(item, i, "crypto_sized", status))

    for i, item in enumerate(offensive):
        rows.append(make_row(item, i, "offensive_voted", "VOTED"))

    rows.sort(key=lambda r: float(r.get("score") or 0), reverse=True)

    return {
        "count": len(rows),
        "rows": rows[:80],
        "plan_id": None,
        "action_policy": "SIGNAL_ONLY",
        "summary": {
            "crypto_candidates": len(candidates),
            "crypto_votes": len(votes),
            "crypto_sized": len(sized),
            "offensive_voted": len(offensive),
        },
        "sources": {
            "signal_candidates": str(SIGNAL_CANDIDATES_PATH),
            "signal_votes": str(SIGNAL_VOTES_PATH),
            "sized_signals": str(SIZED_SIGNALS_PATH),
            "offensive_voted": str(OFFENSIVE_VOTED_PATH),
        },
    }
