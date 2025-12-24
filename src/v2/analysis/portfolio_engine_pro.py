# src/v2/analysis/portfolio_engine_pro.py

import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def get_data_dir() -> str:
    """
    Version locale de get_data_dir pour éviter la dépendance à src.v2.utils.env.

    Priorité :
    1) NSC_DATA_DIR
    2) NSC_ROOT_DIR + '/data'
    3) ./data (répertoire courant)
    """
    env_dir = os.getenv("NSC_DATA_DIR")
    if env_dir:
        return env_dir

    root_dir = os.getenv("NSC_ROOT_DIR")
    if root_dir:
        return os.path.join(root_dir, "data")

    return os.path.join(os.getcwd(), "data")


def _load_sized_signals(data_dir: str) -> List[Dict[str, Any]]:
    """
    Charge les signaux sizés depuis trading/sized_signals.json.
    Retourne une liste vide si le fichier n'existe pas.
    """
    path = os.path.join(data_dir, "trading", "sized_signals.json")
    signals = load_json_file(path, default=[])
    if isinstance(signals, dict):
        # Cas de format dict → on prend une clé standard si elle existe
        signals = signals.get("signals", [])
    logger.info("[portfolio_engine_pro] sized_signals chargés: n=%d", len(signals))
    return signals


def _load_open_positions(data_dir: str) -> List[Dict[str, Any]]:
    """
    Charge les positions ouvertes depuis trading/open_positions.json.
    Retourne une liste vide si le fichier n'existe pas.
    """
    path = os.path.join(data_dir, "trading", "open_positions.json")
    positions = load_json_file(path, default=[])
    if isinstance(positions, dict):
        positions = positions.get("positions", [])
    logger.info("[portfolio_engine_pro] open_positions chargées: n=%d", len(positions))
    return positions


def _load_capital_allocation(data_dir: str) -> Dict[str, Any]:
    """
    Charge l'allocation de capital depuis trading/capital_allocation.json.
    Retourne un dict avec des valeurs par défaut si le fichier n'existe pas.
    """
    path = os.path.join(data_dir, "trading", "capital_allocation.json")
    alloc = load_json_file(
        path,
        default={
            "total_capital": 1000.0,
            "trading_capital": 450.0,
            "capital_per_trade": 9.0,
            "max_positions": 50,
        },
    )
    logger.info(
        "[portfolio_engine_pro] capital_allocation chargé: total=%.2f, trading=%.2f, max_positions=%s",
        float(alloc.get("total_capital", 0.0) or 0.0),
        float(alloc.get("trading_capital", 0.0) or 0.0),
        alloc.get("max_positions"),
    )
    return alloc


def _load_risk_limits(data_dir: str) -> Dict[str, Any]:
    """
    Charge les limites de risque globales depuis trading/risk_limits.json.
    Si absent, renvoie un profil 'normal' par défaut.
    """
    path = os.path.join(data_dir, "trading", "risk_limits.json")
    default = {
        "updated_at": None,
        "risk_mode": "normal",
        "risk_on_off": "on",
        "risk_on": True,
        "size_factor": 1.0,
        "trailing_atr_mult": 2.0,
        "max_daily_drawdown_pct_soft": 0.05,
        "max_daily_drawdown_pct_hard": 0.10,
        "daily_drawdown_pct": 0.0,
        "market_regime": "neutral",
        "market_microstructure_regime": "normal",
        "market_orderflow_regime": "normal",
        "risk_console_flag": "ok",
        "kill_switch": {
            "mode": "soft",
            "enabled": False,
            "hard_block": False,
            "soft_block": False,
        },
        "reasons": [],
    }
    rl = load_json_file(path, default=default)
    logger.info(
        "[portfolio_engine_pro] risk_limits chargés: mode=%s, risk_on_off=%s, size_factor=%.2f",
        rl.get("risk_mode"),
        rl.get("risk_on_off"),
        float(rl.get("size_factor", 1.0) or 1.0),
    )
    return rl


