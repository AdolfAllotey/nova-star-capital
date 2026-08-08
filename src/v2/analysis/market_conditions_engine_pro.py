# src/v2/analysis/market_conditions_engine_pro.py

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file

try:
    from src.v2.utils.logger import get_logger
except ImportError:  # fallback ancien chemin
    from src.v2.logger import get_logger  # type: ignore

# IMPORTANT: wrapper unifié (qui utilise MessageBus + Event)
from src.v2.utils.event_bus import publish_event

logger = get_logger("market_conditions_engine_pro")


# ----------------------------
# Data model
# ----------------------------

@dataclass
class ComponentSpec:
    name: str
    path: str
    weight: float = 0.1
    # optionnel: mapping explicite des champs si tu veux forcer
    score_key: Optional[str] = None
    flag_key: Optional[str] = None


@dataclass
class ComponentResult:
    name: str
    present: bool
    score: Optional[float]
    flag: str
    weight: float
    path: str


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _extract_score(obj: Dict[str, Any], spec: Optional[ComponentSpec] = None) -> Optional[float]:
    """
    Récupère un score numérique (0..100) avec plusieurs fallbacks.
    """
    # 1) override config
    if spec and spec.score_key and isinstance(obj.get(spec.score_key), (int, float, str)):
        return _safe_float(obj.get(spec.score_key))

    # 2) standard keys
    for k in ("score", "global_score", "avg_score", "value"):
        if k in obj:
            s = _safe_float(obj.get(k))
            if s is not None:
                return s

    # 3) nested common patterns
    stats = obj.get("stats")
    if isinstance(stats, dict):
        for k in ("score", "global_score", "avg_score"):
            if k in stats:
                s = _safe_float(stats.get(k))
                if s is not None:
                    return s

    summary = obj.get("summary")
    if isinstance(summary, dict):
        for k in ("score", "global_score", "avg_score"):
            if k in summary:
                s = _safe_float(summary.get(k))
                if s is not None:
                    return s

    # 4) specific engines (optional)
    # signal_quality_engine_pro.json -> score est bien à la racine : déjà couvert
    return None


def _extract_flag(obj: Dict[str, Any], spec: Optional[ComponentSpec] = None) -> str:
    """
    Récupère un flag textuel. Supporte notamment:
    - flag / global_flag
    - quality_flag (signal_quality_engine_pro)
    - risk_console_flag, etc. (si un jour tu l’agrèges)
    """
    # 1) override config
    if spec and spec.flag_key and isinstance(obj.get(spec.flag_key), str):
        v = (obj.get(spec.flag_key) or "").strip()
        return v or "unknown"

    candidates: List[Tuple[str, ...]] = [
        ("flag",),
        ("global_flag",),
        ("quality_flag",),           # ✅ FIX principal (signal_quality_engine_pro.json)
        ("risk_console_flag",),
        ("status",),
        ("mode",),
        ("stats", "flag"),
        ("stats", "global_flag"),
        ("summary", "flag"),
        ("summary", "global_flag"),
    ]

    for path in candidates:
        cur: Any = obj
        ok = True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()

    return "unknown"


def _normalize_flag(flag: str) -> str:
    """
    Normalise un peu (optionnel) :
    - certain modules retournent "neutral", "no_signals", etc.
    On ne les force pas en ok/caution/danger, on les laisse tels quels.
    """
    f = (flag or "").strip().lower()
    return f or "unknown"


def _flag_to_severity(flag: str) -> str:
    """
    Convertit un flag en severity d'event.
    """
    f = (flag or "").lower()
    if f in ("danger", "critical", "hard_block", "block", "emergency"):
        return "critical"
    if f in ("caution", "warning", "degraded", "reduced"):
        return "warning"
    return "info"


def _compute_global_flag(nb_danger: int, nb_caution: int) -> str:
    if nb_danger > 0:
        return "danger"
    if nb_caution > 0:
        return "caution"
    return "ok"


def _load_components_config(data_dir: Path) -> List[ComponentSpec]:
    """
    Charge data/analysis/market_conditions_components.json.
    Format attendu (liste):
    [
      {"name": "...", "path": "analysis/xxx.json", "weight": 0.1},
      ...
    ]
    """
    cfg_path = data_dir / "analysis" / "market_conditions_components.json"
    raw = load_json_file(cfg_path, default=[])

    if not isinstance(raw, list):
        logger.warning(
            "[market_conditions_engine_pro] Config invalide (%s) : attendu list → default []",
            cfg_path,
        )
        return []

    out: List[ComponentSpec] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        path = str(it.get("path") or "").strip()
        if not name or not path:
            continue
        weight = _safe_float(it.get("weight", 0.1)) or 0.1
        score_key = it.get("score_key")
        flag_key = it.get("flag_key")
        out.append(
            ComponentSpec(
                name=name,
                path=path,
                weight=float(weight),
                score_key=str(score_key).strip() if isinstance(score_key, str) and score_key.strip() else None,
                flag_key=str(flag_key).strip() if isinstance(flag_key, str) and flag_key.strip() else None,
            )
        )
    return out


