#!/bin/bash
set -e

# Ce script est pensé pour être lancé depuis: src/v2/interface/react
# Ex: cd src/v2/interface/react && bash ../../../scripts/sync_data.sh

# Chemins vus depuis src/v2/interface/react
SRC_DIR="../../../data"
DEST_DIR="public/data"

echo "📂 Sync des données vers ${DEST_DIR} ..."

# Dossiers à créer côté front
mkdir -p "${DEST_DIR}/reports"
mkdir -p "${DEST_DIR}/simulation"
mkdir -p "${DEST_DIR}/risk"
mkdir -p "${DEST_DIR}"

# Copies "meilleures-efforts" (silencieux si absent)
cp -v "${SRC_DIR}/reports/daily_report.json"         "${DEST_DIR}/reports/"  2>/dev/null || echo "⚠ daily_report.json manquant"
cp -v "${SRC_DIR}/reports/monthly_pnl.json"          "${DEST_DIR}/reports/"  2>/dev/null || echo "⚠ monthly_pnl.json manquant"
cp -v "${SRC_DIR}/simulation/trade_simulation.json"  "${DEST_DIR}/simulation/" 2>/dev/null || echo "⚠ trade_simulation.json manquant"
cp -v "${SRC_DIR}/risk/worst_trades.json"            "${DEST_DIR}/risk/"     2>/dev/null || echo "⚠ worst_trades.json manquant"
cp -v "${SRC_DIR}/risk/worst_trades_summary.json"    "${DEST_DIR}/risk/"     2>/dev/null || echo "⚠ worst_trades_summary.json manquant"

# (optionnels si tu les utilises côté UI)
cp -v "${SRC_DIR}/airdrops.json"                     "${DEST_DIR}/"          2>/dev/null || true
cp -v "${SRC_DIR}/telegram_data.json"                "${DEST_DIR}/"          2>/dev/null || true
cp -v "${SRC_DIR}/twitter_data.json"                 "${DEST_DIR}/"          2>/dev/null || true
cp -v "${SRC_DIR}/reddit_data.json"                  "${DEST_DIR}/"          2>/dev/null || true
cp -v "${SRC_DIR}/meta.json"                         "${DEST_DIR}/"          2>/dev/null || true

echo "✅ Sync OK -> ${DEST_DIR}"
