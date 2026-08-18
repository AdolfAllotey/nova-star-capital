# src/v2/trading/position_manager.py

from __future__ import annotations

import os
from pathlib import Path
from collections import Counter

def _is_hard_block(data_dir, plan):
    """
    Source unique: HARD BLOCK uniquement si hard_block==True (jamais sur soft_veto/caution).
    Priorité:
      1) execution_plan.json -> plan["governance"]["hard_block"]
      2) kill_switch.json    -> KillSwitchState.hard_block (ou dict["hard_block"])
    """
    reasons = []

    # 1) execution_plan.json governance.hard_block
    try:
        if isinstance(plan, dict):
            gov = plan.get("governance") or {}
            if isinstance(gov, dict) and bool(gov.get("hard_block", False)):
                reasons.append("execution_plan.governance.hard_block=true")
                return True, reasons
    except Exception:
        pass

    # 2) kill_switch.json hard_block
    try:
        ks_file = load_kill_switch(str(_path(data_dir, "trading", "kill_switch.json")))
        # support dataclass-like + dict
        hb = getattr(ks_file, "hard_block", None)
        if hb is None and isinstance(ks_file, dict):
            hb = ks_file.get("hard_block", False)
        if bool(hb):
            reasons.append("kill_switch.hard_block=true")
            return True, reasons
    except Exception:
        pass

    return False, reasons

