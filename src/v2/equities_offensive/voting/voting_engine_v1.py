#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        normalized = str(value).replace("Z", "+00:00")
        result = datetime.fromisoformat(normalized)

        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)

        return result.astimezone(timezone.utc)
    except Exception:
        return None


def load_json(path: Path, default: Any = None) -> Any:
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


@dataclass(frozen=True)
class EngineVoteWeight:
    engine: str
    weight: float


ENGINE_WEIGHTS = [
    EngineVoteWeight(
        engine="signal_engine_v1",
        weight=1.0,
    )
]

EXPECTED_SIGNAL_ENGINE = "signal_engine_v1"
EXPECTED_SIGNAL_UNIVERSE = "nasdaq_offensive_core"
EXPECTED_DIRECTION = "long"
EXPECTED_TIMEFRAME = "D1"

MIN_ENGINE_SCORE = 60.0
MAX_SIGNAL_AGE_MINUTES = 360.0
DEFAULT_TOP_K = 5


def data_root() -> Path:
    return Path(
        os.getenv(
            "NSC_DATA_DIR",
            "/opt/nsc/data/preprod",
        )
    )


def compute_meta_score(
    signal: Dict[str, Any],
    engine_weight: float,
) -> tuple[float, float]:
    base = float(signal.get("score") or 0.0)

    setup = str(signal.get("setup") or "").lower()

    bonuses = {
        "breakout": 5.0,
        "retest": 3.0,
        "continuation": 2.0,
    }

    setup_bonus = bonuses.get(setup, 0.0)
    final_score = (base + setup_bonus) * engine_weight

    return round(final_score, 2), setup_bonus


def load_symbol_set(
    path: Path,
) -> set[str]:
    doc = load_json(path, default={}) or {}

    if not isinstance(doc, dict):
        return set()

    symbols = doc.get("symbols") or []

    if not isinstance(symbols, list):
        return set()

    return {
        str(symbol).strip().upper()
        for symbol in symbols
        if str(symbol).strip()
    }


def validate_document(
    doc: Dict[str, Any],
    signals_path: Path,
) -> list[str]:
    errors: list[str] = []

    if doc.get("engine") != EXPECTED_SIGNAL_ENGINE:
        errors.append(
            "unexpected_signal_document_engine:"
            f"{doc.get('engine')}"
        )

    if doc.get("universe") != EXPECTED_SIGNAL_UNIVERSE:
        errors.append(
            "unexpected_signal_universe:"
            f"{doc.get('universe')}"
        )

    generated_at = parse_timestamp(doc.get("ts"))

    if generated_at is None:
        errors.append("missing_or_invalid_signal_timestamp")
    else:
        age_minutes = (
            utc_now() - generated_at
        ).total_seconds() / 60.0

        if age_minutes < -5.0:
            errors.append("signal_timestamp_in_future")

        if age_minutes > MAX_SIGNAL_AGE_MINUTES:
            errors.append(
                "stale_signal_document:"
                f"{age_minutes:.2f}min"
            )

    if not signals_path.exists():
        errors.append("signals_file_missing")

    return errors


