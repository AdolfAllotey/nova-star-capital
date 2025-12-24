#!/bin/bash
set -e
# À lancer depuis: src/v2/interface/react

SRC_DIR="../../data"
DEST_DIR="public/data"

echo "📂 Sync des données vers ${DEST_DIR} ..."

mkdir -p "${DEST_DIR}/reports" "${DEST_DIR}/simulation" "${DEST_DIR}/risk"

# Prendre le daily_report le plus récent si dispo, sinon fallback
LATEST_DAILY="$(ls -t ${SRC_DIR}/reports/daily_report_*.json 2>/dev/null | head -1 || true)"
if [ -n "$LATEST_DAILY" ] && [ -f "$LATEST_DAILY" ]; then
  echo "→ Copie du dernier daily_report: ${LATEST_DAILY}"
  cp -v "$LATEST_DAILY" "${DEST_DIR}/reports/daily_report.json"
elif [ -f "${SRC_DIR}/reports/daily_report.json" ]; then
  echo "→ Copie de reports/daily_report.json (fallback)"
  cp -v "${SRC_DIR}/reports/daily_report.json" "${DEST_DIR}/reports/daily_report.json"
else
  echo "⚠ Aucun daily_report trouvé"
fi

# Autres fichiers
cp -v "${SRC_DIR}/reports/monthly_pnl.json"             "${DEST_DIR}/reports/"      2>/dev/null || echo "⚠ monthly_pnl.json manquant"
cp -v "${SRC_DIR}/simulation/trade_simulation.json"     "${DEST_DIR}/simulation/"   2>/dev/null || echo "⚠ trade_simulation.json manquant"
cp -v "${SRC_DIR}/risk/worst_trades.json"               "${DEST_DIR}/risk/"         2>/dev/null || echo "⚠ worst_trades.json manquant"
cp -v "${SRC_DIR}/risk/worst_trades_summary.json"       "${DEST_DIR}/risk/"         2>/dev/null || echo "⚠ worst_trades_summary.json manquant"

# optionnels
cp -v "${SRC_DIR}/airdrops.json"                        "${DEST_DIR}/"              2>/dev/null || true
cp -v "${SRC_DIR}/telegram_data.json"                   "${DEST_DIR}/"              2>/dev/null || true
cp -v "${SRC_DIR}/twitter_data.json"                    "${DEST_DIR}/"              2>/dev/null || true
cp -v "${SRC_DIR}/reddit_data.json"                     "${DEST_DIR}/"              2>/dev/null || true
cp -v "${SRC_DIR}/meta.json"                            "${DEST_DIR}/"              2>/dev/null || true

echo "✅ Sync OK -> ${DEST_DIR}"
