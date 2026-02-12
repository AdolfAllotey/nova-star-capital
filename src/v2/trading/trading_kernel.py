"""
# NSC_SAFE_STUB_EXECUTION_PLAN_V1_REPLACE_WRITES (replaced=1)
trading_kernel.py
---------------------------------
Noyau d'exécution "hedge fund light" pour Nova Star Capital.


# NSC_SAFE_STUB_EXECUTION_PLAN_V1
def _is_valid_external_plan(existing):
    if not isinstance(existing, dict):
        return False
    writer = existing.get('writer')
    status = existing.get('status')
    orders = existing.get('orders')
    if writer and writer != 'trading_kernel':
        if isinstance(orders, list) and len(orders) > 0 and status not in ('blocked', 'empty', 'error'):
            return True
    return False


Rôle :
  - Orchestrer une boucle de trading complète :
#       1) momentum_scoring       → calcule les meta-scores 0–100 par asset
#       2) signal_voting          → transforme en signaux (enter_long / watch / avoid)
#       3) capital_allocator      → calcule les poches et capital par trade
#       4) position_manager       → ouvre / met à jour / ferme les positions

  - Appliquer :
      * un kill-switch global (kill_switch.json)
      * des gardes de risque (risk_limits.json + daily_trading_feedback.json)

Ce module NE PASSE PAS d'ordres réels (préprod). Il pilote la logique
et écrit des JSON dans /data.
"""
from __future__ import annotations
import time

import secrets
from src.v2.utils.file_utils import load_json_file, save_json_file, get_data_dir




import os

# NSC_IMPORT_FILE_UTILS_TOPLEVEL_V1
# NSC_FIX_UNBOUND_LOAD_JSON_FILE_V1

from pathlib import Path
from typing import Any, Optional
from src.v2.utils.execution_ledger import append_execution_decision
from uuid import uuid4

from src.v2.governance.kill_switch import load_kill_switch
try:
    from src.v2.utils.logger import get_logger
except ImportError:  # pragma: no cover
    from src.v2.utils.logger import get_logger  # type: ignore

logger = get_logger("trading_kernel")

# NSC_STUB_HELPER_EXPORT_V1
# NSC_STUB_CALLS_ADD_LOGGER_V1
# NSC_STUB_CALLS_ADD_LOGGER_V3_SAFE
def _safe_write_stub_execution_plan(plan_path, stub_obj, logger=None):
    """Write a minimal execution_plan.json stub safely (no delete).
    - Ensures the file exists
    - Keeps it JSON-valid
    - Uses file_utils.save_json_file for atomic-ish writes
    """
    try:
        from src.v2.utils.file_utils import save_json_file, load_json_file
    except Exception:
        # fallback: local imports already present in module in most cases
        save_json_file = globals().get("save_json_file")
        load_json_file = globals().get("load_json_file")

    _log = logger or globals().get("logger", None)

    try:
        existing = {}
        if load_json_file:
            existing = load_json_file(str(plan_path), default={}) or {}
    except Exception:
        existing = {}

    # preserve a few fields if present
    merged = {}
    # NSC_PATCH: ensure execution_plan writer
    try:
        if isinstance(merged, dict) and merged.get('writer') is None:
            merged['writer'] = 'execution_engine_pro'
    except Exception:
        pass
    try:
        merged.update(existing if isinstance(existing, dict) else {})
    except Exception:
        pass
    try:
        merged.update(stub_obj if isinstance(stub_obj, dict) else {})
    except Exception:
        pass

    # hard safety defaults
    merged.setdefault("status", "cleared")
    merged.setdefault("note", "autocleared_blocked_plan")
    merged.setdefault("orders", [])
    merged.setdefault("governance", {})
    if isinstance(merged.get("governance"), dict):
        merged["governance"].setdefault("reasons", [])
        merged["governance"].setdefault("kill_switch_reasons", [])

    try:
        if save_json_file:
            save_json_file(str(plan_path), merged)
        else:
            # very last resort
            import json
            Path(plan_path).write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        if _log:
            _log.info("[trading_kernel] stub execution_plan.json written: %s (status=%s note=%s)", plan_path, merged.get("status"), merged.get("note"))
    except Exception:
        if _log:
            _log.exception("[trading_kernel] failed to write stub execution_plan.json")

