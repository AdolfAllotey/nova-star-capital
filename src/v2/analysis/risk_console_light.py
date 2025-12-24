# src/v2/analysis/risk_console_light.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    load_json_file,
    save_json_file,
    get_data_dir,
)

logger = get_logger(__name__)

# DATA_DIR dérivé de l'env (NSC_DATA_DIR) via get_data_dir()
DATA_DIR = Path(get_data_dir()).resolve()
ROOT_DIR = DATA_DIR.parent


def _merge_flag(current: str, new: str) -> str:
    """
    Combine deux flags de sévérité (ok < caution < danger < block).
    """
    order = {"ok": 0, "caution": 1, "danger": 2, "block": 3}
    if new not in order:
        return current
    if current not in order:
        return new
    return new if order[new] > order[current] else current


def compute_risk_console(data_dir: Path | str | None = None) -> Dict[str, Any]:
    """
    Construit une vue consolidée des risques à partir des différents engines.
    """
    if data_dir is None:
        data_dir = DATA_DIR
    data_dir = Path(data_dir)
    analysis_dir = data_dir / "analysis"

    overview: Dict[str, Any] = {}
    reasons: List[str] = []
    global_flag: str = "ok"

    # ---------- 1) Governor / kill switch ----------
    kill_path = data_dir / "trading" / "kill_switch.json"
    kill_raw = load_json_file(kill_path, default={})

    if kill_raw:
        governor_flag = (
            kill_raw.get("governor_flag")
            or kill_raw.get("flag")
            or "ok"
        )

        overview["governor"] = {
            "flag": governor_flag,
            "reason": kill_raw.get("reason"),
        }

        if governor_flag == "soft_block":
            global_flag = _merge_flag(global_flag, "caution")
            reasons.append("Governor flag=soft_block")
        elif governor_flag == "hard_block":
            global_flag = _merge_flag(global_flag, "block")
            reasons.append("Governor flag=hard_block")
    else:
        overview["governor"] = None

    # ---------- 2) Engines de marché / structure ----------
    engines_specs = [
        ("momentum_4_0", "momentum_engine_4_0.json", "Momentum 4.0"),
        ("liquidity_pro", "liquidity_engine_pro.json", "Liquidity Engine Pro"),
        ("cycle_pro", "cycle_engine_pro.json", "Cycle Engine Pro"),
        ("story_pro", "story_engine_pro.json", "Story Engine Pro"),
        ("sector_pro", "sector_engine_pro.json", "Sector Engine Pro"),
        ("cross_asset_pro", "cross_asset_engine_pro.json", "Cross-Asset Engine Pro"),
        ("flow_pro", "flow_engine_pro.json", "Flow Engine Pro"),
        ("meta_score_pro", "meta_score_engine_pro.json", "Meta-Score Pro"),
        ("risk_engine_pro", "risk_engine_pro.json", "Risk Engine Pro"),
        ("weak_signals_engine_pro", "weak_signals_engine_pro.json", "Weak Signals Engine Pro"),
    ]

    for key, filename, label in engines_specs:
        path = analysis_dir / filename
        raw = load_json_file(path, default={})
        stats = raw.get("stats") if isinstance(raw, dict) else {}

        overview[key] = stats or None
        if not stats:
            continue

        engine_flag = stats.get("global_flag")

        # Momentum 4.0
        if key == "momentum_4_0":
            nb_soft = stats.get("nb_soft_veto", 0)
            if nb_soft > 0:
                reasons.append("Momentum 4.0: plusieurs soft vetos / contexte mitigé")
                global_flag = _merge_flag(global_flag, "caution")

        # Cycle Pro
        if key == "cycle_pro":
            if engine_flag == "caution":
                reasons.append("Cycle prudent (flag=caution)")
                global_flag = _merge_flag(global_flag, "caution")
            elif engine_flag == "danger":
                reasons.append("Cycle en danger (flag=danger)")
                global_flag = _merge_flag(global_flag, "danger")

        # Story Engine Pro
        if key == "story_pro":
            if engine_flag == "caution":
                reasons.append("Narrative fragile / non alignée (Story Engine Pro)")
                global_flag = _merge_flag(global_flag, "caution")

        # Sector Engine Pro
        if key == "sector_pro":
            if engine_flag == "caution":
                reasons.append("Rotation sectorielle prudente (flag=caution)")
                global_flag = _merge_flag(global_flag, "caution")
            elif engine_flag == "danger":
                reasons.append("Rotation sectorielle défavorable (flag=danger)")
                global_flag = _merge_flag(global_flag, "danger")

        # Cross-Asset Engine Pro
        if key == "cross_asset_pro":
            if engine_flag == "caution":
                reasons.append("Risque cross-asset équilibré mais prudent (flag=caution)")
                global_flag = _merge_flag(global_flag, "caution")
            elif engine_flag == "danger":
                reasons.append("Risque cross-asset élevé (flag=danger)")
                global_flag = _merge_flag(global_flag, "danger")

        # Flow Engine Pro : pour le moment, on se contente du flag global

        # Meta-score Pro
        if key == "meta_score_pro":
            if engine_flag == "caution":
                reasons.append("Meta-score global mitigé (caution)")
                global_flag = _merge_flag(global_flag, "caution")
            elif engine_flag == "danger":
                reasons.append("Meta-score global dégradé (danger)")
                global_flag = _merge_flag(global_flag, "danger")

        # Risk Engine Pro
        if key == "risk_engine_pro":
            if engine_flag == "caution":
                reasons.append("Risk Engine Pro en mode prudence (caution)")
                global_flag = _merge_flag(global_flag, "caution")
            elif engine_flag == "danger":
                reasons.append("Risk Engine Pro en mode danger")
                global_flag = _merge_flag(global_flag, "danger")

        # Weak Signals Engine Pro
        if key == "weak_signals_engine_pro":
            nb_avoid = stats.get("nb_weak_avoid", 0)
            if nb_avoid > 0:
                reasons.append("Signaux faibles négatifs majoritaires (weak_avoid)")
                global_flag = _merge_flag(global_flag, "caution")

    # ---------- 3) Portfolio Engine Pro (concentration, contraintes) ----------
    portfolio_path = analysis_dir / "portfolio_engine_pro.json"
    portfolio_raw = load_json_file(portfolio_path, default={})

    if portfolio_raw:
        p_stats = portfolio_raw.get("stats", {})
        constraints = portfolio_raw.get("constraints", {})

        overview["portfolio_engine_pro"] = {
            "status": constraints.get("status", "unknown"),
            "herfindahl_index": constraints.get("herfindahl_index"),
            "largest_symbol_weight": constraints.get("largest_symbol_weight"),
        }

        if constraints.get("status") == "breach":
            reasons.append(
                "Portfolio Engine Pro: contraintes violées (concentration ou poids max)"
            )
            global_flag = _merge_flag(global_flag, "danger")
        else:
            reasons.append("Portfolio Engine Pro: concentration et contraintes OK")
    else:
        overview["portfolio_engine_pro"] = None

    # ---------- 4) Clôture ----------
    overview["global_flag"] = global_flag
    overview["reasons"] = reasons
    return overview


def main() -> None:
    logger.info(
        "[risk_console_light] ROOT_DIR=%s, DATA_DIR=%s",
        str(ROOT_DIR),
        str(DATA_DIR),
    )
    overview = compute_risk_console(DATA_DIR)

    analysis_dir = DATA_DIR / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    output_path = analysis_dir / "risk_console_overview.json"

    save_json_file(output_path, overview)
    logger.info(
        "[risk_console_light] Risk console sauvegardée dans %s (global_flag=%s).",
        str(output_path),
        overview.get("global_flag"),
    )


if __name__ == "__main__":
    main()