def main() -> None:
    data_dir = Path(get_data_dir())
    env = os.getenv("NSC_ENV", "PREPROD")

    logger.info("[market_conditions_engine_pro] DATA_DIR=%s, env=%s", data_dir, env)

    specs = _load_components_config(data_dir)

    components: List[ComponentResult] = []
    weighted_sum = 0.0
    weight_sum = 0.0

    nb_ok_flags = 0
    nb_caution_flags = 0
    nb_danger_flags = 0

    nb_with_score = 0

    for spec in specs:
        full_path = data_dir / spec.path
        obj = load_json_file(full_path, default=None)

        present = isinstance(obj, dict)
        if not present:
            components.append(
                ComponentResult(
                    name=spec.name,
                    present=False,
                    score=None,
                    flag="missing",
                    weight=spec.weight,
                    path=str(full_path),
                )
            )
            continue

        score = _extract_score(obj, spec=spec)
        flag = _normalize_flag(_extract_flag(obj, spec=spec))

        # flags counters
        if flag in ("danger", "critical", "hard_block", "block", "emergency"):
            nb_danger_flags += 1
        elif flag in ("caution", "warning", "degraded", "reduced"):
            nb_caution_flags += 1
        elif flag in ("ok", "info"):
            nb_ok_flags += 1
        else:
            # neutral / unknown / no_signals / etc.
            # on ne le compte pas en ok/caution/danger par défaut
            pass

        # aggregation (uniquement si score numérique)
        # Certains moteurs sortent une confidence 0..1, d'autres un score 0..100.
        # Pour l'agrégation Market Conditions, on normalise tout en 0..100.
        if score is not None:
            if 0 <= score <= 1:
                score = score * 100
            nb_with_score += 1
            weighted_sum += score * spec.weight
            weight_sum += spec.weight

        components.append(
            ComponentResult(
                name=spec.name,
                present=True,
                score=score,
                flag=flag,
                weight=spec.weight,
                path=str(full_path),
            )
        )

    # score global
    if weight_sum > 0:
        global_score = round(weighted_sum / weight_sum, 2)
    else:
        global_score = 50.0  # neutre si rien de scoré

    global_flag = _compute_global_flag(nb_danger_flags, nb_caution_flags)

    # regime (simple pour l’instant : neutral si score proche 50)
    # Tu pourras faire mieux plus tard (bull/bear/risk_on/off).
    regime = "neutral"
    if global_score >= 70:
        regime = "risk_on"
    elif global_score <= 30:
        regime = "risk_off"

    reasons: List[str] = []
    reasons.append(f"Score agrégé = {global_score:.2f} (nb_with_score={nb_with_score}, weight_sum={weight_sum:.2f}).")
    if nb_danger_flags > 0:
        reasons.append(f"{nb_danger_flags} moteur(s) en danger/critical.")
    if nb_caution_flags > 0:
        reasons.append(f"{nb_caution_flags} moteur(s) en caution/degraded/reduced.")

    result: Dict[str, Any] = {
        "generated_at": _iso_utc_now(),
        "env": env,
        "regime": regime,
        "global_flag": global_flag,
        "score": global_score,
        "metrics": {
            "nb_components": len(specs),
            "nb_components_with_score": nb_with_score,
            "weight_sum": round(weight_sum, 2),
            "nb_ok_flags": nb_ok_flags,
            "nb_caution_flags": nb_caution_flags,
            "nb_danger_flags": nb_danger_flags,
        },
        "reasons": reasons,
        "components": [asdict(c) for c in components],
    }

    out_path = data_dir / "analysis" / "market_conditions_engine_pro.json"
    now = _iso_utc_now()
    result["timestamp"] = now
    result.setdefault("generated_at", now)
    save_json_file(out_path, result)

    logger.info(
        "[market_conditions_engine_pro] env=%s, regime=%s, global_flag=%s, score=%.2f, nb_components=%d, nb_with_score=%d",
        env,
        regime,
        global_flag,
        global_score,
        len(specs),
        nb_with_score,
    )
    logger.info(
        "[market_conditions_engine_pro] market_conditions_engine_pro.json sauvegardé (regime=%s, global_flag=%s, score=%.2f)",
        regime,
        global_flag,
        global_score,
    )

    # Event payload (compatible JSON — pas de datetime brut)
    payload = {
        "timestamp": _iso_utc_now(),
        "generated_at": result["generated_at"],
        "env": env,
        "symbol": "global",
        "regime": regime,
        "global_flag": global_flag,
        "score": global_score,
        "metrics": result["metrics"],
        "reasons": reasons,
        "components": result["components"],
    }

    severity = _flag_to_severity(global_flag)

    # publish via wrapper unifié (qui s’occupe du MessageBus + Event)
    publish_event(
        event_type="market.conditions.state",
        source="market_conditions_engine_pro",
        severity=severity,
        payload=payload,
    )

    logger.info(
        "[market_conditions_engine_pro] Event publié – type=%s source=%s severity=%s",
        "market.conditions.state",
        "market_conditions_engine_pro",
        severity,
    )


if __name__ == "__main__":
    main()