def _extract_weight(signal: Dict[str, Any]) -> float:
    """
    Extrait le poids cible d'un signal, en essayant plusieurs clés possibles.
    """
    for key in ("final_weight", "target_weight", "requested_weight", "weight"):
        if key in signal and signal[key] is not None:
            try:
                return float(signal[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def _build_symbol_view(
    sized_signals: List[Dict[str, Any]],
    open_positions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float, float, float]:
    """
    Construit une vue par symbole avec :
    - target_weight (dérivé des sized_signals)
    - current_weight (si présent dans open_positions)
    - delta_weight
    Retourne aussi :
    - gross_target_weight
    - max_single_weight
    - nb_symbols
    """
    # current_weight par symbole (si disponible)
    current_by_symbol: Dict[str, float] = {}
    for pos in open_positions:
        sym = (pos.get("symbol") or "").lower()
        if not sym:
            continue
        # On récupère un poids si dispo, sinon 0.0
        w = 0.0
        for key in ("weight", "target_weight", "portfolio_weight"):
            if key in pos and pos[key] is not None:
                try:
                    w = float(pos[key])
                except (TypeError, ValueError):
                    w = 0.0
                break
        current_by_symbol[sym] = current_by_symbol.get(sym, 0.0) + w

    # target_weight par symbole (depuis sized_signals)
    target_by_symbol: Dict[str, float] = {}
    side_by_symbol: Dict[str, str] = {}
    strategy_by_symbol: Dict[str, str] = {}

    for sig in sized_signals:
        sym = (sig.get("symbol") or "").lower()
        if not sym:
            continue
        w = _extract_weight(sig)
        target_by_symbol[sym] = target_by_symbol.get(sym, 0.0) + w
        if "side" in sig:
            side_by_symbol[sym] = sig["side"]
        if "strategy" in sig:
            strategy_by_symbol[sym] = sig["strategy"]

    symbols_view: List[Dict[str, Any]] = []
    gross_target = 0.0
    max_single_weight = 0.0

    for sym, tw in target_by_symbol.items():
        cw = current_by_symbol.get(sym, 0.0)
        dw = tw - cw
        gross_target += abs(tw)
        max_single_weight = max(max_single_weight, abs(tw))

        symbols_view.append(
            {
                "symbol": sym,
                "side": side_by_symbol.get(sym),
                "strategy": strategy_by_symbol.get(sym),
                "target_weight": tw,
                "current_weight": cw,
                "delta_weight": dw,
                "gross_exposure": abs(tw),
            }
        )

    nb_symbols = len(symbols_view)
    return symbols_view, gross_target, max_single_weight, float(nb_symbols)


def _evaluate_constraints(
    symbols_view: List[Dict[str, Any]],
    gross_target_weight: float,
    max_single_weight: float,
    capital_allocation: Dict[str, Any],
    risk_limits: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Évalue les contraintes de portefeuille :
    - max gross exposure
    - max single symbol weight
    - max positions
    - kill switch global
    Retourne un dict avec :
    - constraints_status: ok/breach
    - global_flag: ok/caution/block
    - breaches: liste de raisons
    - constraints: détails des seuils
    """
    breaches: List[str] = []

    max_positions = int(capital_allocation.get("max_positions") or 50)
    max_gross_exposure = float(capital_allocation.get("max_gross_exposure", 1.0) or 1.0)
    max_single_weight_allowed = float(
        capital_allocation.get("max_single_weight", 0.25) or 0.25
    )

    nb_symbols = len(symbols_view)

    # 1) Kill switch global
    ks = risk_limits.get("kill_switch", {}) or {}
    ks_enabled = bool(ks.get("enabled", False))
    ks_hard_block = bool(ks.get("hard_block", False))
    ks_soft_block = bool(ks.get("soft_block", False))

    if ks_enabled and ks_hard_block:
        breaches.append("Kill-switch global HARD BLOCK actif.")
    elif ks_enabled and ks_soft_block:
        breaches.append("Kill-switch global SOFT BLOCK actif.")

    # 2) Max positions
    if nb_symbols > max_positions:
        breaches.append(
            f"Nombre de symboles {nb_symbols} > max_positions autorisées {max_positions}."
        )

    # 3) Gross exposure
    if gross_target_weight > max_gross_exposure + 1e-6:
        breaches.append(
            f"Exposition brute {gross_target_weight:.2f} > max_gross_exposure {max_gross_exposure:.2f}."
        )

    # 4) Poids par symbole
    if max_single_weight > max_single_weight_allowed + 1e-6:
        breaches.append(
            f"Poids max par symbole {max_single_weight:.2f} > max_single_weight autorisé {max_single_weight_allowed:.2f}."
        )

    # 5) Risk console flag
    risk_console_flag = (risk_limits.get("risk_console_flag") or "ok").lower()
    if risk_console_flag in ("caution", "warning"):
        breaches.append("Risk console en mode CAUTION / WARNING.")
    elif risk_console_flag in ("danger", "critical"):
        breaches.append("Risk console en mode DANGER / CRITICAL.")

    # Synthèse
    if ks_enabled and ks_hard_block:
        global_flag = "block"
        constraints_status = "breach"
    elif breaches:
        # si seulement soft_block ou flags de prudence → caution ou block soft
        if ks_enabled and ks_soft_block:
            global_flag = "block"
        else:
            global_flag = "caution"
        constraints_status = "breach"
    else:
        global_flag = "ok"
        constraints_status = "ok"

    constraints = {
        "max_positions": max_positions,
        "max_gross_exposure": max_gross_exposure,
        "max_single_weight": max_single_weight_allowed,
        "risk_console_flag": risk_console_flag,
        "kill_switch": ks,
    }

    return {
        "constraints_status": constraints_status,
        "global_flag": global_flag,
        "breaches": breaches,
        "constraints": constraints,
    }


def run_portfolio_engine_pro(data_dir: str) -> Dict[str, Any]:
    """
    Cœur du Portfolio Engine PRO :
    - Charge sized_signals, open_positions, capital_allocation, risk_limits
    - Construit la vue portefeuille
    - Évalue les contraintes
    - Sauvegarde portfolio_engine_pro.json
    """
    logger.info("[portfolio_engine_pro] DATA_DIR=%s", data_dir)

    sized_signals = _load_sized_signals(data_dir)
    open_positions = _load_open_positions(data_dir)
    capital_allocation = _load_capital_allocation(data_dir)
    risk_limits = _load_risk_limits(data_dir)

    symbols_view, gross_target, max_single_weight, nb_symbols = _build_symbol_view(
        sized_signals, open_positions
    )

    constraints_eval = _evaluate_constraints(
        symbols_view=symbols_view,
        gross_target_weight=gross_target,
        max_single_weight=max_single_weight,
        capital_allocation=capital_allocation,
        risk_limits=risk_limits,
    )

    env = os.getenv("NSC_ENV", "PREPROD")
    now = datetime.utcnow().isoformat() + "Z"

    result: Dict[str, Any] = {
        "timestamp": now,
        "env": env,
        "stats": {
            "nb_signals": len(sized_signals),
            "nb_open_positions": len(open_positions),
            "nb_symbols": nb_symbols,
            "gross_target_weight": gross_target,
            "max_single_weight": max_single_weight,
            "constraints_status": constraints_eval["constraints_status"],
            "global_flag": constraints_eval["global_flag"],
        },
        "constraints": constraints_eval["constraints"],
        "breaches": constraints_eval["breaches"],
        "symbols": symbols_view,
    }

    out_path = os.path.join(data_dir, "analysis", "portfolio_engine_pro.json")
    save_json_file(out_path, result)
    logger.info(
        "[portfolio_engine_pro] portfolio_engine_pro.json sauvegardé (%s, symbols=%d, status=%s).",
        out_path,
        int(nb_symbols),
        constraints_eval["constraints_status"],
    )

    return result


def main() -> None:
    data_dir = get_data_dir()
    run_portfolio_engine_pro(data_dir)


if __name__ == "__main__":
    main()