# ---------------------------------------------------------------------------
# Paths / DATA_DIR
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[3]  # /opt/nsc/app
DATA_DIR = Path(os.getenv("NSC_DATA_DIR", str(ROOT_DIR / "data"))).resolve()

TRADING_DIR = DATA_DIR / "trading"
ANALYSIS_DIR = DATA_DIR / "analysis"
MARKET_DIR = DATA_DIR / "market"
REPORTS_DIR = DATA_DIR / "reports"

TRADING_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
MARKET_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

KILL_SWITCH_FILE = TRADING_DIR / "kill_switch.json"
RISK_LIMITS_FILE = TRADING_DIR / "risk_limits.json"
DAILY_FEEDBACK_FILE = REPORTS_DIR / "daily_trading_feedback.json"
ORCHESTRATOR_STATE_FILE = DATA_DIR / "telemetry" / "orchestrator_pro.json"
SIGNAL_QUALITY_FILE = ANALYSIS_DIR / "signal_quality_engine_pro.json"
SIGNAL_QUALITY_HARD_BLOCK_SCORE = float(45.0)  # score < => stop trading

logger.info(
    "[trading_kernel] ROOT_DIR=%s, DATA_DIR=%s", ROOT_DIR, DATA_DIR
)

# SECURITY: forbid real execution unless explicitly allowed (env-aware)
_dry = str(os.environ.get('NSC_DRY_RUN','1')).strip().lower() in ('1','true','yes')
_env = (os.environ.get('NSC_ENV') or os.environ.get('ENV') or 'PREPROD').strip().upper()
_allow = str(os.environ.get('NSC_ALLOW_DRYRUN0','0')).strip().lower() in ('1','true','yes')

if (not _dry) and (_env != 'PROD') and (not _allow):
    logger.critical('[SECURITY][FATAL] DRY_RUN=0 is forbidden when env=%s (set NSC_ENV=PROD or NSC_ALLOW_DRYRUN0=1 to override)', _env)
    raise SystemExit(2)

if not _dry:
    logger.warning('[SECURITY] DRY_RUN=0 enabled (env=%s, override=%s)', _env, _allow)
else:
    logger.warning('[SECURITY] DRY_RUN enforced — no real execution possible (env=%s)', _env)
# ---------------------------------------------------------------------------
# file_utils fallback
# ---------------------------------------------------------------------------

try:
    # NSC_FIX_UNBOUND_LOAD_JSON_FILE_V1
    from src.v2.utils.file_utils import load_json_file, save_json_file
