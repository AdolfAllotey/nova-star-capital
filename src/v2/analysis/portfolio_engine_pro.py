# src/v2/analysis/portfolio_engine_pro.py

import os
from datetime import datetime, UTC
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def get_data_dir() -> str:
    env_dir = os.getenv("NSC_DATA_DIR")
    if env_dir:
        return env_dir

    root_dir = os.getenv("NSC_ROOT_DIR")
    if root_dir:
        return os.path.join(root_dir, "data")

    return os.path.join(os.getcwd(), "data")


def _load_sized_signals(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, "trading", "sized_signals.json")
    signals = load_json_file(path, default=[])
    if isinstance(signals, dict):
        signals = signals.get("signals", [])
    logger.info("[portfolio_engine_pro] sized_signals chargés: n=%d", len(signals))
    return signals


def _load_open_positions(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, "trading", "open_positions.json")
    positions = load_json_file(path, default=[])
    if isinstance(positions, dict):
        positions = positions.get("positions", [])
    logger.info("[portfolio_engine_pro] open_positions chargées: n=%d", len(positions))
    return positions


def _load_capital_allocation(data_dir: str) -> Dict[str, Any]:
    path = os.path.join(data_dir, "trading", "capital_allocation.json")
    alloc = load_json_file(
        path,
        default={
            "total_capital": 1000.0,
            "trading_capital": 450.0,
            "capital_per_trade": 9.0,
            "max_positions": 50,
            "max_gross_exposure": 1.0,
            "max_single_weight": 0.25,
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


def _load_defensive_signal(data_dir: str) -> Dict[str, Any]:
    repo_root = os.getenv("NSC_ROOT_DIR", os.getcwd())

    candidate_paths = [
        os.path.join(data_dir, "defensive", "defensive_signal.json"),
        os.path.join(repo_root, "src", "v2", "data", "defensive", "defensive_signal.json"),
    ]

    for path in candidate_paths:
        signal = load_json_file(path, default={})
        if isinstance(signal, dict) and signal.get("brick") == "defensive_equities":
            logger.info(
                "[portfolio_engine_pro] defensive_signal chargé depuis %s | assets=%d | exposure=%.4f",
                path,
                len(signal.get("proposed_assets", []) or []),
                float(signal.get("target_exposure", 0.0) or 0.0),
            )
            signal["_loaded_from"] = path
            return signal

    logger.info("[portfolio_engine_pro] defensive_signal absent.")
    return {}


def _extract_weight(signal: Dict[str, Any]) -> float:
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
    defensive_signal: Dict[str, Any] | None = None,
) -> Tuple[List[Dict[str, Any]], float, float, float]:
    current_by_symbol: Dict[str, float] = {}
    for pos in open_positions:
        sym = (pos.get("symbol") or "").lower()
        if not sym:
            continue
        w = 0.0
        for key in ("weight", "target_weight", "portfolio_weight"):
            if key in pos and pos[key] is not None:
                try:
                    w = float(pos[key])
                except (TypeError, ValueError):
                    w = 0.0
                break
        current_by_symbol[sym] = current_by_symbol.get(sym, 0.0) + w

    target_by_symbol: Dict[str, float] = {}
    side_by_symbol: Dict[str, str] = {}
    strategy_by_symbol: Dict[str, str] = {}
    sleeve_by_symbol: Dict[str, str] = {}
    meta_by_symbol: Dict[str, Dict[str, Any]] = {}

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
        sleeve_by_symbol[sym] = "trading"
        meta_by_symbol.setdefault(sym, {})

    defensive_assets = []
    defensive_exposure = 0.0
    if isinstance(defensive_signal, dict):
        defensive_assets = defensive_signal.get("proposed_assets", []) or []
        defensive_exposure = float(defensive_signal.get("target_exposure", 0.0) or 0.0)

    for asset in defensive_assets:
        ticker = str(asset.get("ticker") or "").lower()
        if not ticker:
            continue

        internal_weight = float(asset.get("weight", 0.0) or 0.0)
        portfolio_weight = defensive_exposure * internal_weight

        target_by_symbol[ticker] = target_by_symbol.get(ticker, 0.0) + portfolio_weight
        side_by_symbol[ticker] = "buy"
        strategy_by_symbol[ticker] = "defensive_equities"
        sleeve_by_symbol[ticker] = "defensive_equities"
        meta_by_symbol[ticker] = {
            "type": asset.get("type"),
            "sector": asset.get("sector"),
            "region": asset.get("region"),
            "source_brick": "defensive_equities",
            "internal_weight": internal_weight,
            "brick_target_exposure": defensive_exposure,
        }

    symbols_view: List[Dict[str, Any]] = []
    gross_target = 0.0
    max_single_weight = 0.0

    for sym, tw in target_by_symbol.items():
        cw = current_by_symbol.get(sym, 0.0)
        dw = tw - cw
        gross_target += abs(tw)
        max_single_weight = max(max_single_weight, abs(tw))

        symbol_entry = {
            "symbol": sym,
            "side": side_by_symbol.get(sym),
            "strategy": strategy_by_symbol.get(sym),
            "sleeve": sleeve_by_symbol.get(sym, "unknown"),
            "target_weight": tw,
            "current_weight": cw,
            "delta_weight": dw,
            "gross_exposure": abs(tw),
        }
        symbol_entry.update(meta_by_symbol.get(sym, {}))
        symbols_view.append(symbol_entry)

    nb_symbols = len(symbols_view)
    return symbols_view, gross_target, max_single_weight, float(nb_symbols)


def _build_sleeve_stats(symbols_view: List[Dict[str, Any]]) -> Dict[str, Any]:
    sleeves: Dict[str, Dict[str, Any]] = {}

    for row in symbols_view:
        sleeve = str(row.get("sleeve", "unknown"))
        target_weight = float(row.get("target_weight", 0.0) or 0.0)
        gross_exposure = float(row.get("gross_exposure", 0.0) or 0.0)

        if sleeve not in sleeves:
            sleeves[sleeve] = {
                "symbols_count": 0,
                "gross_target_weight": 0.0,
                "net_target_weight": 0.0,
                "max_single_weight": 0.0,
                "symbols": [],
            }

        sleeves[sleeve]["symbols_count"] += 1
        sleeves[sleeve]["gross_target_weight"] += gross_exposure
        sleeves[sleeve]["net_target_weight"] += target_weight
        sleeves[sleeve]["max_single_weight"] = max(
            float(sleeves[sleeve]["max_single_weight"]),
            abs(target_weight),
        )
        sleeves[sleeve]["symbols"].append(row.get("symbol"))

    for sleeve_name, sleeve_data in sleeves.items():
        sleeve_data["gross_target_weight"] = round(float(sleeve_data["gross_target_weight"]), 6)
        sleeve_data["net_target_weight"] = round(float(sleeve_data["net_target_weight"]), 6)
        sleeve_data["max_single_weight"] = round(float(sleeve_data["max_single_weight"]), 6)
        sleeve_data["symbols"] = sorted(sleeve_data["symbols"])

    return sleeves


def _evaluate_portfolio_constraints(
    symbols_view: List[Dict[str, Any]],
    gross_target_weight: float,
    max_single_weight: float,
    capital_allocation: Dict[str, Any],
    risk_limits: Dict[str, Any],
) -> Dict[str, Any]:
    breaches: List[str] = []

    max_positions = int(capital_allocation.get("max_positions") or 50)
    max_gross_exposure = float(capital_allocation.get("max_gross_exposure", 1.0) or 1.0)
    max_single_weight_allowed = float(capital_allocation.get("max_single_weight", 0.25) or 0.25)

    nb_symbols = len(symbols_view)

    ks = risk_limits.get("kill_switch", {}) or {}
    ks_enabled = bool(ks.get("enabled", False))
    ks_hard_block = bool(ks.get("hard_block", False))
    ks_soft_block = bool(ks.get("soft_block", False))

    if ks_enabled and ks_hard_block:
        breaches.append("Kill-switch global HARD BLOCK actif.")
    elif ks_enabled and ks_soft_block:
        breaches.append("Kill-switch global SOFT BLOCK actif.")

    if nb_symbols > max_positions:
        breaches.append(f"Nombre de symboles {nb_symbols} > max_positions autorisées {max_positions}.")

    if gross_target_weight > max_gross_exposure + 1e-6:
        breaches.append(
            f"Exposition brute {gross_target_weight:.2f} > max_gross_exposure {max_gross_exposure:.2f}."
        )

    if max_single_weight > max_single_weight_allowed + 1e-6:
        breaches.append(
            f"Poids max par symbole {max_single_weight:.2f} > max_single_weight autorisé {max_single_weight_allowed:.2f}."
        )

    risk_console_flag = (risk_limits.get("risk_console_flag") or "ok").lower()
    if risk_console_flag in ("caution", "warning"):
        breaches.append("Risk console en mode CAUTION / WARNING.")
    elif risk_console_flag in ("danger", "critical"):
        breaches.append("Risk console en mode DANGER / CRITICAL.")

    if ks_enabled and ks_hard_block:
        global_flag = "block"
        constraints_status = "breach"
    elif breaches:
        global_flag = "block" if (ks_enabled and ks_soft_block) else "caution"
        constraints_status = "breach"
    else:
        global_flag = "ok"
        constraints_status = "ok"

    return {
        "status": constraints_status,
        "global_flag": global_flag,
        "breaches": breaches,
        "limits": {
            "max_positions": max_positions,
            "max_gross_exposure": max_gross_exposure,
            "max_single_weight": max_single_weight_allowed,
            "risk_console_flag": risk_console_flag,
            "kill_switch": ks,
        },
    }


def _evaluate_sleeve_constraints(sleeve_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contraintes V1.5 par sleeve.
    """
    sleeve_limits = {
        "trading": {
            "max_gross_exposure": 1.0,
            "max_single_weight": 0.25,
        },
        "defensive_equities": {
            "max_gross_exposure": 0.35,
            "max_single_weight": 0.05,
        },
    }

    results: Dict[str, Any] = {}

    for sleeve_name, stats in sleeve_stats.items():
        limits = sleeve_limits.get(
            sleeve_name,
            {"max_gross_exposure": 1.0, "max_single_weight": 0.25},
        )

        breaches: List[str] = []
        gross = float(stats.get("gross_target_weight", 0.0) or 0.0)
        max_single = float(stats.get("max_single_weight", 0.0) or 0.0)

        if gross > float(limits["max_gross_exposure"]) + 1e-6:
            breaches.append(
                f"Sleeve {sleeve_name}: gross_target_weight {gross:.4f} > limite {float(limits['max_gross_exposure']):.4f}."
            )

        if max_single > float(limits["max_single_weight"]) + 1e-6:
            breaches.append(
                f"Sleeve {sleeve_name}: max_single_weight {max_single:.4f} > limite {float(limits['max_single_weight']):.4f}."
            )

        results[sleeve_name] = {
            "status": "breach" if breaches else "ok",
            "breaches": breaches,
            "limits": limits,
            "observed": {
                "symbols_count": stats.get("symbols_count", 0),
                "gross_target_weight": gross,
                "net_target_weight": float(stats.get("net_target_weight", 0.0) or 0.0),
                "max_single_weight": max_single,
            },
        }

    return results


def run_portfolio_engine_pro(data_dir: str) -> Dict[str, Any]:
    logger.info("[portfolio_engine_pro] DATA_DIR=%s", data_dir)

    sized_signals = _load_sized_signals(data_dir)
    open_positions = _load_open_positions(data_dir)
    capital_allocation = _load_capital_allocation(data_dir)
    risk_limits = _load_risk_limits(data_dir)
    defensive_signal = _load_defensive_signal(data_dir)

    symbols_view, gross_target, max_single_weight, nb_symbols = _build_symbol_view(
        sized_signals=sized_signals,
        open_positions=open_positions,
        defensive_signal=defensive_signal,
    )

    sleeve_stats = _build_sleeve_stats(symbols_view)
    portfolio_constraints = _evaluate_portfolio_constraints(
        symbols_view=symbols_view,
        gross_target_weight=gross_target,
        max_single_weight=max_single_weight,
        capital_allocation=capital_allocation,
        risk_limits=risk_limits,
    )
    sleeve_constraints = _evaluate_sleeve_constraints(sleeve_stats)

    env = os.getenv("NSC_ENV", "PREPROD")
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    defensive_assets = defensive_signal.get("proposed_assets", []) if isinstance(defensive_signal, dict) else []
    defensive_target_exposure = float(defensive_signal.get("target_exposure", 0.0) or 0.0) if isinstance(defensive_signal, dict) else 0.0

    result: Dict[str, Any] = {
        "timestamp": now,
        "env": env,
        "stats": {
            "nb_signals": len(sized_signals),
            "nb_open_positions": len(open_positions),
            "nb_symbols": nb_symbols,
            "gross_target_weight": gross_target,
            "max_single_weight": max_single_weight,
            "constraints_status": portfolio_constraints["status"],
            "global_flag": portfolio_constraints["global_flag"],
            "defensive_assets_count": len(defensive_assets),
            "defensive_target_exposure": defensive_target_exposure,
        },
        "portfolio_constraints": portfolio_constraints,
        "sleeve_constraints": sleeve_constraints,
        "constraints": portfolio_constraints["limits"],
        "breaches": portfolio_constraints["breaches"],
        "sleeves": {
            "trading_signals_loaded": len(sized_signals),
            "defensive_equities_loaded": bool(defensive_assets),
            "defensive_signal_source": defensive_signal.get("_loaded_from") if isinstance(defensive_signal, dict) else None,
            "stats": sleeve_stats,
        },
        "symbols": symbols_view,
    }

    out_path = os.path.join(data_dir, "analysis", "portfolio_engine_pro.json")
    save_json_file(out_path, result)
    logger.info(
        "[portfolio_engine_pro] portfolio_engine_pro.json sauvegardé (%s, symbols=%d, status=%s).",
        out_path,
        int(nb_symbols),
        portfolio_constraints["status"],
    )

    return result


def main() -> None:
    data_dir = get_data_dir()
    run_portfolio_engine_pro(data_dir)


if __name__ == "__main__":
    main()
