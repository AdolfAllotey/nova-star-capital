from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

DATA_DIR = Path(get_data_dir()).resolve()
ROOT_DIR = DATA_DIR.parent


def _default_kill_switch() -> Dict[str, Any]:
    """Structure par défaut du kill switch global."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "enabled": False,
        "reason": "initialisation",
        "updated_at": now,
        "details": {
            "anomaly_overview": {
                "nb_anomalies": 0,
                "nb_critical": 0,
                "nb_warning": 0,
            },
            "checklist": {
                "all_ok": False,
                "score": 0.0,
            },
            "emotional_regime": {
                "regime": "unknown",
                "score_emotional": None,
                "recommended_action": None,
            },
        },
        # Mode global “hérité” / legacy : "soft" ou "hard"
        "mode": "soft",
        "enriched": {},
        "locals": [],
    }


def _build_locals_from_weak_signals(weak_signals: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construit les locals à partir de weak_signals_engine_pro.json."""
    locals_list: List[Dict[str, Any]] = []

    symbols = weak_signals.get("symbols") or []
    for sym in symbols:
        symbol = sym.get("symbol", "unknown")
        weak_kind = sym.get("weak_kind") or sym.get("label") or "none"

        if weak_kind not in ("weak_watch", "weak_avoid"):
            continue

        if weak_kind == "weak_avoid":
            mode = "soft_block"
            label = "weak_avoid"
            reason = sym.get("reason") or "Signaux faibles négatifs (weak_avoid)"
        else:
            mode = "soft"
            label = "weak_watch"
            reason = sym.get("reason") or "Signaux faibles mitigés (weak_watch)"

        locals_list.append(
            {
                "scope": f"symbol:{symbol}",
                "mode": mode,
                "source": "weak_signals_engine_pro",
                "label": label,
                "reason": reason,
                "meta_score_pro": sym.get("meta_score_pro"),
                "risk_flag": sym.get("risk_flag"),
                "cycle_regime": sym.get("cycle_regime"),
                "story_regime": sym.get("story_regime"),
            }
        )

    return locals_list