except Exception:  # pragma: no cover
    load_json_file = None
    save_json_file = None

    import json

    def _load_json(path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception(
                "[trading_kernel] Erreur lors du chargement JSON: %s", path
            )
            return default

    def _save_json(path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                import json as _json

                _json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.exception(
                "[trading_kernel] Erreur lors de l'écriture JSON: %s", path
            )
else:

    def _load_json(path: Path, default: Any = None) -> Any:
        return load_json_file(str(path), default=default)

    def _save_json(path: Path, data: Any) -> None:
        save_json_file(str(path), data)


# ---------------------------------------------------------------------------
# Kill-switch
# ---------------------------------------------------------------------------

def _apply_orchestrator_risk_limits() -> None:
    """
    Propulse l'état runtime de l'orchestrator (mode/risk_mode/size_factor)
    dans data/trading/risk_limits.json, sans écraser la config existante.
    """
    st = _load_json(ORCHESTRATOR_STATE_FILE, default={})
    if not isinstance(st, dict):
        logger.warning("[trading_kernel] orchestrator_pro.json invalide -> skip")
        return

    size_factor = st.get("size_factor", None)
    mode = st.get("mode", None)
    risk_mode = st.get("risk_mode", None)

    # Rien à appliquer
    if size_factor is None and mode is None and risk_mode is None:
        return

    cfg = _load_json(RISK_LIMITS_FILE, default={})
    if not isinstance(cfg, dict):
        cfg = {}

    # Merge non destructif
    if size_factor is not None:
        try:
            cfg["size_factor"] = float(size_factor)
        except Exception:
            logger.warning("[trading_kernel] size_factor invalide: %r", size_factor)

    if mode:
        cfg["mode"] = str(mode)

    if risk_mode:
        cfg["risk_mode"] = str(risk_mode)

    _save_json(RISK_LIMITS_FILE, cfg)
    logger.info(
        "[trading_kernel] risk_limits mis à jour depuis orchestrator: mode=%s risk_mode=%s size_factor=%s",
        cfg.get("mode"), cfg.get("risk_mode"), cfg.get("size_factor")
    )

def is_kill_switch_enabled() -> bool:
    """Compat: retourne True si kill-switch activé (enabled)."""
    try:
        from src.v2.governance.kill_switch import load_kill_switch
        ks = load_kill_switch(os.path.join(str(get_data_dir()), "trading", "kill_switch.json"))
        if ks.enabled:
            logger.warning("[trading_kernel] Kill-switch ENABLED (source=%s reasons=%s)", ks.source, ks.reasons or [])
        return bool(ks.enabled)
    except Exception:
        # fallback legacy
        data = _load_json(KILL_SWITCH_FILE, default={})
        if not isinstance(data, dict):
            return False
        enabled = bool(data.get("enabled", False))
        if enabled:
            logger.warning("[trading_kernel] Kill-switch ENABLED (legacy)")
        return enabled
def set_kill_switch(enabled: bool, reason: str = "") -> None:
    payload = {
        "enabled": bool(enabled),
        "reason": reason,
    }
    _save_json(KILL_SWITCH_FILE, payload)
    logger.info(
        "[trading_kernel] Kill-switch mis à jour: enabled=%s, reason=%s",
        enabled,
        reason,
    )


# ---------------------------------------------------------------------------
# Risk guards (risk_limits + daily_feedback)
# ---------------------------------------------------------------------------

def _load_risk_limits() -> dict:
    cfg = _load_json(RISK_LIMITS_FILE, default={})
    if not isinstance(cfg, dict):
        cfg = {}
    return cfg


def _load_daily_feedback() -> dict:
    fb = _load_json(DAILY_FEEDBACK_FILE, default={})
    if not isinstance(fb, dict):
        return {}
    return fb


def _check_risk_guards() -> bool:
    """
    Vérifie les gardes de risque "soft" avant de lancer une boucle de trading.

    risk_limits.json attendu :
    {
      "enable_meta_score_guard": true,
      "min_meta_score_nsc": 50.0,
      "enable_daily_drawdown_guard": true,
      "max_daily_loss_eur": 500.0,
      "enable_hard_risk_off_guard": true
    }

    daily_trading_feedback.json doit contenir idéalement :
    {
      "meta_score_nsc": ...,
      "realized_pnl_today": ...,
      "regime": "...",
      "risk_mode": "..."
      ...
    }
    """
    cfg = _load_risk_limits()
    fb = _load_daily_feedback()

    meta_score = float(fb.get("meta_score_nsc", 0.0)) if fb else 0.0
    realized_today = float(fb.get("realized_pnl_today", 0.0)) if fb else 0.0
    regime = str(fb.get("regime", "")).lower() if fb else ""
    risk_mode = str(fb.get("risk_mode", "")).lower() if fb else ""

    # 1) Meta-score guard
    if cfg.get("enable_meta_score_guard", False):
        min_meta = float(cfg.get("min_meta_score_nsc", 0.0))
        if meta_score < min_meta:
            logger.warning(
                "[trading_kernel] Guard meta_score_nsc active: meta_score=%.2f < %.2f → boucle annulée.",
                meta_score,
                min_meta,
            )
            return False

    # 2) Daily drawdown guard
    if cfg.get("enable_daily_drawdown_guard", False):
        max_loss = float(cfg.get("max_daily_loss_eur", 0.0))
        if realized_today < -abs(max_loss):
            logger.warning(
                "[trading_kernel] Guard daily_drawdown active: realized_pnl_today=%.2f < -%.2f → boucle annulée.",
                realized_today,
                abs(max_loss),
            )
            return False

    # 3) Hard risk_off guard
    if cfg.get("enable_hard_risk_off_guard", False):
        if regime.startswith("bear") or risk_mode == "risk_off":
            logger.warning(
                "[trading_kernel] Guard hard risk_off active: regime=%s, risk_mode=%s → boucle annulée.",
                regime,
                risk_mode,
            )
            return False

    return True


# ---------------------------------------------------------------------------
# Signal Quality gate (Signal Quality Engine Pro)
# ---------------------------------------------------------------------------

def _check_signal_quality_gate() -> bool:
    """
    Gate runtime: bloque la boucle si la qualité de signal est trop faible.
    Source de vérité du threshold: data/trading/risk_limits.json (signal_quality_hard_block_score).
    Bloque si:
      - hard_block=True dans signal_quality_engine_pro.json
      - flag == "hard_block"
      - score < threshold
    """
    # Load signal quality
    sq = _load_json(SIGNAL_QUALITY_FILE, default={})
    if not isinstance(sq, dict):
        return True  # fail-open

    flag = str(sq.get("flag") or "neutral")
    try:
        score = float(sq.get("score", 100.0) or 0.0)
    except Exception:
        score = 100.0

    hard_block = bool(sq.get("hard_block", False))

    # Load threshold from risk_limits
    cfg_rl = _load_json(RISK_LIMITS_FILE, default={})
    if not isinstance(cfg_rl, dict):
        cfg_rl = {}
    try:
        threshold = float(cfg_rl.get("signal_quality_hard_block_score", 45.0))
    except Exception:
        threshold = 45.0

    logger.info(
        "[trading_kernel] signal_quality gate: flag=%s score=%.2f hard_block=%s",
        flag, score, hard_block
    )

    should_block = False
    reason = None

    if hard_block:
        should_block = True
        reason = "hard_block=True"
    elif flag == "hard_block":
        should_block = True
        reason = "flag=hard_block"
    elif score < threshold:
        should_block = True
        reason = f"score<threshold ({score:.2f}<{threshold:.2f})"

    if should_block:
        logger.warning(
            "[trading_kernel] Boucle annulée par Signal Quality: flag=%s score=%.2f hard_block=%s (threshold=%.2f) reason=%s",
            flag, score, hard_block, threshold, reason
        )
        return False

    return True
def _safe_len_json_list(path):
    try:
        # NSC_FIX_UNBOUND_LOAD_JSON_FILE_V1
        data = load_json_file(path, default=[])
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0

def _safe_read_json(path, default=None):
    # === NSC_INIT_COUNTERS_V2 ===
    _nsc_hard_blocked = 0
    try:
        # NSC_FIX_UNBOUND_LOAD_JSON_FILE_V1
        return load_json_file(path, default=default)
    except Exception:
        return default


def _check_orchestrator_gate() -> tuple[bool, bool]:
    """
    Gate runtime (orchestrator-first):
      - return (ok, orch_available)
      - ok=False => stop trading
      - orch_available=False => fail-open + allow SQ fallback gate
    """
    try:
        st = _load_json(ORCHESTRATOR_STATE_FILE, default=None)
    except Exception:
        return (True, False)

    if not isinstance(st, dict):
        return (True, False)  # orchestrator indisponible => fail-open + SQ fallback

    can_trade = bool(st.get("can_trade", True))
    mode = str(st.get("mode") or "unknown")
    reasons = st.get("reasons", []) or []
    severity = str(st.get("severity") or "info")

    if not can_trade:
        logger.warning(
            "[trading_kernel] Boucle annulée par Orchestrator gate: can_trade=False mode=%s severity=%s reasons=%s",
            mode, severity, reasons
        )
        return (False, True)

    return (True, True)

def run_once(max_new_positions: Optional[int] = None) -> None:

    # 0) Kill-switch (single source of truth)
    ks = load_kill_switch(os.path.join(str(get_data_dir()), "trading", "kill_switch.json"))

    if ks.hard_block:
        logger.warning("[trading_kernel] HARD BLOCK active -> no trading. %s", ks.explain())
        try:
            plan_path = TRADING_DIR / "execution_plan.json"
            stub = {
                "writer": "trading_kernel",
                "status": "blocked",
                "note": "kill_switch_hard_block",
                "orders": [],
                "reasons": ["kill_switch:hard_block"],
                "kill_switch": {
                    "enabled": ks.enabled,
                    "hard_block": ks.hard_block,
                    "soft_block": getattr(ks, "soft_block", False),
                    "mode": ks.mode,
                    "source": ks.source,
                    "reasons": ks.reasons,
                    "updated_at": ks.updated_at,
                },
            }
            _safe_write_stub_execution_plan(plan_path, stub, logger=logger)
        except Exception:
            logger.exception("[trading_kernel] failed to write blocked execution_plan stub")
        return

    if ks.enabled and getattr(ks, "soft_block", False):
        logger.warning("[trading_kernel] SOFT BLOCK active (advisory). %s", ks.explain())
    """
    Exécute une boucle complète "hedge fund light" :

#       0) Vérifie kill_switch + guards de risque
#       1) momentum_scoring
#       2) signal_voting
#       3) capital_allocator
#       4) position_manager

    max_new_positions : réservé pour usage futur (limiter le nombre
    de nouvelles positions par cycle).
    """
    # === NSC_INIT_HARD_BLOCKED_RUN_ONCE_V1 ===
    _nsc_hard_blocked = False
    # 0) Kill-switch & risk guards
    if is_kill_switch_enabled():
        logger.warning("[trading_kernel] Boucle annulée car le kill-switch est activé.")
        return

    # Sync risk_limits depuis orchestrator (si dispo) avant guards/sizing
    _apply_orchestrator_risk_limits()

    # Orchestrator gate (source de vérité runtime)
    ok, orch_available = _check_orchestrator_gate()
    if not ok:
        return

    # Signal Quality gate (fallback uniquement si orchestrator indisponible)
    if not orch_available:
        if not _check_signal_quality_gate():
            logger.warning("[trading_kernel] Boucle annulée par Signal Quality Engine (score<threshold ou hard_block).")
            # NSC_EXECUTION_LEDGER_BLOCKED_SQ_FIX_V1
            try:
                # import os (moved to module-level; avoid UnboundLocalError)
                _env_val = str(os.environ.get('NSC_ENV') or os.environ.get('ENV') or 'UNKNOWN')
                _dry_val = str(os.environ.get('NSC_DRY_RUN', '0')).strip().lower() in ('1','true','yes')
                append_execution_decision({
                    'run_id': run_id,
                    'decision': 'BLOCKED',
                    'blocked_by': 'signal_quality_gate',
                    'reason': (reason if 'reason' in locals() else 'signal_quality_gate'),
                    'env': _env_val,
                    'dry_run': _dry_val,
                })
            except Exception:
                pass
            return

    # Imports locaux  ok, orch_available = _check_orchestrator_gate()
    if not ok:
        return

    # Signal Quality gate (sécurité supplémentaire / fallback)
    if not _check_signal_quality_gate():
        logger.warning("[trading_kernel] Boucle annulée par Signal Quality Engine (score<threshold ou hard_block).")
        return

    # Imports locaux pour éviter les cycles d'import
    from src.v2.analysis.momentum_scoring import main as momentum_main
    from src.v2.analysis.signal_voting import main as signal_voting_main
    from src.v2.analysis.capital_allocator import main as capital_allocator_main
    from src.v2.trading.position_manager import main as position_manager_main

    logger.info("[trading_kernel] Démarrage de la boucle hedge fund light (run_once).")
    # NSC_RUN_ID_ENV_DRY_V1
    from datetime import datetime, timezone
    # run_id unique par cycle (ms UTC) pour corrélation ledger / state / events
    # NSC_RUN_ONCE_RUN_ID_SOURCE_V1
    # run_id must come from NSC_RUN_ID when provided (manual debugging / ledger alignment).
    try:
        _rid_env = str(os.environ.get('NSC_RUN_ID') or '').strip()
    except Exception:
        _rid_env = ''
    if _rid_env:
        run_id = _rid_env
    else:
        run_id = f"{int(datetime.now(timezone.utc).timestamp()*1000)}-{uuid4().hex[:8]}"
    # contexte env/dry_run pour le ledger
    _env = str(os.environ.get('NSC_ENV') or os.environ.get('ENV') or 'UNKNOWN')
    _dry = str(os.environ.get('NSC_DRY_RUN','0')).strip().lower() in ('1','true','yes')
    # NSC_PREPROD_ALIGNMENT_STEP2_V1
    # Propagation contexte vers les modules appelés (plan/ledger doivent partager le même run_id)
    # NSC_RUN_ID_NO_OVERWRITE_WHEN_KEEP_V1
    try:
        _keep = str(os.environ.get('NSC_KEEP_RUN_ID','0')).strip().lower() in ('1','true','yes')
    except Exception:
        _keep = False
    try:
        _rid_existing = str(os.environ.get('NSC_RUN_ID') or '').strip()
    except Exception:
        _rid_existing = ''
    if not (_keep and _rid_existing):
        # NSC_GUARD_ALL_ENV_RUN_ID_WRITES_V1
        try:
            _keep = str(os.environ.get('NSC_KEEP_RUN_ID','0')).strip().lower() in ('1','true','yes')
        except Exception:
            _keep = False
        try:
            _rid_existing = str(os.environ.get('NSC_RUN_ID') or '').strip()
        except Exception:
            _rid_existing = ''
        if not (_keep and _rid_existing):
            os.environ['NSC_RUN_ID'] = str(run_id)
    os.environ['NSC_ENV'] = str(_env)
    os.environ['NSC_DRY_RUN'] = '1' if _dry else '0'



    # Étape 1 : momentum
    logger.info("[trading_kernel] Étape 1/4 : momentum_scoring")
    try:
        momentum_main()
    except Exception:
        logger.exception("[trading_kernel] Erreur lors de momentum_scoring.main()")
        return

    # Étape 2 : signal voting
    logger.info("[trading_kernel] Étape 2/4 : signal_voting")
    logger.info("[trading_kernel] Étape 2.1/4 : position_sizing")
    try:
        import subprocess, sys
        subprocess.run([sys.executable, '-m', 'src.v2.analysis.position_sizing', '--data-dir', str(DATA_DIR)], check=True)
    except Exception:
        logger.exception("[trading_kernel] position_sizing failed")
    logger.info("[trading_kernel] Étape 2.2/4 : execution_engine_pro")
    try:
        import subprocess, sys
        subprocess.run([sys.executable, '-m', 'src.v2.analysis.execution_engine_pro', '--data-dir', str(DATA_DIR)], check=True)
    except Exception:
        logger.exception("[trading_kernel] execution_engine_pro failed")

    try:
        signal_voting_main()
    except Exception:
        logger.exception("[trading_kernel] Erreur lors de signal_voting.main()")
        return



    # Étape 2.4/4 : risk_engine_pro (global + per-asset compat)
    try:
        # NSC_PREPROD_ALIGNMENT_STEP2_V1
        # Étape 2.33/4 : market_regime_detector (input direct de risk_engine_pro)
        logger.info("[trading_kernel] Étape 2.33/4 : market_regime_detector")

        if os.getenv("NSC_SKIP_MARKET_REGIME_DETECTOR", "0") == "1":
            logger.warning("[trading_kernel] NSC_SKIP_MARKET_REGIME_DETECTOR=1 => skipping market_regime_detector")
        else:
            import subprocess, sys
            from pathlib import Path

            snapshot = Path(os.getenv("NSC_MARKET_SNAPSHOT", str(DATA_DIR / "analysis" / "market_snapshot.json")))
            out_path = Path(str(DATA_DIR / "analysis" / "market_regime_detector.json"))

            logger.info("[trading_kernel] market_regime_detector CLI: snapshot=%s out=%s", snapshot, out_path)

            # Exécute le module en CLI (argparse attend --snapshot)
            subprocess.run(
                [
                    sys.executable,
                    "-m", "src.v2.analysis.market_regime_detector",
                    "--snapshot", str(snapshot),
                    "--out", str(out_path),
                ],
                check=True,
            )

    except Exception:
        logger.exception("[trading_kernel] Erreur lors de l'étape market_regime_detector (CLI) / wrapper risk_engine_pro")
        return

    logger.info("[trading_kernel] Étape 3/4 : capital_allocator")
    try:
        capital_allocator_main()
    except Exception:
        logger.exception("[trading_kernel] Erreur lors de capital_allocator.main()")
        return

    # Étape 4 : position manager
    logger.info("[trading_kernel] Étape 4/4 : position_manager")
    try:
        # max_new_positions pas encore utilisé, mais gardé pour évolutions futures
        position_manager_main()
    except Exception:
        logger.exception("[trading_kernel] Erreur lors de position_manager.main()")
        return


    # ───────────────────────────────────────────────────────────
    # Kernel Run Summary (logs lisibles en timer)
    # ───────────────────────────────────────────────────────────
    signal_candidates_path = DATA_DIR / "analysis" / "signal_candidates.json"
    sized_signals_path = DATA_DIR / "trading" / "sized_signals.json"
    execution_plan_path = DATA_DIR / "trading" / "execution_plan.json"
    # NSC_AUTO_CLEAR_BLOCKED_EXEC_PLAN_EARLY_V1
    # If previous execution_plan.json was blocked by risk_engine_pro, and risk is now cleared,
    # delete the old file BEFORE any other guards/early-returns so we can regenerate in the same run.
    try:
        if execution_plan_path.exists():
            _prev = _safe_read_json(execution_plan_path, default={}) or {}
            _prev_note = str(_prev.get('note') or '')
            # NSC_AUTO_CLEAR_EARLY_NOOP_IF_ALREADY_CLEARED_V1
            try:
                _prev_status = str(_prev.get('status') or '')
            except Exception:
                _prev_status = ''
            if _prev_status == 'cleared' or _prev_note.startswith('autocleared_'):
                # Already handled by a previous run; BEFORE_EXEC will handle overwrite when needed.
                pass
            _prev_hb = bool((_prev.get('governance') or {}).get('hard_block') is True)
            _risk_now = _safe_read_json(DATA_DIR / 'analysis' / 'risk_engine_pro.json', default={}) or {}
            _risk_hb = bool(_risk_now.get('hard_block') is True)
            _risk_flag = str(_risk_now.get('flag') or '')
            if (_prev_hb or _prev_note.startswith('blocked_by_risk_engine_pro')) and (not _risk_hb) and _risk_flag:
                # NSC_DISABLE_AUTO_CLEAR_EARLY_V1_SAFE
                # AUTO_CLEAR(EARLY) is intentionally disabled; AUTO_CLEAR(BEFORE_EXEC) handles stub+overwrite.
                logger.info('[trading_kernel] AUTO_CLEAR(EARLY) skipped (handled by BEFORE_EXEC) prev_note=%s prev_hard_block=%s risk_flag=%s', _prev_note, _prev_hb, _risk_flag)
    except Exception:
        logger.exception('[trading_kernel] AUTO_CLEAR(EARLY) execution_plan guard failed')


    capital_alloc_path = DATA_DIR / "trading" / "capital_allocation.json"
    risk_path = DATA_DIR / "analysis" / "risk_engine_pro.json"
    sq_path = DATA_DIR / "analysis" / "signal_quality_engine_pro.json"
    sq = _safe_read_json(sq_path, default={}) or {}
    sq_flag = sq.get("flag")
    sq_score = sq.get("score")

    nb_raw = _safe_len_json_list(signal_candidates_path)
    nb_sized = _safe_len_json_list(sized_signals_path)

    exec_plan = _safe_read_json(execution_plan_path, default={}) or {}
    orders = exec_plan.get("orders", [])
    nb_orders = len(orders) if isinstance(orders, list) else 0

    cap = _safe_read_json(capital_alloc_path, default={}) or {}
    capital_per_trade = cap.get("capital_per_trade")
    max_positions = cap.get("max_positions") or cap.get("max_concurrent_positions")
    risk = _safe_read_json(risk_path, default={}) or {}
    risk_flag = risk.get("global_flag") or risk.get("flag")

    logger.info(
    "[trading_kernel][SUMMARY] raw=%s sized=%s orders=%s capital_per_trade=%s max_positions=%s risk=%s signal_quality=%s/%s",
    nb_raw, nb_sized, nb_orders, capital_per_trade, max_positions, risk_flag, sq_flag, sq_score
    )

    logger.info("[trading_kernel] Boucle hedge fund light terminée.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    # NSC_RUN_ID_PROPAGATION_V3_MANUAL_FIRST
    # Default: generate a fresh run_id for each invocation.
    # Manual override: NSC_KEEP_RUN_ID=1 + NSC_RUN_ID=<value> => use it as-is (e.g. manual-xxx).
    try:
        _keep = str(os.environ.get('NSC_KEEP_RUN_ID','0')).strip().lower() in ('1','true','yes')
    except Exception:
        _keep = False
    try:
        _rid_env = str(os.environ.get('NSC_RUN_ID') or '').strip()
    except Exception:
        _rid_env = ''
    if _keep and _rid_env:
        run_id = _rid_env
    else:
        run_id = str(int(time.time() * 1000)) + '-' + secrets.token_hex(4)
    # NSC_RUN_ID_NO_OVERWRITE_WHEN_KEEP_V1
    try:
        _keep = str(os.environ.get('NSC_KEEP_RUN_ID','0')).strip().lower() in ('1','true','yes')
    except Exception:
        _keep = False
    try:
        _rid_existing = str(os.environ.get('NSC_RUN_ID') or '').strip()
    except Exception:
        _rid_existing = ''
    if not (_keep and _rid_existing):
        # NSC_GUARD_ALL_ENV_RUN_ID_WRITES_V1
        try:
            _keep = str(os.environ.get('NSC_KEEP_RUN_ID','0')).strip().lower() in ('1','true','yes')
        except Exception:
            _keep = False
        try:
            _rid_existing = str(os.environ.get('NSC_RUN_ID') or '').strip()
        except Exception:
            _rid_existing = ''
        if not (_keep and _rid_existing):
            os.environ['NSC_RUN_ID'] = str(run_id)
    run_once()


if __name__ == "__main__":
    main()
