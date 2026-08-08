# src/v2/trading/position_sizing_institutionnel.py


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _norm_sym(x: str) -> str:
    return str(x or "").strip().lower()

def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _load_candidates_meta_map(data_dir):
    """
    Lit data/analysis/signal_candidates.json
    Retourne {symbol: meta_score(float)} avec fallback final_score/score.
    """
    try:
        from src.v2.utils.file_utils import load_json_file
        arr = load_json_file(str(data_dir / "analysis" / "signal_candidates.json"), default=[]) or []
        if not isinstance(arr, list):
            return {}
        out = {}
        for it in arr:
            if not isinstance(it, dict):
                continue
            sym = _norm_sym(it.get("symbol") or it.get("asset"))
            if not sym:
                continue
            v = it.get("meta_score")
            if v is None:
                v = it.get("final_score")
            if v is None:
                v = it.get("score")
            try:
                if v is None:
                    continue
                out[sym] = float(v)
            except Exception:
                continue
        return out
    except Exception:
        return {}

def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _attach_meta_score_pro(sized_list, meta_map: dict):
    """
    Remplit meta_score_pro dans sized_signals à partir du meta_map si absent.
    """
    if not isinstance(sized_list, list) or not sized_list:
        return sized_list, 0
    if not isinstance(meta_map, dict) or not meta_map:
        return sized_list, 0

    n = 0
    for it in sized_list:
        if not isinstance(it, dict):
            continue
        sym = _norm_sym(it.get("symbol") or it.get("asset"))
        if not sym:
            continue
        if it.get("meta_score_pro") is None:
            v = meta_map.get(sym)
            if v is not None:
                it["meta_score_pro"] = float(v)
                it["meta_score_source"] = "signal_candidates"
                n += 1
    return sized_list, n



def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _nsc_pick_score(sig: dict) -> float:
    """Extract a ranking score from heterogeneous signal formats."""
    if not isinstance(sig, dict):
        return 0.0

    keys = (
        "meta_score", "final_score", "score",
        "meta_score_pro", "rank_score", "signal_score",
        "confidence", "quality_score"
    )

    for k in keys:
        v = sig.get(k)

        if v is None and isinstance(sig.get("scores"), dict):
            v = sig["scores"].get(k)
        if v is None and isinstance(sig.get("analysis"), dict):
            v = sig["analysis"].get(k)
        if v is None and isinstance(sig.get("context"), dict):
            v = sig["context"].get(k)

        if v is None:
            continue
        try:
            return float(v)
        except Exception:
            continue

    return 0.0
import os

# Si True, on exige un risk_engine_pro par symbole (comportement strict).
# - PROD: strict par défaut
# - PREPROD/DEV: fallback autorisé par défaut
# Override explicite possible via NSC_SIZING_REQUIRE_RISK=0/1
ENV_NAME = os.getenv("NSC_ENV", os.getenv("ENV", "PREPROD")).strip().upper()
_REQUIRE_RISK_RAW = os.getenv("NSC_SIZING_REQUIRE_RISK")
if _REQUIRE_RISK_RAW is None:
    STRICT_REQUIRE_RISK = ENV_NAME in ("PROD", "PRODUCTION")
else:
    STRICT_REQUIRE_RISK = _REQUIRE_RISK_RAW.strip() == "1"
from pathlib import Path
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)

# Détection DATA_DIR (comme les autres modules "pro")
ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("NSC_DATA_DIR") or os.getenv("NSC_DATA_ROOT") or ROOT_DIR / "data")


