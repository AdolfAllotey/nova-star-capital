import os
import time
from src.v2.utils.logger import get_logger

logger = get_logger("transfer_funds")

"""
NSC - transfer_funds (FROZEN)

Objectif:
- Désactiver proprement toute logique de transfert de fonds pendant la PREPROD (et tant que non validée).
- Zéro import exchange / Binance
- Zéro action réseau
- Zéro exception (fail-safe)
- Logs explicites pour éviter toute ambiguïté

Réactivation (quand on sera prêt):
- Implémenter/valider binance_api transfer (subaccount/internal transfer)
- Ajouter un hard-gate complet (NSC_ENV=PROD, confirm, kill_switch, governance)
- Ajouter un mode DRY_RUN planifié
- Ajouter mapping subaccounts + tests
"""

FROZEN = True

def execute_transfers() -> None:
    """
    No-op volontaire.
    """
    try:
        env = str(os.getenv("NSC_ENV", "PREPROD")).upper()
        allow = os.getenv("ALLOW_FUNDS_TRANSFER", "false").lower() == "true"
        confirm = os.getenv("CONFIRM_FUNDS_TRANSFER", "")
        dry_run = os.getenv("TRANSFER_DRY_RUN", "true").lower() == "true"

        logger.warning(
            "[transfer_funds] FROZEN no-op (env=%s allow=%s confirm=%s dry_run=%s) -> transfers disabled",
            env, allow, confirm, dry_run
        )
        return
    except Exception as e:
        # Fail-safe absolu: ne jamais casser la pipeline
        try:
            logger.exception("[transfer_funds] FROZEN no-op error (ignored): %s", e)
        except Exception:
            pass
        return

if __name__ == "__main__":
    # One-shot par défaut: exécute une fois et sort.
    # Mode daemon uniquement si TRANSFER_FUNDS_DAEMON=true
    daemon = os.getenv("TRANSFER_FUNDS_DAEMON", "false").lower() == "true"
    if not daemon:
        execute_transfers()
        raise SystemExit(0)

    interval_h = float(os.getenv("TRANSFER_FUNDS_INTERVAL_HOURS", "6"))
    interval_s = int(interval_h * 3600)
    while True:
        execute_transfers()
        time.sleep(interval_s)
