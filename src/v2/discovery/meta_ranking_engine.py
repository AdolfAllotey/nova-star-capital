from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("DATA_DIR") or "/opt/nsc/data/preprod")

DISCOVERY_PATH = DATA_DIR / "discovery" / "discovery_candidates.json"
PERSISTENCE_PATH = DATA_DIR / "discovery" / "persistence_summary.json"
SOCIAL_PATH = DATA_DIR / "trading" / "selected_tokens.dynamic.json"
OUT_PATH = DATA_DIR / "discovery" / "meta_rankings.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def main() -> None:
    discovery = load_json(DISCOVERY_PATH, default={}) or {}
    persistence = load_json(PERSISTENCE_PATH, default={}) or {}
    social = load_json(SOCIAL_PATH, default={}) or {}

    rows: dict[str, dict] = {}

    for item in discovery.get("items", []) if isinstance(discovery.get("items"), list) else []:
        symbol = str(item.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        rows.setdefault(symbol, {"symbol": symbol})
        rows[symbol].update({
            "discovery_score": float(item.get("discovery_score") or 0.0),
            "chg_24h": float(item.get("chg_24h") or 0.0),
            "sources_count": int(item.get("sources_count") or len(item.get("discovery_sources") or [])),
            "discovery_sources": item.get("discovery_sources") or [],
            "tradable": bool(item.get("tradable")),
            "observation_only": bool(item.get("observation_only")),
            "pair": item.get("pair"),

            # RC2 Strategic Semantics V2:
            # Preserve both observation-layer intelligence and the
            # execution-venue reality used for investment decisions.
            "observed_pair": item.get("observed_pair"),
            "observed_chg_24h": item.get("observed_chg_24h"),
            "observed_source": item.get("observed_source"),

            "execution_confirmed": bool(
                item.get("execution_confirmed", False)
            ),
            "execution_pair": item.get("execution_pair"),
            "execution_chg_24h": item.get("execution_chg_24h"),
            "execution_price": item.get("execution_price"),
            "execution_source": item.get("execution_source"),
            "execution_sources": item.get("execution_sources") or [],

            "cross_source_direction_conflict": bool(
                item.get(
                    "cross_source_direction_conflict",
                    False,
                )
            ),
            "cross_source_conflict_details": (
                item.get(
                    "cross_source_conflict_details"
                )
                or {}
            ),
        })

    for item in persistence.get("top_persistent", []) if isinstance(persistence.get("top_persistent"), list) else []:
        symbol = str(item.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        rows.setdefault(symbol, {"symbol": symbol})
        rows[symbol].update({
            "persistence_score": float(item.get("persistence_score") or 0.0),
            "persistence_status": item.get("persistence_status"),
            "hours_present": float(item.get("hours_present") or 0.0),
            "observations": int(item.get("observations") or 0),
            "gain_delta": float(item.get("gain_delta") or 0.0),
        })

    for item in social.get("items", []) if isinstance(social.get("items"), list) else []:
        symbol = str(item.get("token") or item.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        rows.setdefault(symbol, {"symbol": symbol})
        rows[symbol].update({
            "social_score": float(item.get("score") or 0.0),
            "social_mentions": int(item.get("mentions") or 0),
            "social_source_count": int(item.get("source_count") or len(item.get("sources") or [])),
        })

    ranked = []

    for symbol, r in rows.items():
        discovery_score = float(r.get("discovery_score") or 0.0)
        persistence_score = float(r.get("persistence_score") or 0.0)
        social_score = float(r.get("social_score") or 0.0)

        # ------------------------------------------------------------
        # RC2 META RANKING STRATEGIC SEMANTICS V2
        #
        # Observation data helps discovery.
        # Execution-venue data governs executable momentum.
        #
        # If an NSC execution venue confirms the asset, its 24h move
        # becomes the decision momentum source of truth.
        # Otherwise we retain the observed move for intelligence only.
        # ------------------------------------------------------------
        observed_chg_24h = float(
            r.get("observed_chg_24h")
            if r.get("observed_chg_24h") is not None
            else (r.get("chg_24h") or 0.0)
        )

        execution_confirmed = bool(
            r.get("execution_confirmed", False)
        )

        execution_chg_raw = r.get(
            "execution_chg_24h"
        )

        try:
            execution_chg_24h = (
                float(execution_chg_raw)
                if execution_chg_raw is not None
                else None
            )
        except Exception:
            execution_chg_24h = None

        direction_conflict = bool(
            r.get(
                "cross_source_direction_conflict",
                False,
            )
        )

        if (
            execution_confirmed
            and execution_chg_24h is not None
        ):
            decision_chg_24h = execution_chg_24h
            momentum_source = "execution_venue"
        else:
            decision_chg_24h = observed_chg_24h
            momentum_source = "observation_only"

        # Backward-compatible alias:
        # `chg_24h` in Meta Ranking now represents the decision-layer
        # momentum used by the ranking, while observed_chg_24h remains
        # explicitly available for discovery explainability.
        chg_24h = decision_chg_24h

        if chg_24h <= 0:
            momentum_score = 0.0
        elif chg_24h > 60:
            momentum_score = 45.0
        else:
            momentum_score = clamp(
                (chg_24h / 60.0) * 100.0
            )

        sources_count = int(r.get("sources_count") or 0)
        source_score = clamp(sources_count * 25.0)

        discovery_contribution = discovery_score * 0.30
        persistence_contribution = persistence_score * 0.25
        social_contribution = social_score * 0.20
        momentum_contribution = momentum_score * 0.15
        source_contribution = source_score * 0.10

        meta_rank = (
            discovery_contribution
            + persistence_contribution
            + social_contribution
            + momentum_contribution
            + source_contribution
        )

        risk_flags = []

        if chg_24h > 60:
            risk_flags.append("extreme_pump")

        if not execution_confirmed:
            risk_flags.append(
                "not_confirmed_execution_venue"
            )

        if not r.get("tradable"):
            risk_flags.append(
                "not_confirmed_tradable"
            )

        if r.get("observation_only"):
            risk_flags.append(
                "observation_only"
            )

        # A positive observation on one source and a negative move on
        # the actual execution venue is not an executable long signal.
        if direction_conflict:
            risk_flags.append(
                "cross_source_direction_conflict"
            )

        execution_eligible = (
            execution_confirmed
            and r.get("tradable") is True
            and not r.get("observation_only")
            and not direction_conflict
            and "extreme_pump" not in risk_flags
        )

        recommended = (
            meta_rank >= 70
            and execution_eligible
            and chg_24h >= 15
            and chg_24h <= 60
        )

        if direction_conflict:
            verdict = (
                "AVOID_DIRECTION_CONFLICT"
            )
        elif "extreme_pump" in risk_flags:
            verdict = (
                "AVOID_EXTREME_PUMP"
            )
        elif recommended:
            verdict = (
                "GOOD_CANDIDATE"
            )
        elif (
            execution_eligible
            and chg_24h >= 15
        ):
            verdict = (
                "WATCH_TRADABLE"
            )
        elif not execution_confirmed:
            verdict = (
                "WATCH_ONLY_NOT_EXECUTABLE"
            )
        elif not r.get("tradable"):
            verdict = (
                "WATCH_ONLY_NOT_TRADABLE"
            )
        else:
            verdict = "LOW_PRIORITY"

        positive_drivers = []
        negative_drivers = []

        if discovery_score >= 70:
            positive_drivers.append("strong_discovery_score")
        if persistence_score >= 55:
            positive_drivers.append("persistent_market_interest")
        if social_score >= 60:
            positive_drivers.append("strong_social_signal")
        if 15 <= chg_24h <= 60:
            positive_drivers.append("healthy_24h_momentum")
        if execution_confirmed:
            positive_drivers.append(
                "execution_venue_confirmed"
            )

        if (
            execution_eligible
            and r.get("tradable") is True
        ):
            positive_drivers.append(
                "tradable_confirmed"
            )

        if chg_24h > 60:
            negative_drivers.append(
                "24h_move_above_safety_band"
            )

        if not execution_confirmed:
            negative_drivers.append(
                "execution_venue_not_confirmed"
            )

        if not r.get("tradable"):
            negative_drivers.append(
                "not_tradable_on_confirmed_execution_venues"
            )

        if r.get("observation_only"):
            negative_drivers.append(
                "observation_only_source"
            )

        if direction_conflict:
            negative_drivers.append(
                "cross_source_direction_conflict"
            )

        if meta_rank < 50:
            negative_drivers.append(
                "meta_rank_below_decision_threshold"
            )

        explainability = {
            "breakdown": {
                "discovery": round(discovery_contribution, 2),
                "persistence": round(persistence_contribution, 2),
                "social": round(social_contribution, 2),
                "momentum": round(momentum_contribution, 2),
                "sources": round(source_contribution, 2),
            },
            "positive_drivers": positive_drivers,
            "negative_drivers": negative_drivers,
            "verdict": verdict,
            "summary": (
                f"{symbol}: {verdict} | meta_rank={meta_rank:.2f} | "
                f"execution_eligible={execution_eligible} | "
                f"decision_chg24h={chg_24h:.2f}% | "
                f"momentum_source={momentum_source}"
            ),
        }

        out = dict(r)
        out.update({
            "meta_rank": round(meta_rank, 2),
            "momentum_score": round(momentum_score, 2),

            "decision_chg_24h": round(
                decision_chg_24h,
                4,
            ),
            "momentum_source": momentum_source,

            "execution_eligible": bool(
                execution_eligible
            ),

            "source_score": round(source_score, 2),
            "risk_flags": risk_flags,
            "recommended": recommended,
            "verdict": verdict,
            "explainability": explainability,
            "reason": (
                f"meta_rank={meta_rank:.2f} | discovery={discovery_score:.2f}, "
                f"persistence={persistence_score:.2f}, social={social_score:.2f}, "
                f"momentum={momentum_score:.2f}, sources={source_score:.2f}"
            ),
        })
        ranked.append(out)

    ranked.sort(key=lambda x: x.get("meta_rank", 0.0), reverse=True)

    payload = {
        "status": "ok",
        "generated_at": utc_now(),
        "engine": "meta_ranking_engine_v1",
        "semantics_version": "v2_execution_aware",
        "mode": "execution_governance",
        "weights": {
            "discovery_score": 0.30,
            "persistence_score": 0.25,
            "social_score": 0.20,
            "momentum_score": 0.15,
            "source_score": 0.10,
        },
        "count": len(ranked),
        "recommended_count": len([x for x in ranked if x.get("recommended")]),
        "items": ranked,
    }

    save_json(OUT_PATH, payload)

    print({
        "output": str(OUT_PATH),
        "engine": "meta_ranking_engine_v1",
        "count": len(ranked),
        "recommended_count": payload["recommended_count"],
        "top": [x["symbol"] for x in ranked[:10]],
    })


if __name__ == "__main__":
    main()
