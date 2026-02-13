import os
import json
import datetime
from typing import Any, Dict, List

from openai import OpenAI

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file, ensure_directory_exists

logger = get_logger("worst_trade_analyzer")

TRADE_SIMULATION_PATH = "data/simulation/trade_simulation.json"
WORST_TRADES_PATH = "data/risk/worst_trades.json"
WORST_TRADES_SUMMARY_PATH = "data/risk/worst_trades_summary.json"

# Optional legacy hook (if you later add an external function)
generate_worst_trades_summary = None


def _safe_list(x: Any) -> List[dict]:
    if isinstance(x, list):
        return [t for t in x if isinstance(t, dict)]
    if isinstance(x, dict):
        # Sometimes payloads are wrapped
        for k in ("trades", "data", "items", "results"):
            v = x.get(k)
            if isinstance(v, list):
                return [t for t in v if isinstance(t, dict)]
    return []


def _to_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip().replace(",", ".")
            return float(s)
    except Exception:
        pass
    return 0.0


def _trade_pnl_eur(t: dict) -> float:
    # be tolerant on keys
    return _to_float(
        t.get("pnl_eur")
        or t.get("pnl")
        or t.get("profit_eur")
        or t.get("profit")
        or t.get("realized_pnl_eur")
        or 0.0
    )


def _extract_trade_fields(t: dict) -> dict:
    token = t.get("token") or t.get("symbol") or t.get("asset")
    exchange = t.get("exchange") or t.get("venue")
    strategy = t.get("strategy") or t.get("strategy_name")
    risk_mode = t.get("risk_mode") or t.get("market_regime") or t.get("regime")
    pnl = _trade_pnl_eur(t)
    ts = t.get("timestamp") or t.get("ts") or t.get("time")
    return {
        "token": token,
        "exchange": exchange,
        "strategy": strategy,
        "risk_mode": risk_mode,
        "pnl_eur": pnl,
        "ts": ts,
    }


def _compute_worst_metrics(worst: List[dict]) -> Dict[str, Any]:
    rows = [_extract_trade_fields(t) for t in worst]
    pnls = [r["pnl_eur"] for r in rows]
    tokens = [r["token"] for r in rows if r.get("token")]
    strategies = [r["strategy"] for r in rows if r.get("strategy")]
    exchanges = [r["exchange"] for r in rows if r.get("exchange")]
    risk_modes = [r["risk_mode"] for r in rows if r.get("risk_mode")]

    total = sum(pnls) if pnls else 0.0
    avg = total / len(pnls) if pnls else 0.0

    def _top(items: List[str], n=5):
        counts: Dict[str, int] = {}
        for it in items:
            counts[it] = counts.get(it, 0) + 1
        return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]

    return {
        "n_worst": len(rows),
        "total_pnl_eur": total,
        "avg_pnl_eur": avg,
        "tokens_in_worst": tokens,
        "top_strategies": _top(strategies),
        "top_exchanges": _top(exchanges),
        "risk_modes_in_worst": risk_modes,
    }


def _generate_llm_summary(worst: List[dict], metrics: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal LLM summary generator (OpenAI SDK v1+).
    Returns a dict with keys: summary, root_causes, tokens_to_blacklist, suggested_rules (+ metrics/context are added upstream).
    """
    model = os.getenv("NSC_OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI()

    system_prompt = (
        "Tu es un risk analyst pour un bot de trading crypto (préproduction). "
        "Tu dois produire un JSON STRICT (pas de markdown, pas de texte hors JSON). "
        "Clés attendues: summary (str), root_causes (list[str]), tokens_to_blacklist (list[str]), suggested_rules (list[str]). "
        "Sois concis, actionnable, et prudent (pas de certitudes non justifiées)."
    )

    # Keep input small and stable
    worst_small = [_extract_trade_fields(t) for t in worst]

    user_prompt = json.dumps(
        {
            "context": context,
            "metrics": metrics,
            "worst_trades": worst_small,
            "instructions": [
                "Analyse les patterns (majors vs alts, stratégie, exchange, risk_mode).",
                "Donne 3-6 causes racines probables.",
                "Propose 3-8 règles concrètes (risk gates, sizing, stop, veto).",
                "Blacklist seulement si c'est clairement justifié par répétition/anomalies.",
            ],
        },
        ensure_ascii=False,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            return {"summary": str(content), "root_causes": [], "tokens_to_blacklist": [], "suggested_rules": []}
        # normalize keys if missing
        data.setdefault("summary", "")
        data.setdefault("root_causes", [])
        data.setdefault("tokens_to_blacklist", [])
        data.setdefault("suggested_rules", [])
        return data
    except Exception:
        return {"summary": str(content), "root_causes": [], "tokens_to_blacklist": [], "suggested_rules": []}


def analyze_worst_trades_and_generate_summary(top_n: int = 5) -> List[dict]:
    logger.info("📉 Risk: analyse des pires trades...")

    trades_raw = load_json_file(TRADE_SIMULATION_PATH)
    trades = _safe_list(trades_raw)
    logger.info(f"📊 Trades chargés: {len(trades)}")

    trades_sorted = sorted(trades, key=_trade_pnl_eur)
    worst = trades_sorted[:top_n] if trades_sorted else []

    ensure_directory_exists(WORST_TRADES_PATH)
    save_json_file(WORST_TRADES_PATH, worst)
    logger.info(f"✅ worst_trades.json écrit: {WORST_TRADES_PATH} (n={len(worst)})")

    # Always attempt summary (but failure is non-blocking)
    try:
        metrics = _compute_worst_metrics(worst)
        context = {
            "env": os.getenv("NSC_ENV", os.getenv("ENV", "PREPROD")),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "model": os.getenv("NSC_OPENAI_MODEL", "gpt-4o-mini"),
        }

        if generate_worst_trades_summary is not None:
            # legacy hook path
            summary_payload = generate_worst_trades_summary(worst)
            if not isinstance(summary_payload, dict):
                summary_payload = {"summary": str(summary_payload)}
        else:
            summary_payload = _generate_llm_summary(worst, metrics, context)

        if isinstance(summary_payload, dict):
            summary_payload.setdefault("metrics", metrics)
            summary_payload.setdefault("context", context)

        ensure_directory_exists(WORST_TRADES_SUMMARY_PATH)
        save_json_file(WORST_TRADES_SUMMARY_PATH, summary_payload)
        logger.info(f"✅ worst_trades_summary.json écrit: {WORST_TRADES_SUMMARY_PATH}")
    except Exception as e:
        logger.exception(f"⚠️ LLM summary failed but ignored: {e}")

    return worst


def run() -> int:
    try:
        analyze_worst_trades_and_generate_summary(top_n=5)
        return 0
    except Exception as e:
        logger.exception(f"❌ worst_trade_analyzer failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
