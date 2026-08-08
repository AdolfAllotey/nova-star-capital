from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod")
ANALYSIS = BASE / "analysis"

FILES = {
    "sentiment": ANALYSIS / "average_sentiment.json",
    "sentiment_overview": ANALYSIS / "sentiment_overview.json",
    "market_regime": ANALYSIS / "market_regime_detector.json",
    "risk": ANALYSIS / "risk_engine_pro.json",
    "governance": ANALYSIS / "governance_engine_pro.json",
    "signals": ANALYSIS / "signal_candidates.json",
    "votes": ANALYSIS / "signal_votes.json",
    "movers_review": ANALYSIS / "crypto_movers_review.json",
    "manual_highlights": ANALYSIS / "crypto_market_highlights_observations.json",
    "pnl": ANALYSIS / "pnl_state.json",
}

OUT = ANALYSIS / "narrative_overview.json"


def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def main():
    data = {k: load(v, {}) for k, v in FILES.items()}

    sentiment = data["sentiment"]
    overview = data["sentiment_overview"]
    regime = data["market_regime"]
    risk = data["risk"]
    gov = data["governance"]
    signals = data["signals"] if isinstance(data["signals"], list) else []
    pnl = data["pnl"].get("summary", {}) if isinstance(data["pnl"], dict) else {}

    overall_sentiment = float(sentiment.get("overall", 0.0) or 0.0)
    sentiment_bucket = (overview.get("sentiment", {}) or {}).get("bucket", "unknown")

    action_policy = str(gov.get("action_policy") or gov.get("policy", {}).get("action_policy") or "UNKNOWN")
    hard_block = bool(gov.get("hard_block", False))
    soft_veto = bool(gov.get("soft_veto", False))

    risk_flag = str(risk.get("flag") or risk.get("risk_flag") or "unknown")
    regime_label = str(regime.get("regime") or regime.get("market_regime") or "unknown")

    candidate_tokens = [
        str(x.get("token") or x.get("symbol") or "").upper().replace("USDT", "")
        for x in signals
        if isinstance(x, dict)
    ]
    candidate_tokens = [x for x in candidate_tokens if x]

    top_tokens = [
        x.get("token")
        for x in (overview.get("top_tokens") or [])[:10]
        if isinstance(x, dict)
    ]

    headline = "PREPROD crypto running in monitored simulated mode."
    if hard_block:
        headline = "PREPROD crypto under hard-block governance."
    elif action_policy == "SIMULATED_ONLY":
        headline = "PREPROD crypto active in SIMULATED_ONLY mode with real execution disabled."

    payload = {
        "status": "ok",
        "engine": "preprod_narrative_engine_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "global_view": {
            "headline": headline,
            "regime": regime_label,
            "risk_flag": risk_flag,
            "action_policy": action_policy,
            "hard_block": hard_block,
            "soft_veto": soft_veto,
            "sentiment_score": overall_sentiment,
            "sentiment_bucket": sentiment_bucket,
            "candidate_count": len(candidate_tokens),
            "candidate_tokens": candidate_tokens,
            "top_social_tokens": top_tokens,
            "pnl_total_eur": pnl.get("total_pnl_eur"),
            "open_positions_count": pnl.get("open_positions_count"),
            "bullets": [
                f"Sentiment global: {round(overall_sentiment, 3)} ({sentiment_bucket}).",
                f"Gouvernance: {action_policy}, hard_block={hard_block}, soft_veto={soft_veto}.",
                f"Régime marché: {regime_label}; risk flag: {risk_flag}.",
                f"Signaux crypto actifs: {len(candidate_tokens)} ({', '.join(candidate_tokens) if candidate_tokens else 'aucun'}).",
                f"PnL crypto suivi: {pnl.get('total_pnl_eur')} EUR, positions ouvertes: {pnl.get('open_positions_count')}.",
            ],
        },
        "crypto_context": {
            "current_signal_candidates": candidate_tokens,
            "top_social_tokens": top_tokens,
            "movers_review": data["movers_review"].get("summary") if isinstance(data["movers_review"], dict) else {},
            "manual_highlights_status": data["manual_highlights"].get("status") if isinstance(data["manual_highlights"], dict) else None,
        },
        "sources": {k: str(v) for k, v in FILES.items()},
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