def is_dry_run_enabled() -> bool:
    v = (os.getenv("NSC_DRY_RUN") or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional

from src.v2.utils.file_utils import get_data_dir, load_json_file, save_json_file, load_effective_execution_plan
from src.v2.utils.ohlcv_utils import ohlcv_v2_to_legacy_rows
from src.v2.utils.logger import get_logger

logger = get_logger("position_manager")

from src.v2.governance.kill_switch import load_kill_switch

def _load_hf_policy(data_dir: str):
    """
    Lit data/analysis/risk_engine_pro.json et renvoie policy dict.
    Fallback neutre si absent/invalide.
    """
    try:
        from pathlib import Path
        from src.v2.utils.file_utils import load_json_file
        path = str(Path(data_dir) / "analysis" / "risk_engine_pro.json")
        raw = load_json_file(path, default={}) or {}
        if not isinstance(raw, dict):
            return {"position_size_mult": 1.0, "max_open_positions": None, "min_meta_score": None}

        pol = raw.get("policy") or {}
        if not isinstance(pol, dict):
            pol = {}

        def _f(x, d):
            try:
                return float(x)
            except Exception:
                return d

        def _i(x):
            try:
                return int(x)
            except Exception:
                return None

        mpos = pol.get("max_open_positions")
        mpos = _i(mpos) if mpos is not None else None

        mmeta = pol.get("min_meta_score")
        mmeta = _f(mmeta, None) if mmeta is not None else None

        return {
            "position_size_mult": _f(pol.get("position_size_mult"), 1.0),
            "max_open_positions": mpos,
            "min_meta_score": mmeta,
        }
    except Exception:
        # neutre
        # neutre
        return {"position_size_mult": 1.0, "max_open_positions": None, "min_meta_score": None}

def _nsc_ohlcv_v2_to_legacy_rows(raw, max_points: int = 260):
    """
    Convertit ohlcv_combined.json v2:
      {timestamp, env, assets:[{symbol, candles:[{open,high,low,close,volume,ts}, ...]}]}
    -> format legacy:
      { "BTCUSDT":[{"open":..,"high":..,"low":..,"close":..,"volume":..,"ts":..}, ...], ... }
    """
    if not isinstance(raw, dict):
        return raw

    assets = raw.get("assets")
    if not isinstance(assets, list):
        return raw

    def _f(x):
        try:
            return float(x)
        except Exception:
            return None

    def _i(x):
        try:
            return int(x)
        except Exception:
            return None

    out = {}
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        candles = a.get("candles")
        if not isinstance(sym, str) or not sym.strip() or not isinstance(candles, list):
            continue

        rows = []
        for c in candles[-max_points:]:
            if not isinstance(c, dict):
                continue

            row = {
                "ts": _i(c.get("ts")) or _i(c.get("t")),
                "open": _f(c.get("open") if c.get("open") is not None else c.get("o")),
                "high": _f(c.get("high") if c.get("high") is not None else c.get("h")),
                "low":  _f(c.get("low")  if c.get("low")  is not None else c.get("l")),
                "close": _f(c.get("close") if c.get("close") is not None else c.get("c")),
                "volume": _f(c.get("volume") if c.get("volume") is not None else c.get("v")),
                "source": c.get("source"),
            }

            # garde seulement si close exploitable
            if isinstance(row["close"], float) and row["close"] > 0:
                rows.append(row)

        if rows:
            out[sym.strip().upper()] = rows

    # Si on a réussi à convertir, on renvoie le legacy dict, sinon raw inchangé
    return out if out else raw

    def _f(x):
        try:
            return float(x)
        except Exception:
            return None

    out = {}
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        candles = a.get("candles")
        if not isinstance(sym, str) or not isinstance(candles, list):
            continue

        rows = []
        for c in candles[-max_points:]:
            if not isinstance(c, dict):
                continue
            close = _f(c.get("close") if c.get("close") is not None else c.get("c"))
            if close is None or close <= 0:
                continue
            rows.append({"ts": c.get("ts"), "close": close})

        if len(rows) >= 6:
            out[sym] = rows

    return out if out else raw

# --- Execution plan gate (institutional) ---
def _load_execution_plan(data_dir: str):
    try:
        from pathlib import Path
        from src.v2.utils.file_utils import load_json_file
        p = Path(data_dir) / "trading" / "execution_plan.json"
        obj = load_json_file(str(p), default={})
        return obj if isinstance(obj, dict) else {}
    except Exception:
        logger.exception("[position_manager] Impossible de charger execution_plan.json")
        return {}

def _is_final_safe_plan(plan: dict) -> tuple[bool, str]:
    # Must be written by execution_engine_pro with governance block
    if not isinstance(plan, dict) or not plan:
        return False, "plan_missing"
    # NSC_AUTOCLEARED_BYPASS_WRITER_GATE_V4_MOVED
    # If trading_kernel wrote an autocleared stub, treat it as a normal empty plan (not a gate error).
    try:
        _st0 = str((plan or {}).get('status') or '')
        _note0 = str((plan or {}).get('note') or '')
    except Exception:
        _st0, _note0 = '', ''
    if _st0 == 'cleared' or _note0.startswith('autocleared_') or _note0 == 'autocleared_blocked_plan':
        return False, 'empty'

    # HARD BLOCK (single source of truth + defensive fallbacks)
    try:
        ks_plan = plan.get("kill_switch")
        if isinstance(ks_plan, dict) and bool(ks_plan.get("hard_block", False)):
            return False, "hard_block_true"
        rs = plan.get("reasons") or []
        if isinstance(rs, list) and any(str(r) == "kill_switch:hard_block" for r in rs):
            return False, "hard_block_true"
    except Exception:
        pass

    try:
        ks_file = load_kill_switch()
        if bool(getattr(ks_file, "hard_block", False)):
            return False, "hard_block_true"
    except Exception:
        pass

    # writer gate (robuste): accepte plan["writer"] OU governance["writer"]
    _w_plan = (plan or {}).get("writer")
    _w_gov = None
    try:
        _w_gov = ((plan or {}).get("governance") or {}).get("writer")
    except Exception:
        _w_gov = None
    _writer = _w_plan or _w_gov

    if _writer != "execution_engine_pro":
        _dry = str(__import__("os").environ.get("NSC_DRY_RUN","0")).strip().lower() in ("1","true","yes")
        if _dry:
            return True, "dry_run_bypass_writer_gate"
        return False, "writer_not_execution_engine_pro"
    status = str(plan.get("status") or "").strip().lower()
    # En préprod, on accepte les plans "soft_veto_*" pour simuler la gestion des positions.
    allowed_status = {"ok", "soft_veto_caution", "soft_veto_risk_off", 'ready' }
    if status not in allowed_status:
        return False, "status_not_allowed"
    gov = plan.get("governance")
    if not isinstance(gov, dict) or gov.get("source") != "execution_engine_pro":
        return False, "governance_missing_or_wrong_source"
    if gov.get("hard_block") is True:
        return False, "hard_block_true"
    if not plan.get("run_id"):
        return False, "run_id_missing"
    gov_run_id = gov.get("run_id")
    if gov_run_id is None or str(gov_run_id) != str(plan.get("run_id")):
        return False, "governance_run_id_mismatch"
    gov_gen = gov.get("generated_at")
    if gov_gen is None or str(gov_gen) != str(plan.get("generated_at")):
        return False, "governance_generated_at_mismatch"
    return True, "ok"

def _pm_state_path(data_dir: str) -> str:
    from pathlib import Path
    return str(Path(data_dir) / "trading" / "position_manager_state.json")

def _load_pm_state(data_dir: str) -> dict:
    try:
        from src.v2.utils.file_utils import load_json_file
        return load_json_file(_pm_state_path(data_dir), default={}) or {}
    except Exception:
        logger.exception("[position_manager] Impossible de charger position_manager_state.json")
        return {}

def _save_pm_state(data_dir: str, obj: dict) -> None:
    try:
        from src.v2.utils.file_utils import save_json_file
        save_json_file(_pm_state_path(data_dir), obj)
    except Exception:
        logger.exception("[position_manager] Impossible de sauvegarder position_manager_state.json")

    try:
        from src.v2.utils.file_utils import save_json_file
        save_json_file(_pm_state_path(data_dir), obj)
    except Exception:
        logger.exception("[position_manager] Impossible de sauvegarder position_manager_state.json")
# ============================================================================
# Helpers OHLCV / ATR
# ============================================================================

def _compute_atr_from_bars(
    bars: List[Dict[str, Any]],
    period: int = 14,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcule un ATR simple à partir d'une liste de barres OHLC.
    Retourne (last_close, atr).
    """
    if not isinstance(bars, list) or len(bars) < 2:
        return None, None

    cleaned = []
    for b in bars:
        if not isinstance(b, dict):
            continue
        try:
            high = float(b.get("high"))
            low = float(b.get("low"))
            close = float(b.get("close"))
        except Exception:
            continue
        if high <= 0 or low <= 0 or close <= 0:
            continue
        cleaned.append({"high": high, "low": low, "close": close})

    if len(cleaned) < 2:
        return None, None

    last_close = cleaned[-1]["close"]

    true_ranges = []
    prev_close = cleaned[0]["close"]

    for i, bar in enumerate(cleaned):
        high = bar["high"]
        low = bar["low"]
        close = bar["close"]

        if i == 0:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
        true_ranges.append(tr)
        prev_close = close

    if not true_ranges:
        return last_close, None

    n = min(period, len(true_ranges))
    if n <= 0:
        return last_close, None

    atr = sum(true_ranges[-n:]) / float(n)
    return last_close, atr

def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def _apply_hf_policy(items, policy, logger, context="items"):
    """
    HF enforcement:
      - min_meta_score: drop low quality (sur meta_score/meta_score_pro/score/final_score)
      - max_open_positions: keep top-N (by score)
      - position_size_mult: scale sizing fields (notional_eur/target_notional_eur/capital_per_trade_eur/size/amount)
    """
    if not isinstance(items, list) or not items:
        return items
    if not isinstance(policy, dict):
        return items

    def _score(d):
        if not isinstance(d, dict):
            return None
        # IMPORTANT: sized_signals utilise meta_score_pro
        for k in ("meta_score", "meta_score_pro", "final_score", "score", "risk_score"):
            v = d.get(k)
            try:
                if v is None:
                    continue
                return float(v)
            except Exception:
                continue
        return None

    def _scale_field(d, k, mult):
        try:
            if k in d and d[k] is not None:
                d[k] = float(d[k]) * float(mult)
        except Exception:
            pass

    min_meta = policy.get("min_meta_score", None)
    max_pos  = policy.get("max_open_positions", None)
    mult     = policy.get("position_size_mult", 1.0)

    # Normalize
    try:
        mult = float(mult)
    except Exception:
        mult = 1.0

    # 1) Filter by min_meta_score ONLY if score exists
    kept = items
    if min_meta is not None:
        try:
            min_meta_f = float(min_meta)
        except Exception:
            min_meta_f = None
        if min_meta_f is not None:
            scored = [(it, _score(it)) for it in items]
            # keep items with score >= threshold; if score missing => keep (do not punish unknown)
            tmp = [it for (it, sc) in scored if (sc is None) or (sc >= min_meta_f)]
            if logger:
                logger.info("[position_manager] [HF] meta filter (%s): kept=%d/%d min_meta=%.2f",
                            context, len(tmp), len(items), min_meta_f)
            kept = tmp

            # HF fallback: si on a tout jeté, on garde quand même le top-1/ top-N (quand score dispo)
            if not kept:
                scored2 = [(it, _score(it)) for it in items if _score(it) is not None]
                scored2.sort(key=lambda t: t[1], reverse=True)
                # garde au minimum 1 élément, sinon rien
                fallback_n = 1
                kept = [it for (it, sc) in scored2[:fallback_n]]
                if logger:
                    logger.warning("[position_manager] [HF] meta filter (%s): all dropped -> fallback keep top=%d", context, len(kept))

    # 2) Cap max_open_positions (top-N by score, unknown scores go last)
    if max_pos is not None:
        try:
            n = int(max_pos)
        except Exception:
            n = None
        if n is not None and n >= 0 and len(kept) > n:
            scored = [(it, _score(it)) for it in kept]
            scored.sort(key=lambda t: (t[1] is not None, t[1] if t[1] is not None else -1e9), reverse=True)
            kept = [it for (it, sc) in scored[:n]]
            if logger:
                logger.info("[position_manager] [HF] cap (%s): max_open_positions=%d -> n=%d", context, n, len(kept))

    # 3) Scale sizing fields
    if mult != 1.0 and mult >= 0.0:
        for it in kept:
            if not isinstance(it, dict):
                continue
            for k in ("notional_eur", "target_notional_eur", "capital_per_trade_eur", "size", "amount"):
                _scale_field(it, k, mult)
        if logger:
            logger.info("[position_manager] [HF] sizing mult (%s): position_size_mult=%.3f", context, mult)

    return kept

def get_last_close_and_atr(
    ohlcv_symbol: Any,
    period: int = 14,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Best-effort pour récupérer dernier close + ATR à partir de différents formats OHLCV :
    - list[dict] avec high/low/close
    - dict avec 'candles': [...]
    - dict avec 'high'/'low'/'close' sous forme de listes
    """
    if not ohlcv_symbol:
        return None, None

    if isinstance(ohlcv_symbol, dict) and "candles" in ohlcv_symbol:
        bars = ohlcv_symbol.get("candles") or []
        if not isinstance(bars, list):
            return None, None
        return _compute_atr_from_bars(bars, period)

    if isinstance(ohlcv_symbol, dict) and all(k in ohlcv_symbol for k in ("high", "low", "close")):
        highs = ohlcv_symbol.get("high") or []
        lows = ohlcv_symbol.get("low") or []
        closes = ohlcv_symbol.get("close") or []
        bars = [{"high": h, "low": l, "close": c} for h, l, c in zip(highs, lows, closes)]
        return _compute_atr_from_bars(bars, period)

    if isinstance(ohlcv_symbol, list):
        return _compute_atr_from_bars(ohlcv_symbol, period)

    return None, None

# ============================================================================
# Chargement des fichiers
# ============================================================================

def _path(data_dir: str, *parts: str) -> str:
    return os.path.join(data_dir, *parts)

def load_open_positions(data_dir: str) -> List[Dict[str, Any]]:
    path = _path(data_dir, "trading", "open_positions.json")
    positions = load_json_file(path, default=[])
    if isinstance(positions, dict):
        positions = positions.get("positions", [])
    if not isinstance(positions, list):
        logger.warning("[position_manager] open_positions.json inattendu (%s) -> []", type(positions))
        return []
    return [p for p in positions if isinstance(p, dict)]

def load_exit_events(data_dir: str) -> List[Dict[str, Any]]:
    path = _path(data_dir, "trading", "exit_events.json")
    events = load_json_file(path, default=[])
    if isinstance(events, dict):
        events = events.get("events", [])
    if not isinstance(events, list):
        logger.warning("[position_manager] exit_events.json inattendu (%s) -> []", type(events))
        return []
    return [e for e in events if isinstance(e, dict)]

def _load_simulated_fills_prices(data_dir: str) -> dict:
    """
    Retourne dict symbol_norm -> last_fill_price à partir de data/trading/simulated_fills.json
    (best-effort sur clés: fill_price/price/executed_price/avg_price/close).
    """
    try:
        from src.v2.utils.file_utils import load_json_file
        path = _path(data_dir, "trading", "simulated_fills.json")
        fills = load_json_file(path, default=[]) or []
        out = {}
        if isinstance(fills, list):
            for f in fills:
                if not isinstance(f, dict):
                    continue
                sym = f.get("symbol") or f.get("token") or f.get("asset")
                sn = _normalize_symbol(sym)
                if not sn:
                    continue
                px = f.get("fill_price")
                if px is None: px = f.get("price")
                if px is None: px = f.get("executed_price")
                if px is None: px = f.get("avg_price")
                if px is None: px = f.get("close")
                try:
                    px = float(px) if px is not None else None
                except Exception:
                    px = None
                if px and px > 0:
                    out[sn] = px  # last wins
        # NSC_PATCH_SIMPRICES_NORMKEYS_V2
        # Add normalized keys so lookups work with symbol_norm (e.g., dotusdt/arbusdt).
        try:
            _norm_fn = globals().get('_normalize_symbol')
            if callable(_norm_fn):
                for _k, _v in list(sim_prices.items()):
                    _nk = _norm_fn(_k)
                    if _nk and _nk not in sim_prices:
                        sim_prices[_nk] = _v
            else:
                import re as _re
                def _fallback_norm(s):
                    return _re.sub(r'[^a-z0-9]', '', str(s).lower())
                for _k, _v in list(sim_prices.items()):
                    _nk = _fallback_norm(_k)
                    if _nk and _nk not in sim_prices:
                        sim_prices[_nk] = _v
        except Exception:
            pass
        return out
    except Exception:
        logger.exception("[position_manager] Impossible de charger simulated_fills.json pour fallback prix")
        return {}

def load_execution_plan_orders(data_dir: str) -> List[Dict[str, Any]]:
    """
    Charge le plan effectif d'exécution (execution_plan_simulated prioritaire si présent,
    sinon execution_plan.json) via load_effective_execution_plan.
    Retourne toujours une liste de dicts.
    """
    plan, plan_path = load_effective_execution_plan(data_dir, default={})
    orders: List[Dict[str, Any]] = []

    if isinstance(plan, dict) and isinstance(plan.get("orders"), list):
        orders = plan["orders"]
    elif isinstance(plan, list):
        orders = plan

    orders = [o for o in orders if isinstance(o, dict)]
    logger.info("[position_manager] execution_plan chargé (%s): %d ordres.", plan_path, len(orders))
    return orders

def load_signals(data_dir: str) -> List[Dict[str, Any]]:
    """
    Charge les signaux depuis plusieurs emplacements possibles.

    Priorité :
      1) data/trading/execution_plan.json  (dict.orders ou list)
      2) data/trading/sized_signals.json   (liste)
      3) legacy: data/analysis/signal_candidates_filtered.json
      4) legacy: data/analysis/signal_candidates.json
      5) legacy: data/trading/signals.json

    Retourne toujours une liste de dicts.
    """
    candidates = [
        _path(data_dir, "trading", "execution_plan_simulated.json"),
        _path(data_dir, "trading", "execution_plan.json"),
        _path(data_dir, "trading", "sized_signals.json"),
        _path(data_dir, "analysis", "signal_candidates_filtered.json"),
        _path(data_dir, "analysis", "signal_candidates.json"),
        _path(data_dir, "trading", "signals.json"),
    ]

    chosen: Optional[str] = None
    signals: List[Dict[str, Any]] = []

    for path in candidates:
        data = load_json_file(path, default=None)
        if data is None:
            continue

        chosen = path

        if isinstance(data, dict):
            if "orders" in data and isinstance(data["orders"], list):
                signals = data["orders"]
            elif "signals" in data and isinstance(data["signals"], list):
                signals = data["signals"]
            else:
                # fallback : première valeur list
                for v in data.values():
                    if isinstance(v, list):
                        signals = v
                        break

        elif isinstance(data, list):
            signals = data

        if signals:
            break

    signals = [s for s in signals if isinstance(s, dict)]

    # Guard anti-simulation:
    # - PREPROD: on autorise les signaux simulés (paper trading)
    # - PROD: on filtre dès le chargement
    if signals and os.environ.get("NSC_ENV","").strip().upper() == "PROD":
        before = len(signals)
        filtered = []
        skipped = 0
        for s in signals:
            srcv = (s.get("source") or "").lower().strip()
            if srcv == "derived_from_simulated_fills":
                skipped += 1
                continue
            filtered.append(s)
        signals = filtered
        if skipped:
            logger.warning("[position_manager] Skipped %d simulated-fill signals (load_signals, PROD).", skipped)
            logger.info("[position_manager] Signals: %d -> %d after simulated-fill filter.", before, len(signals))

    if chosen and signals:
        logger.info(
            "[position_manager] Signaux chargés (%s): %d lignes.",
            os.path.basename(chosen),
            len(signals),
        )
    else:
        logger.warning("[position_manager] Aucun fichier de signaux trouvé (candidates=%s).",
                       [os.path.basename(p) for p in candidates])

    return signals

def load_risk_engine(data_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Charge risk_engine_pro.json et renvoie un mapping symbol -> métriques de risque.
    """
    path = _path(data_dir, "analysis", "risk_engine_pro.json")
    data = load_json_file(path, default={})
    assets = data.get("assets", []) if isinstance(data, dict) else []

    by_symbol: Dict[str, Dict[str, Any]] = {}
    for a in assets:
        if not isinstance(a, dict):
            continue
        symbol = a.get("symbol") or a.get("token") or a.get("asset")
        if not symbol:
            continue
        by_symbol[str(symbol).lower()] = a

    logger.info("[position_manager] Risk Engine chargé (%d assets).", len(by_symbol))
    return by_symbol

def load_ohlcv(data_dir: str) -> Dict[str, Any]:
    path = _path(data_dir, "market", "ohlcv_combined.json")
    ohlcv = load_json_file(path, default={})

    # Support format legacy direct OU format v2 {timestamp, env, assets:[...]}
    if isinstance(ohlcv, dict) and "assets" in ohlcv:
        ohlcv = _nsc_ohlcv_v2_to_legacy_rows(ohlcv)

    if not isinstance(ohlcv, dict):
        logger.warning("[position_manager] ohlcv_combined.json inattendu (%s) -> {}", type(ohlcv))
        return {}

    return ohlcv

# ============================================================================
# Logique de position : TP partiels + Trailing
# ============================================================================

PARTIAL_LEVELS = [0.15, 0.30]   # +15 %, +30 %
PARTIAL_RATIOS = [0.40, 0.30]   # 40 %, puis 30 % (reste trailing)
STOP_LOSS_LEVEL = -0.10         # -10 %
STOP_LOSS_COOLDOWN_HOURS = 24     # évite de rouvrir immédiatement un token stoppé

# RC2 Reentry Quality Gate V1.
#
# Purpose:
# - preserve the existing stop-loss cooldown;
# - allow legitimate second momentum entries;
# - prevent repeated exploitation of an exhausted impulse;
# - reject an extended TP1-only reentry when momentum confirmation
#   was insufficient to reach TP2 on the previous cycle.
PROFIT_REENTRY_LOOKBACK_HOURS = 24
PROFIT_REENTRY_TP1_ONLY_MAX_EXTENSION_PCT = 12.5

MARKET_MOMENTUM_PARTIAL_LEVELS = [0.12, 0.25]  # +12 %, +25 %
MARKET_MOMENTUM_STOP_LOSS_LEVEL = -0.07        # -7 %

TRAILING_ATR_MULTIPLIER = 2.0
TRAILING_MIN_PCT = 0.06  # 6 %
TRAILING_MAX_PCT = 0.18  # 18 %

def _normalize_side(side: Optional[str]) -> str:
    s = (side or "long").lower().strip()
    if s in ("buy", "long"):
        return "long"
    if s in ("sell", "short"):
        return "short"
    return "long"

def _normalize_symbol(symbol: Optional[str]) -> Optional[str]:
    if symbol is None:
        return None
    return str(symbol).lower().strip()

def _get_price_and_atr_for_symbol(
    ohlcv_all: Dict[str, Any],
    symbol: str,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Retourne (last_close, atr) pour un symbole donné.
    Gère les variantes :
      - maticusdt / MATICUSDT
      - matic-usdt / matic/usdt
      - matic
    Retourne TOUJOURS un tuple.
    """
    key = _normalize_symbol(symbol)
    if not key or not isinstance(ohlcv_all, dict) or not ohlcv_all:
        return None, None

    # Support schema:
    # {
    #   "assets": [
    #      {"symbol": "PORTAL", "candles": [...]},
    #      ...
    #   ],
    #   "env": "...",
    #   "timestamp": "..."
    # }
    assets = ohlcv_all.get("assets")
    if isinstance(assets, list):
        indexed = {}
        for item in assets:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol") or item.get("pair") or item.get("asset") or item.get("token")
            if not sym:
                continue
            s = str(sym).lower().replace("-", "").replace("/", "").replace("_", "")
            indexed[s] = item
            if not s.endswith("usdt"):
                indexed[s + "usdt"] = item
        ohlcv_all = indexed
    elif isinstance(assets, dict):
        ohlcv_all = assets

    candidates = set()
    candidates.add(key)
    candidates.add(key.upper())

    # variantes sans séparateurs
    compact = key.replace("-", "").replace("/", "").replace("_", "")
    candidates.add(compact)
    candidates.add(compact.upper())

    # base asset only
    if compact.endswith("usdt"):
        base = compact[:-4]
        candidates.add(base)
        candidates.add(base.upper())
        candidates.add(base + "usdt")
        candidates.add((base + "usdt").upper())

    # Support schema:
    # 1) direct map: {"ADAUSDT": [...]}
    # 2) wrapped assets: {"assets": [{"symbol": "ADAUSDT", "candles": [...]}]}
    searchable = {}

    if isinstance(ohlcv_all.get("assets"), list):
        for item in ohlcv_all.get("assets", []):
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol")
            if not sym:
                continue
            searchable[str(sym)] = item
    else:
        searchable = ohlcv_all

    normalized_map = {}
    for raw_k in searchable.keys():
        raw_s = str(raw_k)
        nk = raw_s.lower().replace("-", "").replace("/", "").replace("_", "")
        normalized_map[nk] = raw_k

    for cand in candidates:
        cand_norm = str(cand).lower().replace("-", "").replace("/", "").replace("_", "")
        raw_key = normalized_map.get(cand_norm)
        if raw_key in searchable:
            try:
                res = get_last_close_and_atr(searchable[raw_key])
                if isinstance(res, tuple) and len(res) == 2 and res[0] is not None:
                    return res
            except Exception:
                logger.exception("[position_manager] _get_price_and_atr_for_symbol failed for symbol=%s key=%s", symbol, raw_key)
                return None, None

    # Fallback spot prices for tokens without OHLCV candles.
    try:
        spot_path = Path(os.environ.get("NSC_DATA_DIR", "/opt/nsc/data/preprod")) / "market" / "crypto_spot_prices.json"
        spot = load_json_file(str(spot_path), default={}) or {}
        base = compact[:-4] if compact.endswith("usdt") else compact

        for k in {base, base.upper(), compact, compact.upper()}:
            raw = spot.get(k)
            if raw is None:
                continue
            price = raw.get("price") if isinstance(raw, dict) else raw
            price = float(price or 0.0)
            if price > 0:
                return price, None
    except Exception:
        logger.exception("[position_manager] spot price fallback failed for symbol=%s", symbol)

    return None, None

def _compute_trailing_params(
    last_close: float,
    atr: Optional[float],
) -> Tuple[float, float]:
    """
    Renvoie (trailing_pct, trailing_price).
    trailing_pct borné entre TRAILING_MIN_PCT et TRAILING_MAX_PCT.
    """
    if atr is None or last_close <= 0:
        trailing_pct = 0.10  # fallback 10%
    else:
        raw_pct = (atr * TRAILING_ATR_MULTIPLIER) / float(last_close)
        trailing_pct = max(TRAILING_MIN_PCT, min(TRAILING_MAX_PCT, raw_pct))

    trailing_price = last_close * (1.0 - trailing_pct)
    return trailing_pct, trailing_price

def _compute_pnl(
    entry_price: float,
    exit_price: float,
    size: float,
    side: str = "long",
) -> float:
    if size <= 0 or entry_price <= 0:
        return 0.0
    direction = 1.0 if side.lower() != "short" else -1.0
    return (exit_price - entry_price) * size * direction

def _dedup_positions_keep_latest(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dédup par (symbol_norm, side_norm) en conservant la position la plus récente (opened_at max).
    """
    best: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def _ts(p: Dict[str, Any]) -> str:
        # string ISOZ comparables lexicographiquement si format stable
        return str(p.get("opened_at") or p.get("timestamp") or "")

    for p in positions:
        if not isinstance(p, dict):
            continue
        sym = _normalize_symbol(p.get("symbol") or p.get("token") or p.get("asset"))
        if not sym:
            continue
        side = _normalize_side(p.get("side"))
        k = (sym, side)

        if k not in best:
            best[k] = p
            continue

        if _ts(p) >= _ts(best[k]):
            best[k] = p

    return list(best.values())


def _recent_stoploss_symbols(exit_events, now_dt, hours=24):
    out = set()
    cutoff = now_dt - timedelta(hours=hours)
    for e in exit_events:
        if not isinstance(e, dict):
            continue
        if e.get("exit_type") != "stop_loss":
            continue
        sym = _normalize_symbol(e.get("symbol"))
        ts = str(e.get("timestamp") or "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        if sym and dt >= cutoff:
            out.add(sym)
    return out


def _profit_reentry_quality_gate(
    exit_events,
    symbol,
    now_dt,
    candidate_entry_price=None,
):
    """
    RC2 Reentry Quality Gate V1.

    This gate applies only to NEW positions. Existing-position
    reinforcement remains governed by the existing sizing logic.

    Rules:
    1. Stop-loss cooldown is handled independently by
       _recent_stoploss_symbols().
    2. Consider positive TP/trailing economic exits from the last
       PROFIT_REENTRY_LOOKBACK_HOURS.
    3. Group those exits by entry price to approximate distinct
       momentum-entry cycles.
    4. The number of profitable cycles is recorded for observation
       only and is not an autonomous veto.
    5. After a TP1-only cycle, reject an extended reentry if the
       candidate price is more than the configured percentage above
       that cycle's entry price.

    Returns:
        (allowed: bool, reason: str, context: dict)
    """
    symbol_norm = _normalize_symbol(symbol)

    if not symbol_norm:
        return True, "no_symbol", {}

    cutoff = now_dt - timedelta(
        hours=PROFIT_REENTRY_LOOKBACK_HOURS
    )

    profitable_types = {
        "partial_tp1",
        "partial_tp2",
        "trailing_stop",
    }

    cycles = {}

    for event in exit_events:
        if not isinstance(event, dict):
            continue

        event_symbol = _normalize_symbol(
            event.get("symbol")
        )

        if event_symbol != symbol_norm:
            continue

        exit_type = str(
            event.get("exit_type") or ""
        ).strip().lower()

        if exit_type not in profitable_types:
            continue

        try:
            pnl = float(event.get("pnl") or 0.0)
        except Exception:
            pnl = 0.0

        if pnl <= 0:
            continue

        raw_ts = str(
            event.get("timestamp") or ""
        )

        try:
            event_dt = datetime.fromisoformat(
                raw_ts.replace("Z", "+00:00")
            )
        except Exception:
            continue

        if event_dt < cutoff:
            continue

        try:
            entry_price = float(
                event.get("entry_price") or 0.0
            )
        except Exception:
            entry_price = 0.0

        if entry_price <= 0:
            continue

        # Entry price identifies one position lifecycle in the
        # current crypto runtime. Rounding protects grouping from
        # harmless float serialization noise.
        cycle_key = round(entry_price, 12)

        cycle = cycles.setdefault(
            cycle_key,
            {
                "entry_price": entry_price,
                "exit_types": set(),
                "latest_exit_at": event_dt,
                "realized_pnl": 0.0,
            },
        )

        cycle["exit_types"].add(exit_type)
        cycle["realized_pnl"] += pnl

        if event_dt > cycle["latest_exit_at"]:
            cycle["latest_exit_at"] = event_dt

    ordered_cycles = sorted(
        cycles.values(),
        key=lambda x: x["latest_exit_at"],
    )

    context = {
        "profitable_cycles": len(ordered_cycles),
        "lookback_hours": (
            PROFIT_REENTRY_LOOKBACK_HOURS
        ),
    }

    if not ordered_cycles:
        return True, "first_entry", context

    latest = ordered_cycles[-1]

    latest_types = latest["exit_types"]

    # TP2 confirms that the preceding impulse had enough breadth
    # to permit one additional opportunity. TP1 alone does not.
    tp1_only = (
        "partial_tp1" in latest_types
        and "partial_tp2" not in latest_types
    )

    try:
        candidate_price = float(
            candidate_entry_price or 0.0
        )
    except Exception:
        candidate_price = 0.0

    previous_entry = float(
        latest["entry_price"]
    )

    if (
        tp1_only
        and candidate_price > 0
        and previous_entry > 0
    ):
        extension_pct = (
            (
                candidate_price
                / previous_entry
            )
            - 1.0
        ) * 100.0

        context["previous_entry_price"] = (
            round(previous_entry, 12)
        )
        context["candidate_entry_price"] = (
            round(candidate_price, 12)
        )
        context["extension_pct"] = round(
            extension_pct,
            4,
        )

        if extension_pct > (
            PROFIT_REENTRY_TP1_ONLY_MAX_EXTENSION_PCT
        ):
            context["rule"] = (
                "tp1_only_extended_reentry"
            )

            return (
                False,
                "tp1_only_extended_reentry",
                context,
            )

    return True, "reentry_quality_pass", context


def update_positions(
    data_dir: str,
    positions: List[Dict[str, Any]],
    exit_events: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    risk_by_symbol: Dict[str, Dict[str, Any]],
    ohlcv_all: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """
    Règles :
    - TP1 : 40% à +15%
    - TP2 : 30% à +30%
    - Trailing ATR sur le reste
    - Ouverture de nouvelles positions via signaux (execution_plan/sized_signals)
      en tenant compte du Risk Engine (hard/soft veto, size_multiplier).
    """
    now_ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    new_exit_events = 0
    new_positions = 0
    closed_symbols_this_run = set()
    now_dt = datetime.now(timezone.utc)
    stoploss_cooldown_symbols = _recent_stoploss_symbols(
        exit_events, now_dt, STOP_LOSS_COOLDOWN_HOURS
    )

    # Dédup d'entrée (au cas où l'historique a déjà été pollué)
    positions = _dedup_positions_keep_latest([p for p in positions if isinstance(p, dict)])

    # Index positions actives par symbole
    active_by_symbol: Dict[str, Dict[str, Any]] = {}
    for pos in positions:
        sym = _normalize_symbol(pos.get("symbol") or pos.get("token") or pos.get("asset"))
        if not sym:
            continue
        rem = float(pos.get("remaining_size", pos.get("size", 0.0)) or 0.0)
        if rem > 0 and not bool(pos.get("closed", False)):
            active_by_symbol[sym] = pos

    # ----------------------------------------------------------------------
    # 1) Exits (TP1/TP2/Trailing)
    # ----------------------------------------------------------------------
    for pos in positions:
        side = _normalize_side(pos.get("side"))
        symbol_raw = pos.get("symbol") or pos.get("token") or pos.get("asset")
        symbol_norm = _normalize_symbol(symbol_raw)

        size = float(pos.get("size", 0.0) or 0.0)
        remaining_size = float(pos.get("remaining_size", size) or 0.0)
        entry_price = pos.get("entry_price") or pos.get("price")

        if symbol_norm is None or remaining_size <= 0 or entry_price is None:
            continue

        entry_price = float(entry_price)
        last_close, atr = _get_price_and_atr_for_symbol(ohlcv_all, str(symbol_raw))
        if last_close is None or entry_price <= 0:
            continue
        last_close = float(last_close)

        perf = (last_close - entry_price) / entry_price if side == "long" else (entry_price - last_close) / entry_price

        tp1_done = bool(pos.get("tp1_done", False))
        tp2_done = bool(pos.get("tp2_done", False))
        realized_pnl = float(pos.get("realized_pnl", 0.0) or 0.0)

        strategy = str(pos.get("strategy") or "").strip().lower()
        is_market_momentum = strategy == "market_momentum"

        partial_levels = MARKET_MOMENTUM_PARTIAL_LEVELS if is_market_momentum else PARTIAL_LEVELS
        stop_loss_level = MARKET_MOMENTUM_STOP_LOSS_LEVEL if is_market_momentum else STOP_LOSS_LEVEL

        # Stop-loss
        if perf <= stop_loss_level and remaining_size > 0:
            exit_size = remaining_size
            exit_pnl = _compute_pnl(entry_price, last_close, exit_size, side)
            realized_pnl += exit_pnl
            remaining_size = 0.0
            new_exit_events += 1
            exit_events.append({
                "timestamp": now_ts,
                "symbol": symbol_raw,
                "side": side,
                "exit_type": "stop_loss",
                "reason": f"Stop-loss atteint ({int(stop_loss_level*100)}%)",
                "price": last_close,
                "size": exit_size,
                "pnl": exit_pnl,
                "strategy": pos.get("strategy"),
                "entry_price": entry_price,
                "risk_flag": pos.get("risk_flag"),
                "meta_score": pos.get("meta_score"),

                # RC2 Meta Decision Lineage V1.
                "meta_score_pro": pos.get("meta_score_pro"),
                "meta_rank": pos.get("meta_rank"),
                "meta_verdict": pos.get("meta_verdict"),
                "meta_recommended": pos.get("meta_recommended"),
                "meta_execution_gate": pos.get("meta_execution_gate"),
                "execution_eligible": pos.get("execution_eligible"),
                "execution_confirmed": pos.get("execution_confirmed"),
                "decision_chg_24h": pos.get("decision_chg_24h"),
                "momentum_source": pos.get("momentum_source"),
                "execution_pair": pos.get("execution_pair"),
                "execution_source": pos.get("execution_source"),
                "cross_source_direction_conflict": pos.get("cross_source_direction_conflict"),
                "meta_risk_flags": list(pos.get("meta_risk_flags") or []),
                "execution_mode": pos.get("execution_mode"),
            })
            logger.info("[position_manager] STOP LOSS %s: size=%.6f price=%.6f pnl=%.4f",
                        symbol_raw, exit_size, last_close, exit_pnl)

        # TP1
        if (not tp1_done) and perf >= partial_levels[0] and remaining_size > 0:
            exit_size = remaining_size * PARTIAL_RATIOS[0]
            exit_pnl = _compute_pnl(entry_price, last_close, exit_size, side)
            remaining_size -= exit_size
            realized_pnl += exit_pnl
            tp1_done = True
            new_exit_events += 1
            exit_events.append({
                "timestamp": now_ts,
                "symbol": symbol_raw,
                "side": side,
                "exit_type": "partial_tp1",
                "reason": f"TP1 atteint (+{int(partial_levels[0]*100)}%)",
                "price": last_close,
                "size": exit_size,
                "pnl": exit_pnl,
                "strategy": pos.get("strategy"),
                "entry_price": entry_price,
                "risk_flag": pos.get("risk_flag"),
                "meta_score": pos.get("meta_score"),

                # RC2 Meta Decision Lineage V1.
                "meta_score_pro": pos.get("meta_score_pro"),
                "meta_rank": pos.get("meta_rank"),
                "meta_verdict": pos.get("meta_verdict"),
                "meta_recommended": pos.get("meta_recommended"),
                "meta_execution_gate": pos.get("meta_execution_gate"),
                "execution_eligible": pos.get("execution_eligible"),
                "execution_confirmed": pos.get("execution_confirmed"),
                "decision_chg_24h": pos.get("decision_chg_24h"),
                "momentum_source": pos.get("momentum_source"),
                "execution_pair": pos.get("execution_pair"),
                "execution_source": pos.get("execution_source"),
                "cross_source_direction_conflict": pos.get("cross_source_direction_conflict"),
                "meta_risk_flags": list(pos.get("meta_risk_flags") or []),
                "execution_mode": pos.get("execution_mode"),
            })
            logger.info("[position_manager] TP1 %s: size=%.6f price=%.6f pnl=%.4f",
                        symbol_raw, exit_size, last_close, exit_pnl)

        # TP2
        if (not tp2_done) and perf >= partial_levels[1] and remaining_size > 0:
            pass  # auto-fix empty if
            # ratio appliqué sur le restant (après TP1) pour approx 30% initial
            denom = max(1e-9, 1.0 - PARTIAL_RATIOS[0])
            exit_size = remaining_size * (PARTIAL_RATIOS[1] / denom)
            exit_size = min(exit_size, remaining_size)

            exit_pnl = _compute_pnl(entry_price, last_close, exit_size, side)
            remaining_size -= exit_size
            realized_pnl += exit_pnl
            tp2_done = True
            new_exit_events += 1
            exit_events.append({
                "timestamp": now_ts,
                "symbol": symbol_raw,
                "side": side,
                "exit_type": "partial_tp2",
                "reason": f"TP2 atteint (+{int(partial_levels[1]*100)}%)",
                "price": last_close,
                "size": exit_size,
                "pnl": exit_pnl,
                "strategy": pos.get("strategy"),
                "entry_price": entry_price,
                "risk_flag": pos.get("risk_flag"),
                "meta_score": pos.get("meta_score"),

                # RC2 Meta Decision Lineage V1.
                "meta_score_pro": pos.get("meta_score_pro"),
                "meta_rank": pos.get("meta_rank"),
                "meta_verdict": pos.get("meta_verdict"),
                "meta_recommended": pos.get("meta_recommended"),
                "meta_execution_gate": pos.get("meta_execution_gate"),
                "execution_eligible": pos.get("execution_eligible"),
                "execution_confirmed": pos.get("execution_confirmed"),
                "decision_chg_24h": pos.get("decision_chg_24h"),
                "momentum_source": pos.get("momentum_source"),
                "execution_pair": pos.get("execution_pair"),
                "execution_source": pos.get("execution_source"),
                "cross_source_direction_conflict": pos.get("cross_source_direction_conflict"),
                "meta_risk_flags": list(pos.get("meta_risk_flags") or []),
                "execution_mode": pos.get("execution_mode"),
            })
            logger.info("[position_manager] TP2 %s: size=%.6f price=%.6f pnl=%.4f",
                        symbol_raw, exit_size, last_close, exit_pnl)

        # Trailing
        trailing_active = bool(pos.get("trailing_active", False))
        trailing_stop = pos.get("trailing_stop")

        if (not trailing_active) and remaining_size > 0 and (tp2_done or (is_market_momentum and tp1_done) or perf >= partial_levels[0] * 2):
            trailing_pct, trailing_price = _compute_trailing_params(last_close, atr)
            trailing_active = True
            trailing_stop = trailing_price
            logger.info("[position_manager] Trailing ON %s: pct=%.2f%% stop=%.6f",
                        symbol_raw, trailing_pct * 100.0, trailing_price)

        if trailing_active and trailing_stop is not None and remaining_size > 0:
            trailing_stop = float(trailing_stop)
            _, new_trailing_price = _compute_trailing_params(last_close, atr)

            # Stop monotone
            if side == "long":
                if new_trailing_price > trailing_stop:
                    trailing_stop = new_trailing_price
                stop_hit = last_close <= trailing_stop
            else:
                # short: stop au-dessus, monotone "descendant" n'a pas de sens ici -> on garde simple
                # (si tu veux short sérieux, on adaptera après)
                stop_hit = last_close >= trailing_stop

            if stop_hit:
                exit_size = remaining_size
                exit_pnl = _compute_pnl(entry_price, last_close, exit_size, side)
                realized_pnl += exit_pnl
                remaining_size = 0.0
                trailing_active = False
                new_exit_events += 1
                exit_events.append({
                    "timestamp": now_ts,
                    "symbol": symbol_raw,
                    "side": side,
                    "exit_type": "trailing_stop",
                    "reason": "Trailing stop déclenché",
                    "price": last_close,
                    "size": exit_size,
                    "pnl": exit_pnl,
                    "strategy": pos.get("strategy"),
                    "entry_price": entry_price,
                    "risk_flag": pos.get("risk_flag"),
                    "meta_score": pos.get("meta_score"),

                    # RC2 Meta Decision Lineage V1.
                    "meta_score_pro": pos.get("meta_score_pro"),
                    "meta_rank": pos.get("meta_rank"),
                    "meta_verdict": pos.get("meta_verdict"),
                    "meta_recommended": pos.get("meta_recommended"),
                    "meta_execution_gate": pos.get("meta_execution_gate"),
                    "execution_eligible": pos.get("execution_eligible"),
                    "execution_confirmed": pos.get("execution_confirmed"),
                    "decision_chg_24h": pos.get("decision_chg_24h"),
                    "momentum_source": pos.get("momentum_source"),
                    "execution_pair": pos.get("execution_pair"),
                    "execution_source": pos.get("execution_source"),
                    "cross_source_direction_conflict": pos.get("cross_source_direction_conflict"),
                    "meta_risk_flags": list(pos.get("meta_risk_flags") or []),
                    "execution_mode": pos.get("execution_mode"),
                })
                logger.info("[position_manager] Trailing HIT %s: size=%.6f price=%.6f pnl=%.4f",
                            symbol_raw, exit_size, last_close, exit_pnl)

        # update pos
        pos["remaining_size"] = float(max(0.0, remaining_size))
        pos["tp1_done"] = tp1_done
        pos["tp2_done"] = tp2_done
        pos["trailing_active"] = trailing_active
        if trailing_stop is not None:
            pos["trailing_stop"] = float(trailing_stop)
        pos["realized_pnl"] = float(realized_pnl)

        if pos["remaining_size"] <= 0:
            pos["closed_at"] = now_ts
            pos["closed"] = True
            if symbol_norm:
                closed_symbols_this_run.add(symbol_norm)
    # NSC_FIX_PREPROD_ALLOW_PAPER_OPENINGS_V1
    # En PREPROD / DRY_RUN, on autorise les ouvertures papier.
    # Le blocage des ordres réels est déjà géré par execution_engine_pro + governance.
    env_name = (os.environ.get("NSC_ENV") or "").strip().upper()
    if is_dry_run_enabled() and env_name == "PROD":
        logger.info("[position_manager] NSC_DRY_RUN=1 en PROD => skip ouverture nouvelles positions")
        return positions, exit_events, 0, 0

    # ----------------------------------------------------------------------
    # 1.5) PREPROD cleanup: remove paper positions no longer present in current execution plan
    # ----------------------------------------------------------------------
    try:
        env_cleanup = (os.environ.get("NSC_ENV") or "").strip().upper()
        data_dir_cleanup = str(data_dir).lower()
        is_preprod_cleanup = env_cleanup == "PREPROD" or "/preprod" in data_dir_cleanup
        if is_preprod_cleanup and isinstance(signals, list) and signals:
            plan_symbols = {
                _normalize_symbol(s.get("symbol") or s.get("token") or s.get("asset"))
                for s in signals
                if isinstance(s, dict)
            }
            plan_symbols = {s for s in plan_symbols if s}

            cleaned_positions = []
            for pos in positions:
                sym = _normalize_symbol(pos.get("symbol") or pos.get("token") or pos.get("asset"))
                rem = float(pos.get("remaining_size", pos.get("size", 0.0)) or 0.0)
                is_open = rem > 0 and not bool(pos.get("closed", False))
                is_paper = bool(pos.get("paper", False)) or str(pos.get("execution_mode", "")).upper() == "SIMULATED_ONLY"

                if is_open and is_paper and sym:
                    if sym in plan_symbols:
                        pos["stale_plan_miss_count"] = 0
                    else:
                        grace_cycles = int(os.environ.get("NSC_STALE_PLAN_CLEANUP_GRACE_CYCLES", "6"))
                        miss_count = int(pos.get("stale_plan_miss_count", 0) or 0) + 1
                        pos["stale_plan_miss_count"] = miss_count
                        pos["stale_plan_last_missing_at"] = now_ts

                        if miss_count >= grace_cycles:
                            pos["closed"] = True
                            pos["closed_at"] = now_ts
                            pos["close_reason"] = "stale_not_in_current_execution_plan_after_grace"
                            exit_events.append({
                                "timestamp": now_ts,
                                "symbol": pos.get("symbol"),
                                "side": _normalize_side(pos.get("side")),
                                "exit_type": "stale_plan_cleanup",
                                "reason": f"Position papier absente du plan depuis {miss_count} cycles",
                                "price": pos.get("entry_price"),
                                "size": rem,
                                "pnl": 0.0,
                                "strategy": pos.get("strategy"),
                                "entry_price": pos.get("entry_price"),
                                "risk_flag": pos.get("risk_flag"),
                                "meta_score": pos.get("meta_score"),

                                # RC2 Meta Decision Lineage V1.
                                "meta_score_pro": pos.get("meta_score_pro"),
                                "meta_rank": pos.get("meta_rank"),
                                "meta_verdict": pos.get("meta_verdict"),
                                "meta_recommended": pos.get("meta_recommended"),
                                "meta_execution_gate": pos.get("meta_execution_gate"),
                                "execution_eligible": pos.get("execution_eligible"),
                                "execution_confirmed": pos.get("execution_confirmed"),
                                "decision_chg_24h": pos.get("decision_chg_24h"),
                                "momentum_source": pos.get("momentum_source"),
                                "execution_pair": pos.get("execution_pair"),
                                "execution_source": pos.get("execution_source"),
                                "cross_source_direction_conflict": pos.get("cross_source_direction_conflict"),
                                "meta_risk_flags": list(pos.get("meta_risk_flags") or []),
                                "execution_mode": pos.get("execution_mode"),
                                "stale_plan_miss_count": miss_count,
                                "grace_cycles": grace_cycles,
                            })
                            new_exit_events += 1
                            continue

                cleaned_positions.append(pos)

            positions = cleaned_positions
            active_by_symbol = {
                _normalize_symbol(pos.get("symbol") or pos.get("token") or pos.get("asset")): pos
                for pos in positions
                if _normalize_symbol(pos.get("symbol") or pos.get("token") or pos.get("asset"))
                and float(pos.get("remaining_size", pos.get("size", 0.0)) or 0.0) > 0
                and not bool(pos.get("closed", False))
            }
    except Exception:
        logger.exception("[position_manager] stale plan cleanup failed")

    # ----------------------------------------------------------------------
    # 2) Ouverture nouvelles positions
    # ----------------------------------------------------------------------
    skip_counts = Counter()
    sim_prices = _load_simulated_fills_prices(data_dir)
        # Use the signals already loaded upstream (execution_plan first, then fallbacks)
    entry_candidates = signals if isinstance(signals, list) else []
    if not isinstance(entry_candidates, list) or not entry_candidates:
        entry_candidates = signals
    # ------------------------------------------------------------
    # NSC_FIX_OPEN_FROM_EXECUTION_PLAN_SIGNALS_V1
    # Source of truth = signals déjà chargés (execution_plan_simulated en PREPROD)
    # Ne jamais re-prioriser sized_signals_hf.json ici.
    # ------------------------------------------------------------
    entry_candidates = signals if isinstance(signals, list) else []
    if not isinstance(entry_candidates, list) or not entry_candidates:
        entry_candidates = []


    for sig in entry_candidates:
        src = str(sig.get("source") or "").lower().strip()
        symbol_raw = sig.get("symbol") or sig.get("token") or sig.get("asset")
        symbol_norm = _normalize_symbol(symbol_raw)
        if not symbol_norm:
            continue

        if symbol_norm in closed_symbols_this_run:
            skip_counts["closed_this_run_no_reopen"] += 1
            logger.info("[position_manager] skip reopen after exit in same run symbol=%s", symbol_raw)
            continue

        if symbol_norm in stoploss_cooldown_symbols:
            skip_counts["stoploss_cooldown"] += 1
            logger.info("[position_manager] skip reopen during stop-loss cooldown symbol=%s", symbol_raw)
            continue

        if symbol_norm in active_by_symbol:
            existing = active_by_symbol.get(symbol_norm)

            try:
                # PREPROD sizing rule:
                # notional_eur is the source of truth.
                # `notional` may be USDT-derived and must not override EUR sizing.
                target_notional = float(
                    sig.get("notional_eur")
                    or sig.get("target_notional_eur")
                    or sig.get("notional")
                    or 0.0
                )
            except Exception:
                target_notional = 0.0

            try:
                current_notional = float(existing.get("notional_eur") or 0.0)
            except Exception:
                current_notional = 0.0

            # If notional_eur is missing, reconstruct from size * entry_price.
            if current_notional <= 0:
                try:
                    current_notional = float(existing.get("remaining_size", existing.get("size", 0.0)) or 0.0) * float(existing.get("entry_price") or 0.0)
                except Exception:
                    current_notional = 0.0

            # PREPROD paper-position alignment:
            # if the current simulated position is above the new target,
            # downscale it to keep portfolio exposure coherent with sizing.
            if (
                (
                    str(os.environ.get("NSC_ENV") or "").upper() == "PREPROD"
                    or "/preprod" in str(data_dir).lower()
                )
                and target_notional > 0
                and current_notional > target_notional
                and bool(existing.get("paper", False))
            ):
                ratio = target_notional / current_notional
                existing["size"] = round(float(existing.get("size", 0.0) or 0.0) * ratio, 12)
                existing["remaining_size"] = round(float(existing.get("remaining_size", existing.get("size", 0.0)) or 0.0) * ratio, 12)
                existing["notional_eur"] = round(target_notional, 6)
                existing["target_notional_eur_snapshot"] = round(target_notional, 6)
                existing["preprod_downscaled_from_notional_eur"] = round(current_notional, 6)
                existing["last_downscaled_at"] = now_ts
                skip_counts["preprod_downscaled_existing"] += 1
                logger.info(
                    "[position_manager] preprod downscaled existing symbol=%s current_notional=%.2f target_notional=%.2f",
                    symbol_raw,
                    current_notional,
                    target_notional,
                )
                continue

            if target_notional > current_notional > 0:
                gap = target_notional - current_notional
                max_add = current_notional * 0.50
                add_notional = min(gap, max_add)

                try:
                    entry_price_existing = float(existing.get("entry_price") or sig.get("price_ref") or sig.get("price") or 0.0)
                except Exception:
                    entry_price_existing = 0.0

                if add_notional > 0 and entry_price_existing > 0:
                    add_size = add_notional / entry_price_existing

                    existing["size"] = float(existing.get("size", 0.0) or 0.0) + add_size
                    existing["remaining_size"] = float(existing.get("remaining_size", existing.get("size", 0.0)) or 0.0) + add_size
                    existing["notional_eur"] = round(current_notional + add_notional, 6)
                    existing["last_reinforced_at"] = now_ts
                    existing["reinforced_from_plan"] = True
                    existing["reinforcement_notional_eur"] = round(add_notional, 6)
                    existing["target_notional_eur_snapshot"] = round(target_notional, 6)

                    skip_counts["reinforced_existing"] += 1
                    logger.info(
                        "[position_manager] reinforced existing symbol=%s current_notional=%.2f target_notional=%.2f add_notional=%.2f new_notional=%.2f",
                        symbol_raw,
                        current_notional,
                        target_notional,
                        add_notional,
                        current_notional + add_notional,
                    )
                    continue

            skip_counts["already_open"] += 1
            continue

        # ----------------------------------------------------------
        # RC2 REENTRY QUALITY GATE V1
        #
        # Important:
        # this is deliberately AFTER active_by_symbol handling.
        # Existing-position reinforcement is therefore unchanged.
        # ----------------------------------------------------------
        candidate_entry_price = (
            sig.get("entry_price")
            or sig.get("price_ref")
            or sig.get("price")
        )

        (
            reentry_allowed,
            reentry_reason,
            reentry_context,
        ) = _profit_reentry_quality_gate(
            exit_events=exit_events,
            symbol=symbol_raw,
            now_dt=now_dt,
            candidate_entry_price=(
                candidate_entry_price
            ),
        )

        if not reentry_allowed:
            skip_counts[
                "reentry_quality_gate"
            ] += 1

            logger.info(
                "[position_manager] "
                "skip reentry quality gate "
                "symbol=%s reason=%s context=%s",
                symbol_raw,
                reentry_reason,
                reentry_context,
            )

            continue

        side = _normalize_side(sig.get("side"))
        execution_mode = str(sig.get("execution_mode") or sig.get("action") or "").upper()
        blocked_by = sig.get("blocked_by") or []
        executable = bool(sig.get("executable", True))

        _env_name = (os.environ.get("NSC_ENV", "") or "").strip().upper()

        is_simulated = (
            _env_name == "PREPROD"
            or src == "derived_from_simulated_fills"
            or "SIMULATED" in execution_mode
            or (not executable)
            or any("soft_veto" in str(x).lower() for x in blocked_by)
        )

        if is_simulated and os.environ.get("NSC_ENV", "").strip().upper() == "PROD":
            skip_counts["simulated_source_prod"] += 1
            logger.info("[position_manager] skip_open:simulated_source_prod symbol=%s", symbol_raw)
            continue

        risk = risk_by_symbol.get(symbol_norm, {})
        risk_flag = str(risk.get("risk_flag", "unknown"))
        size_multiplier = float(risk.get("size_multiplier", 1.0) or 1.0)
        flags = risk.get("flags") or {}
        hard_veto = bool(flags.get("hard_veto", False))
        soft_veto = bool(flags.get("soft_veto", False))

        if hard_veto or risk_flag == "danger":
            skip_counts["hard_veto_or_danger"] += 1
            continue

        logger.info(
            "[position_manager] signal symbol=%s action=%s execution_mode=%s blocked_by=%s price=%s price_ref=%s notional_eur=%s",
            symbol_raw,
            sig.get("action"),
            execution_mode,
            blocked_by,
            sig.get("price"),
            sig.get("price_ref"),
            sig.get("notional_eur"),
        )

        # NSC_STRICT_EXECUTION_PLAN_GATE_V1
        # En PREPROD/DRY_RUN, execution_plan est la source de vérité :
        # on n'ouvre pas une position si le plan n'a ni qty valide,
        # ni price_ref exploitable avec notional_eur.
        try:
            _env_name_gate = (os.environ.get("NSC_ENV") or "").strip().upper()
        except Exception:
            _env_name_gate = ""

        try:
            _qty_plan = float(sig.get("qty")) if sig.get("qty") is not None else 0.0
        except Exception:
            _qty_plan = 0.0

        try:
            _price_ref_plan = float(sig.get("price_ref")) if sig.get("price_ref") is not None else 0.0
        except Exception:
            _price_ref_plan = 0.0

        try:
            _notional_eur_plan = float(sig.get("notional_eur")) if sig.get("notional_eur") is not None else 0.0
        except Exception:
            _notional_eur_plan = 0.0

        _validation_errors = sig.get("validation_errors")
        _has_validation_errors = isinstance(_validation_errors, list) and len(_validation_errors) > 0

        _plan_has_minimum_exec_fields = (
            (_qty_plan > 0)
            or (_price_ref_plan > 0 and _notional_eur_plan > 0)
        )

        if _env_name_gate == "PREPROD":
            if _has_validation_errors or not _plan_has_minimum_exec_fields:
                skip_counts["invalid_execution_plan_signal"] += 1
                logger.info(
                    "[position_manager] skip invalid_execution_plan_signal symbol=%s qty=%s price_ref=%s notional_eur=%s validation_errors=%s",
                    symbol_raw, sig.get("qty"), sig.get("price_ref"), sig.get("notional_eur"), _validation_errors
                )
                continue


        entry_price = (
            sig.get("entry_price")
            or sig.get("price")
            or sig.get("fill_price")
            or sig.get("price_ref")
        )

        if entry_price is None:
            sp = sim_prices.get(symbol_norm)
            if sp is not None:
                try:
                    spv = float(sp)
                except Exception:
                    spv = None
                if spv is not None and spv > 0:
                    entry_price = spv

        if entry_price is None:
            _env_name_price = (os.environ.get("NSC_ENV") or "").strip().upper()
            if _env_name_price == "PREPROD":
                skip_counts["missing_entry_price_from_plan"] += 1
                logger.info(
                    "[position_manager] skip missing_entry_price_from_plan symbol=%s",
                    symbol_raw
                )
                continue

            try:
                last_close, _ = _get_price_and_atr_for_symbol(ohlcv_all, str(symbol_raw))
            except Exception:
                last_close = None
            if last_close is None:
                skip_counts["no_price_no_ohlcv"] += 1
                continue
            entry_price = last_close

        try:
            entry_price_f = float(entry_price)
        except Exception:
            entry_price_f = 0.0

        if entry_price_f <= 0:
            skip_counts["bad_entry_price"] += 1
            continue

        size = 0.0

        qty = sig.get("qty")
        notional_eur = sig.get("notional_eur")

        try:
            qty_f = float(qty) if qty is not None else 0.0
        except Exception:
            qty_f = 0.0

        if qty_f > 0:
            size = qty_f
        elif notional_eur is not None:
            try:
                notional_f = float(notional_eur)
            except Exception:
                notional_f = 0.0
            if notional_f > 0:
                size = (notional_f / entry_price_f)
        else:
            try:
                base_size = float(sig.get("size", sig.get("amount", 0.0) or 0.0) or 0.0)
            except Exception:
                base_size = 0.0
            size = base_size * max(0.0, size_multiplier)

        if size <= 0:
            skip_counts["size_le_0"] += 1
            logger.info(
                "[position_manager] skip size_le_0 symbol=%s entry_price=%s notional_eur=%s size_multiplier=%s",
                symbol_raw, entry_price_f, notional_eur, size_multiplier
            )
            continue

        pos = {
            "symbol": symbol_raw,
            "side": side,
            "size": float(size),
            "remaining_size": float(size),
            "entry_price": float(entry_price_f),
            "opened_at": now_ts,
            "risk_flag": risk_flag,
            "risk_score": risk.get("risk_score"),
            "size_multiplier": float(size_multiplier),
            "soft_veto": soft_veto,
            "hard_veto": hard_veto,
            "source": (sig.get("source") or src or "unknown"),
            "strategy": sig.get("strategy"),
            "meta_score": sig.get("meta_score"),

            # RC2 Meta Decision Lineage V1.
            "meta_score_pro": sig.get("meta_score_pro"),
            "meta_rank": sig.get("meta_rank"),
            "meta_verdict": sig.get("meta_verdict"),
            "meta_recommended": sig.get("meta_recommended"),
            "meta_execution_gate": sig.get("meta_execution_gate"),
            "execution_eligible": sig.get("execution_eligible"),
            "execution_confirmed": sig.get("execution_confirmed"),
            "decision_chg_24h": sig.get("decision_chg_24h"),
            "momentum_source": sig.get("momentum_source"),
            "execution_pair": sig.get("execution_pair"),
            "execution_source": sig.get("execution_source"),
            "cross_source_direction_conflict": sig.get("cross_source_direction_conflict"),
            "meta_risk_flags": list(sig.get("meta_risk_flags") or []),
            "notional_eur": notional_eur,
            "tp1_done": False,
            "tp2_done": False,
            "trailing_active": False,
            "realized_pnl": 0.0,
            "paper": bool(is_simulated),
            "execution_mode": "SIMULATED_ONLY" if is_simulated else "LIVE",
            "action": "SIMULATED_ONLY" if is_simulated else "LIVE",
            "blocked_by": blocked_by,
        }

        positions.append(pos)
        active_by_symbol[symbol_norm] = pos
        new_positions += 1

        logger.info(
            "[position_manager] opened symbol=%s size=%s entry_price=%s execution_mode=%s paper=%s",
            symbol_raw, size, entry_price_f, pos["execution_mode"], pos["paper"]
        )
    if skip_counts:
        logger.info("[position_manager] skip_counts_summary=%s", dict(skip_counts))

    # Dédup final + save
    positions = _dedup_positions_keep_latest(positions)

    open_pos_path = _path(data_dir, "trading", "open_positions.json")
    exit_events_path = _path(data_dir, "trading", "exit_events.json")    # NSC_PATCH: governance_hard_block_gate BEGIN
    # Source unique: _is_hard_block(data_dir, plan)
    try:
        hard_block_active, hb_reasons = _is_hard_block(data_dir, plan)
    except Exception:
        hard_block_active, hb_reasons = False, []

    _env_name = (os.environ.get("NSC_ENV") or "").strip().upper()

    if hard_block_active and _env_name != "PREPROD":
        logger.warning(
            "[position_manager] HARD BLOCK active => skip writes open_positions/exit_events. reasons=%s",
            hb_reasons,
        )
        return positions, exit_events, [], []

    if hard_block_active and _env_name == "PREPROD":
        logger.warning(
            "[position_manager] PREPROD override: hard block active but writes allowed. reasons=%s",
            hb_reasons,
        )

    # NSC_PATCH: governance_hard_block_gate END
    # Persist only active open positions.
    # Closed / zero-size paper positions are already represented in exit_events.json.
    positions = [
        pos for pos in positions
        if isinstance(pos, dict)
        and pos.get("closed") is not True
        and float(pos.get("remaining_size", pos.get("size", 0)) or 0) > 0
    ]

    # Mark-to-market active positions from latest spot prices.
    spot_path = _path(data_dir, "market", "crypto_spot_prices.json")
    spot_prices = load_json_file(spot_path, default={}) or {}

    for pos in positions:
        symbol = str(pos.get("symbol", "")).upper().replace("USDT", "")
        entry_price = float(pos.get("entry_price") or 0)
        remaining_size = float(pos.get("remaining_size", pos.get("size", 0)) or 0)
        last_price = spot_prices.get(symbol)

        if last_price is None or entry_price <= 0 or remaining_size <= 0:
            continue

        last_price = float(last_price)
        pos["last_price"] = last_price
        pos["unrealized_pnl"] = round((last_price - entry_price) * remaining_size, 6)
        pos["unrealized_pnl_pct"] = round(((last_price - entry_price) / entry_price) * 100, 4)

    save_json_file(open_pos_path, positions)
    nb_active = len([p for p in positions if float(p.get("remaining_size", p.get("size", 0.0)) or 0.0) > 0 and not p.get("closed", False)])
    logger.info("[position_manager] Positions ouvertes sauvegardées (%s, n=%d).", open_pos_path, nb_active)

    save_json_file(exit_events_path, exit_events)
    logger.info("[position_manager] Exit events sauvegardés (%s, total=%d).", exit_events_path, len(exit_events))

    return positions, exit_events, new_positions, new_exit_events

# ============================================================================
# Entrée principale
# ============================================================================

def main() -> None:
    _env_dd = (os.environ.get("NSC_DATA_DIR") or "").strip()
    data_dir = _env_dd or get_data_dir()
    if _env_dd:
        logger.info("[position_manager] NSC_DATA_DIR override active => DATA_DIR=%s", data_dir)

    logger.info("[position_manager] DATA_DIR=%s", data_dir)
    plan = _load_execution_plan(data_dir)

    # NSC_FIX_CLEAR_STALE_HARD_BLOCK_SKIP_WRITES_V1
    try:
        hard_block, hb_reasons = _is_hard_block(data_dir, plan)
    except Exception:
        hard_block, hb_reasons = False, []

    pm_state = _load_pm_state(data_dir)
    if not isinstance(pm_state, dict):
        pm_state = {}

    # Si aucun vrai hard block n'est actif, on purge immédiatement l'ancien flag
    if not hard_block and pm_state.get("hard_block_skip_writes") is True:
        pm_state.pop("hard_block_skip_writes", None)
        pm_state.pop("hard_block_reasons", None)
        _save_pm_state(data_dir, pm_state)
        logger.info("[position_manager] Cleared stale hard_block_skip_writes flag (no active hard block).")

    ok, reason = _is_final_safe_plan(plan)
    if not ok:
        _env_name = (os.environ.get("NSC_ENV") or "").strip().upper()

        _top_reasons = None
        _gov_reasons = None
        _hb_reasons = None
        _hb_active = False

        try:
            _hb_active, _hb_reasons = _is_hard_block(data_dir, plan)
        except Exception:
            _hb_active, _hb_reasons = False, []

        try:
            _top_reasons = plan.get("reasons") if isinstance(plan, dict) else None
            _gov = plan.get("governance") if isinstance(plan, dict) else None
            if isinstance(_gov, dict):
                _gov_reasons = _gov.get("kill_switch_reasons") or _gov.get("reasons")
                if bool(_gov.get("hard_block", False)):
                    if not isinstance(_top_reasons, list):
                        _top_reasons = [] if _top_reasons is None else [str(_top_reasons)]
                    _top_reasons = ["execution_plan.governance.hard_block=true"] + list(_top_reasons)
        except Exception:
            pass

        try:
            if _hb_active and _hb_reasons:
                if not isinstance(_top_reasons, list):
                    _top_reasons = [] if _top_reasons is None else [str(_top_reasons)]
                for r in _hb_reasons:
                    if r not in _top_reasons:
                        _top_reasons.insert(0, r)
        except Exception:
            pass

        if _env_name == "PREPROD":
            logger.warning(
                "[position_manager] PREPROD override: continue despite non-final-safe plan (reason=%s) writer=%s status=%s gov_source=%s hard_block=%s top_reasons=%s gov_reasons=%s",
                reason,
                plan.get("writer"),
                plan.get("status"),
                (plan.get("governance") or {}).get("source"),
                _hb_active,
                _top_reasons,
                _gov_reasons,
            )
        else:
            logger.warning(
                "[position_manager] Gate: skip (reason=%s) writer=%s status=%s gov_source=%s hard_block=%s top_reasons=%s gov_reasons=%s",
                reason,
                plan.get("writer"),
                plan.get("status"),
                (plan.get("governance") or {}).get("source"),
                _hb_active,
                _top_reasons,
                _gov_reasons,
            )
            return
    # --- Idempotence: do not re-apply on same execution_plan run_id ---
    state = _load_pm_state(data_dir)
    last_run_id = state.get("last_processed_run_id")
    if last_run_id and str(last_run_id) == str(plan.get("run_id")):
        pass  # auto-fix empty if
        # NSC_PATCH: force_reprocess_idempotence BEGIN
        _force = str(os.environ.get('NSC_FORCE_REPROCESS', '0')).strip().lower() in ('1','true','yes')
        _dry = str(os.environ.get('NSC_DRY_RUN', '0')).strip().lower() in ('1','true','yes')
        if _force and _dry:
            logger.warning('[position_manager] FORCE_REPROCESS enabled (DRY_RUN): bypass idempotence')
        else:
            logger.info("[position_manager] Idempotence: skip (run_id=%s already processed)", plan.get("run_id"))
        # NSC_PATCH: force_reprocess_idempotence END

        if not (_force and _dry):
            return

    # ─────────────────────────────────────────────
    positions = load_open_positions(data_dir)
    exit_events = load_exit_events(data_dir)
    logger.info("[position_manager] Positions ouvertes initiales: %d", len(positions))

    signals = load_signals(data_dir)

    # ─────────────────────────────────────────────
    # HF POLICY ENFORCEMENT
    # Source de vérité:
    # - PREPROD: execution_plan_simulated via load_signals()
    # - PROD:    execution_plan via load_signals()
    # On ne re-filtre plus ici.
    # ─────────────────────────────────────────────
    try:
        logger.info(
            "[position_manager] HF policy skipped on signals: n=%d (source of truth kept as-is)",
            len(signals) if isinstance(signals, list) else -1,
        )

        sized = load_execution_plan_orders(data_dir)
        if isinstance(sized, list):
            logger.info(
                "[position_manager] HF policy skipped on execution_plan orders: n=%d (source of truth kept as-is)",
                len(sized),
            )
    except Exception as exc:
        logger.exception("[position_manager] HF policy inspection failed (ignored): %s", exc)

    # ─────────────────────────────────────────────
    ohlcv_all = load_ohlcv(data_dir)
    if not ohlcv_all:
        logger.warning("[position_manager] Aucun OHLCV exploitable: %s", _path(data_dir, "market", "ohlcv_combined.json"))

    risk_by_symbol = load_risk_engine(data_dir)

    positions, exit_events, new_pos, new_exits = update_positions(
        data_dir=data_dir,
        positions=positions,
        exit_events=exit_events,
        signals=signals,
        risk_by_symbol=risk_by_symbol,
        ohlcv_all=ohlcv_all,
    )

    # --- Idempotence: persist last processed execution_plan run_id ---
    try:
        from datetime import datetime, timezone, timedelta
        _force = str(os.environ.get('NSC_FORCE_REPROCESS','0')).strip().lower() in ('1','true','yes')
        _dry   = str(os.environ.get('NSC_DRY_RUN','0')).strip().lower() in ('1','true','yes')
        _prev  = _load_pm_state(data_dir)
        if not isinstance(_prev, dict):
            _prev = {}

        _current_run = str(plan.get('run_id'))
        _prev_last   = _prev.get('last_processed_run_id')

        # Build next state by preserving previous fields/counters
        _next = dict(_prev)

        if _force and _dry and _prev_last is not None:
            pass  # auto-fix empty if
            # DRY_RUN replay: keep last_processed_run_id unchanged
            _next['last_processed_run_id'] = _prev_last
            # Track reprocess attempts
            _next['forced_reprocess_count'] = int(_prev.get('forced_reprocess_count') or 0) + 1
            _next['forced_reprocess_last_run_id_seen'] = _current_run
        else:
            _next['last_processed_run_id'] = _current_run

        _next['last_processed_generated_at'] = plan.get('generated_at')
        _next['saved_at'] = datetime.now(timezone.utc).isoformat()

        # NSC_FIX_DISABLE_STALE_HARD_BLOCK_SKIP_WRITES_V2
        try:
            _hb_now, _hb_reasons_now = _is_hard_block(data_dir, plan)
        except Exception:
            _hb_now, _hb_reasons_now = False, []

        if _hb_now:
            _save_pm_state(data_dir, {
                "hard_block_skip_writes": True,
                "hard_block_reasons": _hb_reasons_now,
            })
        else:
            logger.info("[position_manager] Skip writing hard_block_skip_writes=True because no active hard block.")
        logger.info("[position_manager] Idempotence state saved (run_id=%s)", plan.get('run_id'))
        if not _dry and not _force:
            logger.info("[position_manager][IDEMPOTENCE] commit run_id=%s", _current_run)

    except Exception:
        logger.exception("[position_manager] Failed to persist idempotence state")
    nb_active = len([p for p in positions if float(p.get("remaining_size", p.get("size", 0.0)) or 0.0) > 0 and not p.get("closed", False)])
    logger.info(
    "[position_manager] Update terminé: positions_actives=%d, new_positions=%d, new_exit_events=%d",
    len(positions) if isinstance(positions, list) else 0,
    len(new_pos) if isinstance(new_pos, list) else int(new_pos or 0),
    len(new_exits) if isinstance(new_exits, list) else int(new_exits or 0),
    )

if __name__ == "__main__":
    main()
