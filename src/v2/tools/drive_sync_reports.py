# src/v2/tools/drive_sync_reports.py
"""
Synchronise les rapports clés NSC vers Google Drive
en utilisant google_drive_sync.upload_file.

Les fichiers manquants sont ignorés avec un warning.
"""

from __future__ import annotations

import os
from pathlib import Path

from src.v2.utils.logger import get_logger
from src.v2.tools.google_drive_sync import upload_file

log = get_logger("drive_sync_reports")

# Dossier Drive NSC-Reports (fourni par Adolf)
FOLDER_ID = os.environ.get(
    "NSC_DRIVE_FOLDER_ID",
    "1u4tzdpISg-rOaTlohsKwFVmbMBBGF-3L",  # NSC-Reports
)

BASE = Path("/opt/nsc")

FILES = [
    # Regime / Risk
    BASE / "src" / "v2" / "data" / "reports" / "market_regime.json",
    BASE / "src" / "v2" / "data" / "reports" / "risk_state.json",

    # PnL & coûts
    BASE / "src" / "v2" / "data" / "reports" / "monthly_pnl.json",
    BASE / "src" / "v2" / "data" / "reports" / "monthly_costs.json",

    # Trades & positions
    BASE / "src" / "v2" / "data" / "reports" / "worst_trades.json",
    BASE / "src" / "v2" / "data" / "reports" / "worst_trades_summary.json",
    BASE / "src" / "v2" / "data" / "reports" / "open_positions.json",

    # Intelligence (sentiment / whales)
    BASE / "src" / "v2" / "data" / "intelligence" / "sentiment_overview.json",
    BASE / "src" / "v2" / "data" / "intelligence" / "whales_leaderboard.json",
]


def main() -> None:
    log.info("[drive_sync_reports] start sync → folder=%s", FOLDER_ID)

    ok = 0
    skipped = 0

    for path in FILES:
        path_str = str(path)
        if not path.exists():
            skipped += 1
            log.warning(
                "[drive_sync_reports] fichier absent, on ignore : %s", path_str
            )
            continue

        try:
            log.info("[drive_sync_reports] upload → %s", path_str)
            res = upload_file(path_str, folder_id=FOLDER_ID)
            log.info(
                "[drive_sync_reports] OK %s → id=%s",
                path.name,
                res.get("id"),
            )
            ok += 1
        except Exception as e:
            log.exception(
                "[drive_sync_reports] erreur upload %s : %s", path_str, e
            )

    log.info(
        "[drive_sync_reports] terminé : %s fichiers envoyés, %s ignorés",
        ok,
        skipped,
    )


if __name__ == "__main__":
    main()