# Majors : on évite de bloquer totalement un buy momentum juste parce que weak_signals est en "weak_avoid"
MAJORS = {"bitcoin", "ethereum", "solana", "bnb"}


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _build_index(items: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    """Indexe une liste de dicts par une clé (ex: symbol)."""
    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        k = it.get(key)
        if not k:
            continue
        out[str(k)] = it
    return out


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _load_signals(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge les signaux à dimensionner.
    On privilégie analysis/signal_candidates.json (signal_voting).
    """
    candidates_path = data_dir / "analysis" / "signal_candidates.json"
    signals = load_json_file(candidates_path, default=[])
    if not isinstance(signals, list):
        logger.warning(
            "[position_sizing] signal_candidates.json n'est pas une liste, fallback []"
        )
        return []
    if not signals:
        logger.info("[position_sizing] Aucun signal trouvé dans %s", candidates_path)
    else:
        logger.info(
            "[position_sizing] %d signaux chargés depuis %s",
            len(signals),
            candidates_path,
        )
    return signals


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _load_risk_engine(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Charge le résultat de risk_engine_pro.json et indexe par symbol."""
    risk_path = data_dir / "analysis" / "risk_engine_pro.json"
    risk_data = load_json_file(
        risk_path,
        default={"assets": []},
    )
    assets = risk_data.get("assets", [])
    if not isinstance(assets, list):
        logger.warning(
            "[position_sizing] risk_engine_pro.json ne contient pas une liste 'assets'"
        )
        return {}
    logger.info(
        "[position_sizing] Risk engine chargé: %d assets (global_flag=%s)",
        len(assets),
        risk_data.get("global_flag"),
    )
    return _build_index(assets, "symbol")


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _load_weak_signals(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Charge weak_signals_engine_pro.json (si dispo) et indexe par symbol.
    """
    weak_path = data_dir / "analysis" / "weak_signals_engine_pro.json"
    weak_data = load_json_file(
        weak_path,
        default={"assets": []},
    )
    assets = weak_data.get("assets", [])
    if not isinstance(assets, list):
        logger.warning(
            "[position_sizing] weak_signals_engine_pro.json ne contient pas une liste 'assets'"
        )
        return {}
    logger.info(
        "[position_sizing] Weak signals pro chargé: %d assets (global_flag=%s)",
        len(assets),
        weak_data.get("stats", {}).get("global_flag"),
    )
    return _build_index(assets, "symbol")


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def _compute_size_multiplier(
    risk_item: Dict[str, Any],
    weak_item: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Calcule le multiplicateur de taille final en combinant :
    - risk_engine_pro (risk_flag, size_multiplier)
    - weak_signals_engine_pro (weak_watch / weak_avoid)
    """
    risk_flag = risk_item.get("risk_flag", "caution")
    base_mult = float(risk_item.get("size_multiplier", 1.0))
    hard_veto = bool(risk_item.get("flags", {}).get("hard_veto", False))
    soft_veto = bool(risk_item.get("flags", {}).get("soft_veto", False))

    weak_kind = None
    notes: List[str] = []
    if weak_item:
        weak_kind = weak_item.get("kind")

    # Majors override : weak_avoid ne bloque pas (réduit seulement)
    majors = {"bitcoin", "ethereum", "solana"}
    symbol = str(risk_item.get("symbol") or risk_item.get("inputs", {}).get("symbol") or "").strip()
    if symbol in majors and weak_kind == "weak_avoid":
        notes.append("Majors override: weak_avoid -> weak_watch (no hard block)")
        weak_kind = "weak_watch"


    # Soft risk flags: caution → réduction douce
    if str(risk_flag).lower() in ("caution", "warn", "warning"):
        notes.append("risk_flag=caution -> reduce")
        base_mult = min(base_mult, 0.5)
        soft_veto = True

    # 1) Hard veto risk engine → taille 0
    if hard_veto:
        notes.append("Hard veto (risk engine)")
        return {
            "final_mult": 0.0,
            "hard_veto": True,
            "soft_veto": True,
            "weak_kind": weak_kind,
            "notes": notes,
        }

    # 2) Base sur risk_engine_pro
    final_mult = base_mult
    notes.append(f"Risk flag={risk_flag}, base_mult={base_mult:.2f}")

    if soft_veto:
        notes.append("Soft veto (risk engine)")

    # 3) Weak signals pro
    if weak_kind == "weak_avoid":
        # Institutionnellement, on coupe la taille
        notes.append("weak_avoid → taille coupée")
        final_mult = 0.0
        soft_veto = True
    elif weak_kind == "weak_watch":
        # On réduit la taille mais on ne coupe pas totalement.
        # Majors: réduction plus douce (on garde de l'exposition)
        sym = str(risk_item.get("symbol") or risk_item.get("inputs", {}).get("symbol") or "").strip().lower()
        if sym in {"bitcoin", "ethereum", "solana"}:
            notes.append("weak_watch (major) → réduction douce (×0.8)")
            final_mult *= 0.8
        else:
            notes.append("weak_watch → taille réduite (×0.5)")
            final_mult *= 0.5

    # Clamp raisonnable
    final_mult = max(0.0, min(final_mult, 1.5))

    return {
        "final_mult": final_mult,
        "hard_veto": hard_veto,
        "soft_veto": soft_veto,
        "weak_kind": weak_kind,
        "notes": notes,
    }


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned
def build_sized_signals() -> list[dict[str, Any]]:
    """
    Construit la liste des signaux dimensionnés (sized_signals.json) à partir de :
    - signal_candidates.json (signaux bruts)
    - risk_engine_pro.json (risk_score, size_multiplier, flags)
    - weak_signals_engine_pro.json (weak_watch / weak_avoid)
    """
    data_dir = DATA_DIR
    capital = load_json_file(data_dir / "trading" / "capital_allocation.json", default={}) or {}
    capital_per_trade = float(capital.get("capital_per_trade") or 0.0)

    risk_limits = load_json_file(data_dir / "trading" / "risk_limits.json", default={}) or {}
    strategy_intensity = risk_limits.get("strategy_intensity_factors", {}) or {}
    strategy_vetos = risk_limits.get("strategy_vetos", {}) or {}
    strategy_boosts = risk_limits.get("strategy_boosts", {}) or {}

    strategy_selector = load_json_file(data_dir / "analysis" / "strategy_weights.json", default={}) or {}
    strategy_weights_v5 = strategy_selector.get("weights", {}) if isinstance(strategy_selector, dict) else {}

    logger.info("[position_sizing] DATA_DIR=%s", data_dir)


    signals = _load_signals(data_dir)
    if not signals:
        logger.warning("[position_sizing] Aucun signal à dimensionner.")
        return []

    risk_index = _load_risk_engine(data_dir)
    weak_index = _load_weak_signals(data_dir)

    sized: List[Dict[str, Any]] = []

    for sig in signals:
        _sym = str(sig.get("symbol") or "")
        symbol = str(sig.get("symbol") or sig.get("asset") or "").lower()
        if not symbol:
            logger.warning("[position_sizing] Signal sans 'symbol': %s", sig)
            continue

        # Charger weak_signals AVANT risk fallback (utile pour choisir risk_flag fallback)
        weak_item = weak_index.get(symbol)

        risk_item = risk_index.get(symbol)
        if not risk_item:
            if STRICT_REQUIRE_RISK:
                logger.warning("[position_sizing] Aucun risk_engine_pro pour %s, skip.", symbol)
                continue

            # Fallback neutre (préprod): autoriser le sizing même sans risk_engine_pro
            fallback_flag = "caution"
            if weak_item and isinstance(weak_item, dict):
                fallback_flag = weak_item.get("risk_flag") or fallback_flag

            risk_item = {
                "symbol": symbol,
                "risk_flag": fallback_flag,
                "risk_score": None,
                "size_multiplier": 1.0,
                "flags": {"hard_veto": False, "soft_veto": False},
                "inputs": {"fallback_risk_engine_missing": True},
            }
            logger.info(
                "[position_sizing] fallback_risk_engine_missing=%s -> sizing autorisé (risk_flag=%s)",
                symbol,
                risk_item.get("risk_flag"),
            )
        if weak_item and weak_item.get("kind") == "weak_avoid" and symbol in MAJORS:
            logger.info("[position_sizing] Majors override: weak_avoid -> weak_watch (symbol=%s)", symbol)
            weak_item = dict(weak_item)
            weak_item["kind"] = "weak_watch"
        mult_info = _compute_size_multiplier(risk_item, weak_item)

        base_weight = float(sig.get("weight", 1.0))

        strategy_key = str(sig.get("strategy", "momentum") or "momentum").lower()
        try:
            strategy_factor = float(strategy_intensity.get(strategy_key, 1.0) or 1.0)
        except Exception:
            strategy_factor = 1.0

        veto_reason = strategy_vetos.get(strategy_key)
        boost_reason = strategy_boosts.get(strategy_key)

        if veto_reason:
            strategy_factor = 0.0

        selector_weight = strategy_weights_v5.get(strategy_key, 1.0)
        try:
            selector_weight = float(selector_weight or 1.0)
        except Exception:
            selector_weight = 1.0

        # V5 SAFE:
        # - risk engine reste dominant
        # - strategy intensity module 30%
        # - selector module seulement entre 0.75 et 1.05 pour éviter l'overfit.
        selector_weight_safe = max(0.75, min(1.05, selector_weight))

        strategy_modulator = 0.70 + (0.30 * strategy_factor)
        final_weight = base_weight * mult_info["final_mult"] * strategy_modulator * selector_weight_safe

        if final_weight <= 0:
            logger.info("[position_sizing] strategy veto/zero weight symbol=%s strategy=%s reason=%s", symbol, strategy_key, veto_reason or "final_weight<=0")
            continue

        sized_signal = {
            "symbol": symbol,
            "side": sig.get("side", "buy"),
            "strategy": sig.get("strategy", "momentum"),
            "base_weight": base_weight,
            "requested_weight": base_weight,
            "weight": final_weight,
            "meta_score": (sig.get("meta_score") if sig.get("meta_score") is not None else _nsc_pick_score(sig)),
            "market_momentum": sig.get("market_momentum"),
            "chg_24h": sig.get("chg_24h"),
            "pair": sig.get("pair"),
            "source": sig.get("source"),
            "momentum_regime": sig.get("momentum_regime"),
            "reason": sig.get("reason"),
            "final_score": sig.get("final_score"),
            "score": sig.get("score"),
            "risk_score": risk_item.get("risk_score"),
            "risk_flag": risk_item.get("risk_flag"),
            "size_multiplier_risk": risk_item.get("size_multiplier", 1.0),
            "strategy_intensity_factor": strategy_factor,
            "strategy_modulator_v4": strategy_modulator,
            "strategy_selector_weight_v5": selector_weight_safe,
            "strategy_intensity_source": "risk_limits.strategy_intensity_factors",
            "strategy_veto": veto_reason,
            "strategy_boost": boost_reason,
            "weak_kind": mult_info["weak_kind"],
            "hard_veto": mult_info["hard_veto"],
            "soft_veto": mult_info["soft_veto"],
            "final_size_multiplier": mult_info["final_mult"],
            "final_weight": final_weight,
            "capital_per_trade_eur": round(capital_per_trade, 2) if capital_per_trade else None,
            "target_notional_eur": round(capital_per_trade * final_weight, 2) if (capital_per_trade and final_weight) else None,
            "notional_eur": round(capital_per_trade * final_weight, 2) if (capital_per_trade and final_weight) else None,
            # Pour debug / transparence
            "meta_score_pro": risk_item.get("inputs", {}).get("meta_score_pro")
            or risk_item.get("meta_score_pro"),
            "flow_direction": risk_item.get("inputs", {}).get("flow_direction"),
            "notes": (
                mult_info["notes"]
                + [f"Strategy intensity factor={strategy_factor:.2f}"]
                + [f"Strategy modulator V4={strategy_modulator:.2f}"]
                + [f"Strategy selector V5={selector_weight_safe:.2f}"]
                + ([f"Strategy boost: {boost_reason}"] if boost_reason else [])
                + ([f"Strategy veto: {veto_reason}"] if veto_reason else [])
            ),
        }

        sized.append(sized_signal)

    logger.info(
        "[position_sizing] %d signaux dimensionnés construits (sur %d signaux bruts).",
        len(sized),
        len(signals),
    )

    # -------------------------------------------------------------------
    # NSC_SORT_SIZED_SIGNALS_BUILD
    # Keep best first for downstream caps
    # -------------------------------------------------------------------
    try:
        if isinstance(sized, list) and sized:
            sized.sort(
                key=lambda s: (
                    float(s.get("meta_score") or s.get("meta_score_pro") or s.get("final_score") or s.get("score") or 0.0),
                    float(s.get("weight") or s.get("final_weight") or 0.0),
                ),
                reverse=True,
            )
    except Exception:
        logger.exception("[position_sizing] Failed to sort sized_signals in build (ignored)")
    return sized


def _cap_and_renormalize_weights(signals, max_gross=1.0, max_single=0.25):

    cleaned = []

    for s in (signals or []):

        if not isinstance(s, dict):

            continue

        w = float(s.get("weight") or 0.0)

        if w <= 0:

            continue

        s["weight"] = min(w, max_single)

        cleaned.append(s)

    if not cleaned:

        return []

    total = sum(float(x.get("weight") or 0.0) for x in cleaned)

    if total > max_gross and total > 0:

        scale = max_gross / total

        for x in cleaned:

            x["weight"] = min(float(x.get("weight") or 0.0) * scale, max_single)

    return cleaned

def main() -> None:
    """Point d'entrée CLI."""
    data_dir = DATA_DIR
    capital = load_json_file(data_dir / "trading" / "capital_allocation.json", default={}) or {}
    capital_per_trade = float(capital.get("capital_per_trade") or 0.0)

    trading_dir = data_dir / "trading"
    trading_dir.mkdir(parents=True, exist_ok=True)

    sized = _cap_and_renormalize_weights(build_sized_signals())


    # --- Option A: attach meta_score_pro from analysis/signal_candidates.json ---

    try:

        _meta_map = _load_candidates_meta_map(data_dir)

        sized, _n = _attach_meta_score_pro(sized, _meta_map)

        logger.info("[position_sizing] meta_score_pro attached from signal_candidates: %d/%d", _n, len(sized) if isinstance(sized, list) else -1)

    except Exception:

        logger.exception("[position_sizing] attach meta_score_pro failed (ignored)")

    out_path = trading_dir / "sized_signals.json"
    try:
        # Toujours écraser sized_signals.json (même si vide) pour éviter les signaux stale

        # -------------------------------------------------------------------
        # NSC_SORT_SIZED_SIGNALS_MAIN
        # Safety: ensure persisted file is sorted
        # -------------------------------------------------------------------
        try:
            if isinstance(sized, list) and sized:
                sized.sort(
                    key=lambda s: (
                        float(s.get("meta_score") or s.get("meta_score_pro") or s.get("final_score") or s.get("score") or 0.0),
                        float(s.get("weight") or s.get("final_weight") or 0.0),
                    ),
                    reverse=True,
                )
        except Exception:
            logger.exception("[position_sizing] Failed to sort sized_signals in main (ignored)")
        save_json_file(str(out_path), sized)
    except Exception:
        logger.exception("[position_sizing] Échec save_json_file -> fallback write_text")
        import json as _json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(_json.dumps(sized, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "[position_sizing] sized_signals.json sauvegardé (%s, n=%d).",
        out_path,
        len(sized),
    )


if __name__ == "__main__":
    main()
