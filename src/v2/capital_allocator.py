# src/v2/capital_allocator.py
# Nova Star Capital — V2 Préproduction
# Allocation dynamique, fiscalité, BFR, sécurité, réinvestissement trading
# Compatible avec generate_trade_simulation.py & position_manager.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import datetime as dt

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import save_json_file, load_json_file

log = get_logger("capital_allocator")

# ---------------------------------------------------------------------
# 🔧 PARAMÈTRES GLOBAUX — V2 PRÉPROD
# ---------------------------------------------------------------------

THRESHOLD_EQUITY_EUR = 5000.0        # Seuil d’activation des règles
TAX_RATE = 0.25                      # Fiscalité IS 25%
REINVEST_TRADING = 0.50              # 50 % des gains nets → trading
LONG_TERM_RATE = 0.37                # 37 % vers poche long terme (BTC/ETH/SOL/…)
BFR_RATE = 0.10                      # 10 % vers BFR
SECURITY_RATE = 0.03                 # 3 % vers sécurité

# Répartition interne des 37 % long terme
LONG_TERM_SPLIT = {
    "BTC": 0.40,
    "ETH": 0.25,
    "SOL": 0.15,
    "BNB": 0.07,
    "XRP": 0.05,
    "AVAX": 0.05,
    "MATIC": 0.03,
}

ALLOCATOR_REPORT_FILE = "src/v2/data/reports/allocator_last_run.json"
EQUITY_FILE = "src/v2/data/reports/equity_state.json"

# ---------------------------------------------------------------------
# 🧮 Modèle interne
# ---------------------------------------------------------------------

@dataclass
class AllocationResult:
    gross_gain: float
    tax_paid: float
    net_gain: float
    routed: Dict[str, float]
    server_ts: str

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------
# 📌 Helper : écriture des reports propres
# ---------------------------------------------------------------------

def write_report(data: Dict[str, Any]):
    save_json_file(ALLOCATOR_REPORT_FILE, data)
    log.info(f"[allocator] Report written → {ALLOCATOR_REPORT_FILE}")


# ---------------------------------------------------------------------
# 📌 Mise à jour equity dans equity_state.json
# ---------------------------------------------------------------------

def update_equity(delta: float):
    state = load_json_file(EQUITY_FILE, default={"equity_eur": 0.0})
    eq = float(state.get("equity_eur", 0.0))
    eq += float(delta)
    save_json_file(EQUITY_FILE, {
        "equity_eur": round(eq, 2),
        "server_ts": dt.datetime.now(dt.timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------
# 🚀 Fonction principale appelée par generate_trade_simulation
# ---------------------------------------------------------------------

def on_realized_gain(gain_gross_eur: float, totals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelé POUR CHAQUE gain réalisé.
    Gère fiscalité, allocation interne, réinvestissement trading.
    """

    gain_gross_eur = float(gain_gross_eur)
    equity = float(totals.get("equity_eur", 0.0))

    log.info(f"[allocator] Realized gain={gain_gross_eur}€ | equity={equity}€")

    # Si aucun gain → rien à faire
    if gain_gross_eur <= 0:
        write_report({
            "gross_gain": gain_gross_eur,
            "net_gain": 0.0,
            "tax_paid": 0.0,
            "routed": {},
            "server_ts": dt.datetime.now(dt.timezone.utc).isoformat()
        })
        return {"net_gain": 0.0}

    # -----------------------------------------------------------------
    # 1) Fiscalité → IS 25%
    # -----------------------------------------------------------------
    tax = round(gain_gross_eur * TAX_RATE, 2)
    net_after_tax = round(gain_gross_eur - tax, 2)

    # -----------------------------------------------------------------
    # 2) Si equity < 5000€, on réinvestit *tout* dans le trading
    # -----------------------------------------------------------------
    if equity < THRESHOLD_EQUITY_EUR:
        routed = {"trading_reinvest": net_after_tax}
        update_equity(net_after_tax)
        result = AllocationResult(
            gross_gain=gain_gross_eur,
            tax_paid=tax,
            net_gain=net_after_tax,
            routed=routed,
            server_ts=dt.datetime.now(dt.timezone.utc).isoformat()
        )
        write_report(result.to_dict())
        return result.to_dict()

    # -----------------------------------------------------------------
    # 3) Répartition normale (equity >= 5000€)
    # -----------------------------------------------------------------
    amt_trading = round(net_after_tax * REINVEST_TRADING, 2)
    amt_long_term = round(net_after_tax * LONG_TERM_RATE, 2)
    amt_bfr = round(net_after_tax * BFR_RATE, 2)
    amt_sec = round(net_after_tax * SECURITY_RATE, 2)

    # Répartition long terme interne
    long_term_detail = {
        k: round(amt_long_term * ratio, 2) for k, ratio in LONG_TERM_SPLIT.items()
    }

    routed = {
        "trading_reinvest": amt_trading,
        "long_term_total": amt_long_term,
        "bfr": amt_bfr,
        "security": amt_sec,
        "long_term_detail": long_term_detail,
    }

    # Mise à jour equity : seule la part trading augmente l’équity
    update_equity(amt_trading)

    # -----------------------------------------------------------------
    # 4) Report
    # -----------------------------------------------------------------
    result = AllocationResult(
        gross_gain=gain_gross_eur,
        tax_paid=tax,
        net_gain=net_after_tax,
        routed=routed,
        server_ts=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    write_report(result.to_dict())
    return result.to_dict()


# ---------------------------------------------------------------------
# CLI de test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    try:
        val = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
        out = on_realized_gain(val, totals={"equity_eur": 6000})
        print(out)
    except Exception as e:
        print({"error": str(e)})
