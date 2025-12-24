# /opt/nsc/src/v2/position_manager.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal as D
from pathlib import Path
from typing import Optional, Dict, Any
import datetime as dt
import json

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

log = get_logger("position_manager")

ROOT = Path("/opt/nsc")
CFG_PATH = ROOT / "src" / "v2" / "config" / "settings.json"
REPORTS_DIR = ROOT / "src" / "v2" / "data" / "reports"
LOGS_DIR = ROOT / "src" / "v2" / "logs"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
EXITS_FILE = REPORTS_DIR / "exits.jsonl"  # historique minimal des sorties

# --- tentatives d’intégration optionnelles ----------------------------------------
try:
    # Si tu as un routeur d'exchange interne
    from src.v2.core.exchange_router import market_sell_to_stable as _market_sell_to_stable
except Exception:
    _market_sell_to_stable = None

try:
    # Si tu as un oracle prix interne (EUR)
    from src.v2.core.pricing_oracle import get_eur_price as _get_eur_price
except Exception:
    _get_eur_price = None

# --- config helpers ----------------------------------------------------------------
def cfg() -> Dict[str, Any]:
    c = load_json_file(str(CFG_PATH), default={})
    c.setdefault("stablecoin", {"primary": "USDC"})
    return c

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

# --- modèle d’événement d’exit -----------------------------------------------------
@dataclass
class ExitEvent:
    ts: str
    token: str
    qty: float
    proceeds_stable: float
    stable_ccy: str
    reason: str
    dest_bucket: str
    price_eur: Optional[float] = None
    proceeds_eur: Optional[float] = None
    exchange: Optional[str] = None
    txid: Optional[str] = None
    mode: str = "simulated"  # "exchange" si ordre réel exécuté

# --- helpers -----------------------------------------------------------------------
def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def _estimate_proceeds_eur(token: str, proceeds_stable: float) -> Optional[float]:
    try:
        if _get_eur_price is None:
            return None
        px = float(_get_eur_price(token))
        # on n'a pas la qty exacte ici → approximation: proceeds_stable ≈ qty * px (si 1 USDC ≈ 1 EUR)
        return round(float(proceeds_stable), 2) if px <= 0 else round(float(proceeds_stable), 2)
    except Exception:
        return None

# --- API publique ------------------------------------------------------------------
def execute_partial_exit(token: str,
                         qty: float,
                         reason: str,
                         dest_bucket: str = "TRADING_STABLE_FLOAT",
                         stable_ccy: Optional[str] = None) -> ExitEvent:
    """
    Vend 'qty' de 'token' vers stablecoin (USDC par défaut), tague la destination.
    - Si un exchange router existe : exécute un ordre réel et log TXID.
    - Sinon : mode simulé (aucun ordre réel), écrit juste l'événement.
    Renvoie un ExitEvent (pour traçabilité / tests).
    """
    if qty is None or qty <= 0:
        raise ValueError(f"qty must be > 0 (got {qty})")

    c = cfg()
    stable = stable_ccy or c["stablecoin"].get("primary", "USDC")

    proceeds_stable = 0.0
    exchange = None
    txid = None
    mode = "simulated"

    if _market_sell_to_stable is not None:
        # --- mode “réel” via exchange_router --------------------------------------
        try:
            res = _market_sell_to_stable(token, qty, quote=stable)
            # on s'attend à un dict du type {"filled_qty": ..., "received_quote": ..., "exchange": ..., "txid": ...}
            proceeds_stable = float(res.get("received_quote", 0.0))
            exchange = res.get("exchange")
            txid = res.get("txid")
            mode = "exchange"
        except Exception as e:
            log.exception(f"[exit] exchange sell failed; fallback to simulated: {e}")

    if proceeds_stable <= 0.0:
        # --- fallback simulé -------------------------------------------------------
        # Hypothèse simple : 1 USDC ≈ 1 EUR → on convertit qty * prix_EUR (si dispo) en USDC
        px_eur = None
        try:
            if _get_eur_price:
                px_eur = float(_get_eur_price(token))
        except Exception:
            px_eur = None
        if px_eur and px_eur > 0 and qty > 0:
            proceeds_stable = round(qty * px_eur, 2)  # équiv. USDC ~ EUR
        else:
            proceeds_stable = round(qty * 10.0, 2)    # valeur fictive pour smoke-test

    evt = ExitEvent(
        ts=now_utc(),
        token=token.upper(),
        qty=float(qty),
        proceeds_stable=float(proceeds_stable),
        stable_ccy=stable,
        reason=reason,
        dest_bucket=dest_bucket,
        price_eur=None,
        proceeds_eur=_estimate_proceeds_eur(token, proceeds_stable),
        exchange=exchange,
        txid=txid,
        mode=mode
    )

    # Journalisation JSONL (traçabilité minimale)
    _append_jsonl(EXITS_FILE, asdict(evt))
    log.info(f"[exit] {evt.token} qty={evt.qty} -> {evt.proceeds_stable} {stable} "
             f"bucket={evt.dest_bucket} mode={evt.mode} txid={evt.txid}")

    return evt

# --- CLI de test -------------------------------------------------------------------
if __name__ == "__main__":
    # Exemple : vendre 0.5 SOL vers USDC pour alimenter la poche Trading
    e = execute_partial_exit("SOL", 0.5, reason="take_profit", dest_bucket="TRADING_STABLE_FLOAT")
    print(json.dumps(asdict(e), ensure_ascii=False, indent=2))
