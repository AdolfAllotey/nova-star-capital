from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.v2.utils.file_utils import get_data_dir, save_json_file


ENGINE = "market_momentum_shadow_v1"
EPISODE_SILENCE_SECONDS = 4 * 60 * 60
MOMENTUM_MAX_AGE_SECONDS = 45 * 60

H1_MIN_CHG_24H = 20.0
H1_MIN_VOL_RATIO = 0.8
H1_MAX_VOL_RATIO = 1.5
H2_MIN_VOL_RATIO = 5.0

OBSERVATION_MIN_CHG_24H = 15.0


def _parse_dt(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_last_seen_state(
    state_path: Path,
    history_path: Path,
) -> Dict[str, datetime]:
    state: Dict[str, datetime] = {}

    raw = _read_json(state_path, {})
    last_seen = raw.get("last_seen", {}) if isinstance(raw, dict) else {}

    if isinstance(last_seen, dict):
        for symbol, value in last_seen.items():
            observed = _parse_dt(value)
            symbol_norm = str(symbol or "").lower()
            if symbol_norm and observed:
                state[symbol_norm] = observed

    # Recovery/bootstrap fallback: episode history can reconstruct at least
    # the last persisted episode timestamp if the continuity state is absent
    # or damaged.
    if not state and history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    symbol = str(row.get("symbol") or "").lower()
                    observed = _parse_dt(row.get("movers_updated_at"))

                    if symbol and observed:
                        previous = state.get(symbol)
                        if previous is None or observed > previous:
                            state[symbol] = observed
        except OSError:
            return {}

    return state


def run_shadow(
    data_dir: Path | None = None,
    *,
    now: datetime | None = None,
) -> Dict[str, Any]:
    data_dir = Path(data_dir or get_data_dir()).resolve()

    generated_dt = now or datetime.now(timezone.utc)
    if generated_dt.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    generated_dt = generated_dt.astimezone(timezone.utc)

    selected_path = data_dir / "trading" / "selected_tokens.dynamic.json"
    momentum_path = data_dir / "analysis" / "momentum_scores.json"
    snapshot_path = data_dir / "analysis" / "market_momentum_shadow.json"
    history_path = data_dir / "analysis" / "market_momentum_shadow_history.jsonl"
    state_path = data_dir / "analysis" / "market_momentum_shadow_state.json"

    selected = _read_json(selected_path, {})
    momentum = _read_json(momentum_path, {})

    mm = selected.get("market_movers", {}) if isinstance(selected, dict) else {}
    gainers = mm.get("gainers", []) if isinstance(mm, dict) else []
    movers_updated_at_raw = mm.get("updated_at") if isinstance(mm, dict) else None
    movers_updated_at = _parse_dt(movers_updated_at_raw)

    momentum_generated_raw = (
        momentum.get("generated_at") if isinstance(momentum, dict) else None
    )
    momentum_source_raw = (
        momentum.get("source_timestamp") if isinstance(momentum, dict) else None
    )

    momentum_generated_at = _parse_dt(momentum_generated_raw)
    momentum_source_timestamp = _parse_dt(momentum_source_raw)

    momentum_fresh = False
    momentum_age_seconds = None

    if momentum_source_timestamp is not None:
        momentum_age_seconds = (
            generated_dt - momentum_source_timestamp
        ).total_seconds()
        momentum_fresh = (
            0.0 <= momentum_age_seconds <= MOMENTUM_MAX_AGE_SECONDS
        )

    scores = momentum.get("scores", {}) if isinstance(momentum, dict) else {}
    if not isinstance(scores, dict):
        scores = {}

    last_seen_state = _load_last_seen_state(state_path, history_path)

    observations = []
    new_episodes = []

    for mover in gainers:
        if not isinstance(mover, dict):
            continue

        pair = str(mover.get("pair") or "").upper()
        symbol = pair.lower()

        try:
            chg_24h = float(mover.get("chg_24h"))
        except (TypeError, ValueError):
            continue

        if not pair or chg_24h < OBSERVATION_MIN_CHG_24H:
            continue

        score = scores.get(symbol, {})
        if not isinstance(score, dict):
            score = {}

        vol_ratio = score.get("vol_ratio")
        vol_ratio_state = score.get("vol_ratio_state", "UNKNOWN")

        feature_available = (
            momentum_fresh
            and vol_ratio_state == "AVAILABLE"
            and isinstance(vol_ratio, (int, float))
        )

        ge15 = chg_24h >= 15.0
        ge20 = chg_24h >= 20.0
        ge30 = chg_24h >= 30.0

        if feature_available:
            h1 = bool(
                ge20
                and H1_MIN_VOL_RATIO
                <= float(vol_ratio)
                < H1_MAX_VOL_RATIO
            )
            h2 = bool(float(vol_ratio) >= H2_MIN_VOL_RATIO)
            hypothesis_state = "EVALUABLE"
            reason = "canonical_vol_ratio_available_and_fresh"
        else:
            h1 = None
            h2 = None
            hypothesis_state = "UNKNOWN"

            if not momentum_fresh:
                reason = "momentum_source_missing_or_stale"
            elif vol_ratio_state != "AVAILABLE":
                reason = "vol_ratio_unknown"
            else:
                reason = "vol_ratio_invalid"

        previous_seen = last_seen_state.get(symbol)
        is_new_episode = False

        if movers_updated_at is not None:
            if previous_seen is None:
                is_new_episode = True
            elif movers_updated_at > previous_seen:
                gap = (movers_updated_at - previous_seen).total_seconds()
                is_new_episode = gap > EPISODE_SILENCE_SECONDS

        row = {
            "engine": ENGINE,
            "symbol": symbol,
            "pair": pair,
            "token": mover.get("token") or mover.get("symbol"),
            "source": mover.get("source"),
            "movers_updated_at": movers_updated_at_raw,
            "momentum_generated_at": momentum_generated_raw,
            "momentum_source_timestamp": momentum_source_raw,
            "momentum_source_file": momentum.get("source_file"),
            "momentum_age_seconds": momentum_age_seconds,
            "chg_24h": chg_24h,
            "ge15": ge15,
            "ge20": ge20,
            "ge30": ge30,
            "vol_ratio": vol_ratio if feature_available else None,
            "vol_ratio_state": (
                "AVAILABLE" if feature_available else "UNKNOWN"
            ),
            "hypothesis_state": hypothesis_state,
            "h1": h1,
            "h2": h2,
            "reason": reason,
            "is_new_episode": is_new_episode,
            "episode_silence_seconds": EPISODE_SILENCE_SECONDS,
        }

        observations.append(row)

        if is_new_episode:
            new_episodes.append(row)

        # Continuity tracks every valid mover presence, not only episode
        # creation. Never move state backwards on an older/replayed snapshot.
        if movers_updated_at is not None:
            previous = last_seen_state.get(symbol)
            if previous is None or movers_updated_at > previous:
                last_seen_state[symbol] = movers_updated_at

    # Persist new episodes first. If state persistence subsequently fails,
    # history remains sufficient to prevent loss of the episode itself.
    for row in new_episodes:
        _append_jsonl(history_path, row)

    continuity_state = {
        "engine": ENGINE,
        "updated_at": generated_dt.isoformat(),
        "last_seen": {
            symbol: observed.isoformat()
            for symbol, observed in sorted(last_seen_state.items())
        },
    }
    save_json_file(state_path, continuity_state)

    result = {
        "engine": ENGINE,
        "generated_at": generated_dt.isoformat(),
        "mode": "SHADOW_ONLY",
        "decision_impact": False,
        "execution_impact": False,
        "selected_tokens_file": str(selected_path),
        "momentum_file": str(momentum_path),
        "movers_updated_at": movers_updated_at_raw,
        "momentum_source_timestamp": momentum_source_raw,
        "momentum_fresh": momentum_fresh,
        "momentum_max_age_seconds": MOMENTUM_MAX_AGE_SECONDS,
        "episode_silence_seconds": EPISODE_SILENCE_SECONDS,
        "definitions": {
            "observation": "market_momentum gainer with chg_24h >= 15",
            "h1": "chg_24h >= 20 and 0.8 <= vol_ratio < 1.5",
            "h2": "vol_ratio >= 5",
            "ge_thresholds": [15, 20, 30],
        },
        "observations_count": len(observations),
        "new_episodes_count": len(new_episodes),
        "observations": observations,
    }

    save_json_file(snapshot_path, result)
    return result


def main() -> None:
    run_shadow()


if __name__ == "__main__":
    main()
