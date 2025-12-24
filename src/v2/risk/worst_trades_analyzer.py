# src/v2/risk/worst_trades_analyzer.py
import csv, os, json, logging
from datetime import datetime, timezone, timezone
log = logging.getLogger(__name__)

def analyze_worst_trades() -> bool:
    """
    Stub: lit trading/trades.csv, prend les 3 pires PnL et écrit worst_trades.json
    """
    try:
        in_file  = "src/v2/data/trading/trades.csv"
        out_dir  = "src/v2/data/risk"
        out_file = os.path.join(out_dir, "worst_trades.json")
        if not os.path.exists(in_file):
            log.info("ℹ️ Aucun trade à analyser (fichier absent).")
            return True

        rows = []
        with open(in_file, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r: rows.append(row)

        # cast float
        for r in rows:
            try:
                r["pnl_usd"] = float(r["pnl_usd"])
            except Exception:
                r["pnl_usd"] = 0.0

        worst = sorted(rows, key=lambda x: x["pnl_usd"])[:3]

        os.makedirs(out_dir, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "worst": worst
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        log.info("🛡️ Pires trades sauvegardés dans %s (%d éléments)", out_file, len(worst))
        return True
    except Exception as e:
        log.warning("⚠️ analyze_worst_trades: %s", e)
        return False
