#!/usr/bin/env bash
set -euo pipefail

# Répertoires de base
BASE_DIR="/opt/nsc"
APP_DIR="$BASE_DIR/app"
REPORTS_DIR="$BASE_DIR/src/v2/data/reports"

# Python + module de sync
PY_BIN="/opt/nsc-venv/bin/python"
MODULE="src.v2.tools.google_drive_sync"

# Dossier Google Drive "NSC-Reports"
FOLDER_ID="1u4tzdpISg-rOaTlohsKwFVmbMBBGF-3L"

cd "$APP_DIR"

# Si le dossier des reports n'existe pas, on log et on sort
if [ ! -d "$REPORTS_DIR" ]; then
  echo "[drive-sync] $(date -Iseconds) WARNING: dossier introuvable : $REPORTS_DIR"
  exit 0
fi

# Upload de tous les .json du dossier reports
for file in "$REPORTS_DIR"/*.json; do
  # Si aucun fichier ne matche, on skip
  [ -e "$file" ] || continue

  echo "[drive-sync] $(date -Iseconds) upload → $file"
  $PY_BIN -m $MODULE --local "$file" --folder "$FOLDER_ID" || {
    echo "[drive-sync] $(date -Iseconds) ERREUR sur $file"
  }
done
