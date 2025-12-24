#!/bin/bash

PYTHON_BACKUP_SCRIPT="src/v2/backup/backup_logs.py"
BACKUP_BASE_DIR="src/v2/data/v2/backups"
RETENTION_DAYS=30

# Lancer le backup Python et récupérer le dossier créé
BACKUP_OUTPUT=$(python $PYTHON_BACKUP_SCRIPT | grep "Création du dossier de backup" | awk -F': ' '{print $2}')

if [ -d "$BACKUP_OUTPUT" ]; then
    echo "Compression du dossier backup : $BACKUP_OUTPUT"
    tar -czf "${BACKUP_OUTPUT}.tar.gz" -C "$(dirname "$BACKUP_OUTPUT")" "$(basename "$BACKUP_OUTPUT")"
    echo "Compression terminée : ${BACKUP_OUTPUT}.tar.gz"
else
    echo "Erreur : dossier de backup non trouvé."
fi

# Suppression des backups compressés plus vieux que $RETENTION_DAYS jours
echo "Suppression des backups compressés de plus de $RETENTION_DAYS jours dans $BACKUP_BASE_DIR"
find "$BACKUP_BASE_DIR" -name "backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -exec rm -v {} \;