def _build_locals_from_orderflow(orderflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construit les locals à partir de orderflow_adapter.json."""
    locals_list: List[Dict[str, Any]] = []

    symbols = orderflow.get("symbols") or []
    for sym in symbols:
        symbol = sym.get("symbol", "unknown")
        risk_flag_of = sym.get("risk_flag", "ok")  # "ok", "caution", "block"
        kill_hint = sym.get("kill_switch_hint") or "none"  # "none", "soft_block", "hard_block"

        # Si tout va bien, on ne crée pas de local
        if risk_flag_of == "ok" and kill_hint in ("none", None):
            continue

        # Décision de mode local
        if kill_hint == "hard_block" or risk_flag_of == "block":
            local_mode = "hard_block"
        else:
            # "caution" ou kill_hint="soft_block"
            local_mode = "soft_block"

        reasons = sym.get("reasons") or []
        reason = reasons[0] if reasons else f"Orderflow risk={risk_flag_of}"

        locals_list.append(
            {
                "scope": f"symbol:{symbol}",
                "mode": local_mode,
                "source": "orderflow_adapter",
                "label": f"orderflow_{risk_flag_of}",
                "reason": reason,
                "spread_pct": sym.get("spread_pct"),
                "order_imbalance": sym.get("order_imbalance"),
                "spoof_score": sym.get("spoof_score"),
            }
        )

    return locals_list


def compute_kill_switch(data_dir: Path) -> Dict[str, Any]:
    """
    Kill Switch Global – Option A (conseiller).

    Lit les différents engines (risk_console, weak_signals, risk_engine, meta_score, orderflow_adapter),
    produit un mode global proposé (soft / soft_block / hard_block) et des locals par symbole.
    NE CHANGE PAS directement le mode global top-level (on reste en mode “advisory”).
    """
    analysis_dir = data_dir / "analysis"
    trading_dir = data_dir / "trading"

    logger.info("[kill_switch_global] DATA_DIR=%s", data_dir)

    # --- Lecture des JSON d'analyse ---
    risk_console = load_json_file(analysis_dir / "risk_console_overview.json", default={})
    weak_signals = load_json_file(analysis_dir / "weak_signals_engine_pro.json", default={})
    risk_engine = load_json_file(analysis_dir / "risk_engine_pro.json", default={})
    meta_score = load_json_file(analysis_dir / "meta_score_engine_pro.json", default={})
    orderflow = load_json_file(analysis_dir / "orderflow_adapter.json", default={})

    risk_flag = risk_console.get("global_flag", "ok")
    weak_stats = weak_signals.get("stats", {})
    risk_stats = risk_engine.get("stats", {})
    meta_stats = meta_score.get("stats", {})

    orderflow_flag = orderflow.get("global_flag", "ok")
    orderflow_stats = orderflow.get("stats", {})
    orderflow_symbols = orderflow.get("symbols", []) or []

    # --- Lecture de l'état existant du kill switch ---
    kill_switch_path = trading_dir / "kill_switch.json"
    kill_switch = load_json_file(kill_switch_path, default=_default_kill_switch())

    existing_mode = kill_switch.get("mode", "soft")
    existing_enabled = kill_switch.get("enabled", False)
    existing_hard_block = kill_switch.get("hard_block", False)
    existing_soft_block = kill_switch.get("soft_block", existing_mode in ("soft", "soft_block"))

    # --- Locals (weak_signals + orderflow) ---
    locals_list: List[Dict[str, Any]] = []

    locals_list.extend(_build_locals_from_weak_signals(weak_signals))
    locals_list.extend(_build_locals_from_orderflow(orderflow))

    # --- Proposition de mode global (advisory) ---
    proposed_mode = "soft"  # "soft", "soft_block", "hard_block"
    proposed_reasons: List[str] = []

    # 1) Risk console / risk engine / meta-score
    if risk_flag == "danger":
        proposed_mode = "hard_block"
        proposed_reasons.append("Risk console: flag=danger (conditions critiques).")
    elif risk_flag == "caution":
        if proposed_mode not in ("soft_block", "hard_block"):
            proposed_mode = "soft_block"
        proposed_reasons.append("Risk console: flag=caution (prudence).")

    avg_risk = risk_stats.get("avg_risk_score")
    if isinstance(avg_risk, (int, float)) and avg_risk is not None:
        if avg_risk >= 70:
            proposed_mode = "hard_block"
            proposed_reasons.append(f"Risk engine: avg_risk_score={avg_risk:.2f} (élevé).")
        elif avg_risk >= 55 and proposed_mode != "hard_block":
            if proposed_mode not in ("soft_block", "hard_block"):
                proposed_mode = "soft_block"
            proposed_reasons.append(f"Risk engine: avg_risk_score={avg_risk:.2f} (modéré).")

    avg_meta = meta_stats.get("avg_meta_score")
    if isinstance(avg_meta, (int, float)) and avg_meta is not None:
        if avg_meta <= 35:
            proposed_mode = "hard_block"
            proposed_reasons.append(f"Meta-score: avg_meta_score={avg_meta:.2f} (faible).")
        elif avg_meta <= 50 and proposed_mode != "hard_block":
            if proposed_mode not in ("soft_block", "hard_block"):
                proposed_mode = "soft_block"
            proposed_reasons.append(f"Meta-score: avg_meta_score={avg_meta:.2f} (mitigé).")

    # 2) Weak signals
    nb_weak_avoid = weak_stats.get("nb_weak_avoid", 0) or 0
    nb_weak_watch = weak_stats.get("nb_weak_watch", 0) or 0
    if nb_weak_avoid > 0:
        if proposed_mode != "hard_block":
            if proposed_mode not in ("soft_block", "hard_block"):
                proposed_mode = "soft_block"
        proposed_reasons.append(
            f"Weak signals: weak_avoid={nb_weak_avoid}, weak_watch={nb_weak_watch}."
        )

    # 3) Orderflow adapter (microstructure / spoofing / spread)
    any_block_of = any(
        (sym.get("risk_flag") == "block")
        or (sym.get("kill_switch_hint") == "hard_block")
        for sym in orderflow_symbols
    )
    any_caution_of = any(
        (sym.get("risk_flag") == "caution")
        or (sym.get("kill_switch_hint") == "soft_block")
        for sym in orderflow_symbols
    )

    if orderflow_flag == "block" or any_block_of:
        if proposed_mode != "hard_block":
            proposed_reasons.append(
                "Orderflow: conditions dangereuses (block / hard_block sur le carnet)."
            )
        proposed_mode = "hard_block"
    elif orderflow_flag == "caution" or any_caution_of:
        if proposed_mode not in ("soft_block", "hard_block"):
            proposed_reasons.append(
                "Orderflow: conditions prudentes (caution / soft_block sur le carnet)."
            )
            proposed_mode = "soft_block"

    # --- Enrichissement ---
    env = os.getenv("NSC_ENV", "PREPROD")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    summary: List[str] = []

    # Résumé kill-switch existant
    summary.append(
        f"Kill-switch existant: mode={existing_mode.upper()}, "
        f"enabled={existing_enabled}, soft_block={existing_soft_block}, hard_block={existing_hard_block}."
    )

    # Résumé weak signals
    summary.append(
        f"Weak signals: weak_avoid={nb_weak_avoid}, weak_watch={nb_weak_watch}, "
        f"global_flag={weak_stats.get('global_flag', 'unknown')}."
    )

    # Résumé orderflow
    summary.append(
        f"Orderflow: flag={orderflow_flag}, "
        f"nb_block={orderflow_stats.get('nb_block', 0)}, "
        f"nb_caution={orderflow_stats.get('nb_caution', 0)}."
    )

    # Résumé proposé
    summary.append(
        f"Proposition kill-switch global: MODE={proposed_mode.upper()} "
        f"({'; '.join(proposed_reasons) if proposed_reasons else 'aucune raison explicite'})."
    )

    enriched = {
        "timestamp": now,
        "env": env,
        "source": "kill_switch_global_v1",
        "existing": {
            "mode": existing_mode,
            "enabled": existing_enabled,
            "hard_block": existing_hard_block,
            "soft_block": existing_soft_block,
        },
        "proposed": {
            "mode": proposed_mode,
            "reasons": proposed_reasons,
        },
        "risk_console": {
            "global_flag": risk_flag,
        },
        "risk_engine": {
            "global_flag": risk_engine.get("stats", {}).get("global_flag")
            or risk_engine.get("global_flag"),
            "avg_risk_score": avg_risk,
        },
        "weak_signals": {
            "stats": weak_stats,
        },
        "meta_score": {
            "global_flag": meta_score.get("global_flag"),
            "avg_meta_score": avg_meta,
        },
        "orderflow": {
            "global_flag": orderflow_flag,
            "stats": orderflow_stats,
            "nb_symbols": orderflow_stats.get("nb_symbols"),
            "nb_block": orderflow_stats.get("nb_block"),
            "nb_caution": orderflow_stats.get("nb_caution"),
        },
        "summary": summary,
    }

    kill_switch["enriched"] = enriched
    kill_switch["locals"] = locals_list
    kill_switch["updated_at"] = now

    # On ne force PAS le mode global ici (advisory seulement)
    # => un autre module / opérateur pourra décider d'appliquer proposed.mode

    return kill_switch


def main() -> None:
    data_dir = DATA_DIR
    trading_dir = data_dir / "trading"
    trading_dir.mkdir(parents=True, exist_ok=True)

    result = compute_kill_switch(data_dir)
    out_path = trading_dir / "kill_switch.json"
    save_json_file(out_path, result)
    logger.info(
        "[kill_switch_global] kill_switch.json enrichi sauvegardé (%s, locals=%d).",
        out_path,
        len(result.get("locals", [])),
    )


if __name__ == "__main__":
    main()