def vote_signals(
    signals_path: str | None = None,
    out_voted: str | None = None,
    out_explain: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    root = data_root()

    signals_file = Path(
        signals_path
        or root
        / "equities_offensive/signals/signals_v1.json"
    )

    voted_file = Path(
        out_voted
        or root
        / "equities_offensive/voting/voted_signals.json"
    )

    explain_file = Path(
        out_explain
        or root
        / "equities_offensive/voting/voting_explain.json"
    )

    core_path = (
        root
        / "equities_offensive/universe/universe_filtered.json"
    )

    tactical_path = (
        root
        / "equities_offensive/universe/tactical_watchlist.json"
    )

    doc = load_json(signals_file, default={}) or {}

    if not isinstance(doc, dict):
        raise RuntimeError(
            "Le document de signaux n'est pas un objet JSON."
        )

    document_errors = validate_document(
        doc=doc,
        signals_path=signals_file,
    )

    if document_errors:
        raise RuntimeError(
            "Signal document rejected: "
            + ", ".join(document_errors)
        )

    core_symbols = load_symbol_set(core_path)
    tactical_symbols = load_symbol_set(tactical_path)

    if not core_symbols:
        raise RuntimeError(
            "L'univers Core actif est vide ou indisponible."
        )

    overlap = core_symbols & tactical_symbols

    if overlap:
        raise RuntimeError(
            "Core/Tactical overlap detected: "
            + ", ".join(sorted(overlap))
        )

    signals = doc.get("signals") or []

    if not isinstance(signals, list):
        raise RuntimeError(
            "Le champ signals n'est pas une liste."
        )

    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    explain: Dict[str, Any] = {}

    for index, signal in enumerate(signals):
        reasons: list[str] = []

        if not isinstance(signal, dict):
            rejected.append(
                {
                    "index": index,
                    "reasons": ["signal_not_an_object"],
                }
            )
            continue

        symbol = str(
            signal.get("symbol") or ""
        ).strip().upper()

        engine = str(
            signal.get("engine") or ""
        ).strip()

        direction = str(
            signal.get("direction") or ""
        ).strip().lower()

        timeframe = str(
            signal.get("timeframe") or ""
        ).strip().upper()

        setup = str(
            signal.get("setup") or ""
        ).strip().lower()

        try:
            engine_score = float(
                signal.get("score")
            )
        except Exception:
            engine_score = -1.0
            reasons.append("invalid_engine_score")

        signal_timestamp = parse_timestamp(
            signal.get("ts")
        )

        if not symbol:
            reasons.append("missing_symbol")

        if symbol not in core_symbols:
            reasons.append("symbol_not_in_active_core")

        if symbol in tactical_symbols:
            reasons.append(
                "tactical_symbol_direct_execution_forbidden"
            )

        if engine != EXPECTED_SIGNAL_ENGINE:
            reasons.append(
                f"unsupported_signal_engine:{engine}"
            )

        if direction != EXPECTED_DIRECTION:
            reasons.append(
                f"unsupported_direction:{direction}"
            )

        if timeframe != EXPECTED_TIMEFRAME:
            reasons.append(
                f"unsupported_timeframe:{timeframe}"
            )

        if engine_score < MIN_ENGINE_SCORE:
            reasons.append(
                f"engine_score_below_{MIN_ENGINE_SCORE}"
            )

        if signal_timestamp is None:
            reasons.append(
                "missing_or_invalid_signal_timestamp"
            )
        else:
            signal_age_minutes = (
                utc_now() - signal_timestamp
            ).total_seconds() / 60.0

            if signal_age_minutes < -5.0:
                reasons.append(
                    "signal_timestamp_in_future"
                )

            if (
                signal_age_minutes
                > MAX_SIGNAL_AGE_MINUTES
            ):
                reasons.append(
                    "signal_too_old:"
                    f"{signal_age_minutes:.2f}min"
                )

        weight = next(
            (
                item.weight
                for item in ENGINE_WEIGHTS
                if item.engine == engine
            ),
            0.0,
        )

        if weight <= 0:
            reasons.append(
                "engine_weight_not_positive"
            )

        if reasons:
            rejected.append(
                {
                    "symbol": symbol or None,
                    "index": index,
                    "reasons": reasons,
                }
            )
            continue

        meta_score, setup_bonus = compute_meta_score(
            signal=signal,
            engine_weight=weight,
        )

        entry = {
            "symbol": symbol,
            "direction": direction,
            "setup": setup,
            "engine": engine,
            "engine_score": round(
                engine_score,
                2,
            ),
            "engine_weight": weight,
            "setup_bonus": setup_bonus,
            "meta_score": meta_score,
            "timeframe": timeframe,
            "signal_ts": signal.get("ts"),
            "voted_at": utc_now_iso(),
            "universe": EXPECTED_SIGNAL_UNIVERSE,
            "execution_scope": "core_only",
            "tactical": False,
        }

        accepted.append(entry)

        explain[symbol] = {
            "decision": "ACCEPTED",
            "engine": engine,
            "engine_score": round(
                engine_score,
                2,
            ),
            "engine_weight": weight,
            "setup": setup,
            "setup_bonus": setup_bonus,
            "final_meta_score": meta_score,
            "core_membership": True,
            "tactical_membership": False,
            "direction": direction,
            "timeframe": timeframe,
            "signal_ts": signal.get("ts"),
            "reasons": signal.get(
                "reasons",
                [],
            ),
        }

    accepted.sort(
        key=lambda row: float(
            row.get("meta_score") or 0.0
        ),
        reverse=True,
    )

    safe_top_k = max(
        0,
        min(int(top_k), DEFAULT_TOP_K),
    )

    selected = accepted[:safe_top_k]

    generated_at = utc_now_iso()

    out = {
        "ts": generated_at,
        "engine": "voting_engine_v2_core_guarded",
        "voting_engine": (
            "voting_engine_v2_core_guarded"
        ),
        "status": "active_simulated",
        "source_signal_engine": (
            EXPECTED_SIGNAL_ENGINE
        ),
        "source_signal_universe": (
            EXPECTED_SIGNAL_UNIVERSE
        ),
        "source_signal_ts": doc.get("ts"),
        "core_universe_path": str(core_path),
        "tactical_watchlist_path": str(
            tactical_path
        ),
        "core_symbols": sorted(core_symbols),
        "tactical_symbols": sorted(
            tactical_symbols
        ),
        "count_received": len(signals),
        "count_accepted": len(accepted),
        "count_rejected": len(rejected),
        "count_in": len(accepted),
        "count_out": len(selected),
        "top_k": safe_top_k,
        "minimum_engine_score": (
            MIN_ENGINE_SCORE
        ),
        "maximum_signal_age_minutes": (
            MAX_SIGNAL_AGE_MINUTES
        ),
        "voted": selected,
        "rejected": rejected,
        "execution_scope": "core_only",
        "tactical_execution_allowed": False,
        "etf_allowed": False,
    }

    save_json(voted_file, out)

    save_json(
        explain_file,
        {
            "ts": generated_at,
            "engine": (
                "voting_engine_v2_core_guarded"
            ),
            "source_signal_ts": doc.get("ts"),
            "details": explain,
            "rejected": rejected,
        },
    )

    return out


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Equities Offensive Core-Guarded "
            "Voting Engine V2"
        )
    )

    parser.add_argument(
        "--signals",
        default=None,
    )
    parser.add_argument(
        "--out",
        default=None,
    )
    parser.add_argument(
        "--explain",
        default=None,
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    args = parser.parse_args()

    result = vote_signals(
        signals_path=args.signals,
        out_voted=args.out,
        out_explain=args.explain,
        top_k=args.top_k,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
