from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/opt/nsc/data/preprod")
ANALYSIS = BASE / "analysis"

FILES = {
    "manual": ANALYSIS / "crypto_market_highlights_observations.json",
    "signals": ANALYSIS / "signal_candidates.json",
    "orders": BASE / "trading/execution_plan.json",
    "positions": BASE / "trading/open_positions.json",
    "sentiment": ANALYSIS / "sentiment_overview.json",
    "combined_movers": BASE / "market/top_movers_combined.json",
}

OUT = ANALYSIS / "crypto_highlights_vs_detection.json"


def load(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def norm(x):
    return str(x or "").upper().replace("USDT", "").replace("/", "").replace("-", "").strip()


def extract_manual_tokens(manual):
    gainers, losers = [], []
    for obs in manual.get("observations", []):
        for item in obs.get("gainers", []) or []:
            gainers.append({
                "token": norm(item.get("token")),
                "change_pct": item.get("change_pct"),
                "observed_at": obs.get("observed_at"),
                "note": item.get("note"),
                "external_source": "bitpanda_manual_screenshot",
            })
        for item in obs.get("losers", []) or []:
            losers.append({
                "token": norm(item.get("token")),
                "change_pct": item.get("change_pct"),
                "observed_at": obs.get("observed_at"),
                "note": item.get("note"),
                "external_source": "bitpanda_manual_screenshot",
            })
    return gainers, losers


def main():
    data = {k: load(v, {}) for k, v in FILES.items()}

    manual_gainers, manual_losers = extract_manual_tokens(data["manual"])

    signal_tokens = {
        norm(x.get("token") or x.get("symbol") or x.get("pair"))
        for x in data["signals"]
        if isinstance(x, dict)
    } if isinstance(data["signals"], list) else set()

    orders = data["orders"].get("orders", []) if isinstance(data["orders"], dict) else []
    order_tokens = {
        norm(x.get("token") or x.get("symbol") or x.get("pair"))
        for x in orders
        if isinstance(x, dict)
    }

    position_tokens = {
        norm(x.get("token") or x.get("symbol") or x.get("pair"))
        for x in data["positions"]
        if isinstance(x, dict)
    } if isinstance(data["positions"], list) else set()

    social_tokens = {
        norm(x.get("token"))
        for x in (data["sentiment"].get("top_tokens", []) if isinstance(data["sentiment"], dict) else [])
        if isinstance(x, dict)
    }

    mover_items = data["combined_movers"].get("items", []) if isinstance(data["combined_movers"], dict) else []
    combined_map = {
        norm(x.get("symbol")): x
        for x in mover_items
        if isinstance(x, dict)
    }

    def classify(item):
        token = item["token"]
        mover = combined_map.get(token, {})
        tradable = bool(mover.get("tradable"))
        observation_only = bool(mover.get("observation_only"))
        in_nsc_market_feed = token in combined_map

        captured = token in signal_tokens or token in order_tokens or token in position_tokens

        if captured:
            gap_type = "captured_by_nsc"
        elif in_nsc_market_feed and tradable:
            gap_type = "tradable_but_not_selected"
        elif in_nsc_market_feed and observation_only:
            gap_type = "external_observation_only"
        else:
            gap_type = "external_not_in_nsc_feed"

        return {
            **item,
            "in_signal_candidates": token in signal_tokens,
            "in_execution_orders": token in order_tokens,
            "in_open_positions": token in position_tokens,
            "in_social_top_tokens": token in social_tokens,
            "in_nsc_market_feed": in_nsc_market_feed,
            "nsc_tradable": tradable,
            "observation_only": observation_only,
            "preferred_exchange": mover.get("preferred_exchange"),
            "pair": mover.get("pair"),
            "captured_by_nsc": captured,
            "gap_type": gap_type,
        }

    gainers_analysis = [classify(x) for x in manual_gainers]
    losers_analysis = [classify(x) for x in manual_losers]

    captured_gainers = [x for x in gainers_analysis if x["captured_by_nsc"]]
    external_not_in_feed = [x for x in gainers_analysis if x["gap_type"] == "external_not_in_nsc_feed"]
    tradable_but_not_selected = [x for x in gainers_analysis if x["gap_type"] == "tradable_but_not_selected"]
    observation_only = [x for x in gainers_analysis if x["gap_type"] == "external_observation_only"]

    reversing_tokens = []
    gainers_by_token = {x["token"]: x for x in manual_gainers}
    for loser in manual_losers:
        if loser["token"] in gainers_by_token:
            reversing_tokens.append({
                "token": loser["token"],
                "previous_gainer": gainers_by_token[loser["token"]],
                "later_loser": loser,
            })

    payload = {
        "status": "ok",
        "engine": "crypto_highlights_vs_detection_v2_external_aware",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "manual_gainers_count": len(manual_gainers),
            "manual_losers_count": len(manual_losers),
            "nsc_signal_tokens_count": len(signal_tokens),
            "nsc_order_tokens_count": len(order_tokens),
            "nsc_open_positions_count": len(position_tokens),
            "captured_gainers_count": len(captured_gainers),
            "external_not_in_nsc_feed_count": len(external_not_in_feed),
            "tradable_but_not_selected_count": len(tradable_but_not_selected),
            "observation_only_count": len(observation_only),
            "reversing_tokens_count": len(reversing_tokens),
        },
        "manual_gainers_analysis": gainers_analysis,
        "manual_losers_analysis": losers_analysis,
        "captured_gainers": captured_gainers,
        "external_not_in_nsc_feed": external_not_in_feed,
        "tradable_but_not_selected": tradable_but_not_selected,
        "observation_only": observation_only,
        "reversing_tokens": reversing_tokens,
        "diagnosis": [
            f"{len(captured_gainers)} Bitpanda/manual gainers were captured by NSC.",
            f"{len(external_not_in_feed)} Bitpanda/manual gainers are outside NSC market feed, so they are observation gaps, not execution failures.",
            f"{len(tradable_but_not_selected)} gainers were tradable in NSC feed but not selected.",
            f"{len(reversing_tokens)} tokens reversed from gainer to loser, useful for late-pump risk calibration.",
        ],
        "recommendations": [
            "Do not treat Bitpanda-only movers as direct NSC misses unless Bitpanda or an equivalent tradable venue is connected.",
            "Use external movers as benchmark/watchlist to improve market awareness.",
            "Focus audit on tradable_but_not_selected tokens first.",
            "Keep reversing tokens as negative examples for late-pump and reversal filters.",
        ],
        "sources": {k: str(v) for k, v in FILES.items()},
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
