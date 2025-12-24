#!/bin/bash
# ==========================================
# Init Nova Star Capital (DEV)
# Active un venv existant + exporte variables
# ==========================================

# 1) Trouver un venv connu
CANDIDATES=(
  "/opt/nsc-venv"
  "/root/Bot_crypto_ultra/nsc-venv"
)

VENV=""
for p in "${CANDIDATES[@]}"; do
  if [ -f "$p/bin/activate" ]; then
    VENV="$p"
    break
  fi
done

if [ -z "$VENV" ]; then
  echo "⚠️  Aucun venv trouvé aux chemins connus."
  echo "   → Pour en créer un local au projet :"
  echo "      python3 -m venv /root/Bot_crypto_ultra/nsc-venv && source /root/Bot_crypto_ultra/nsc-venv/bin/activate"
  echo "   (ou utilise /opt/nsc-venv si déjà installé pour le service systemd)"
else
  # 2) Activer le venv trouvé
  # shellcheck disable=SC1090
  source "$VENV/bin/activate"
  echo "✅ Venv activé: $VENV"
fi

# 3) Variables d'env DEV
export PYTHONPATH=/root/Bot_crypto_ultra/src
export NSC_API_TOKEN="2d9624fb5808628625fa9cd4e500a5a86152bc794a66ef23"
export NSC_API_BASE="http://127.0.0.1:8000"

echo "✅ Environnement DEV prêt"
echo "   - PYTHONPATH=$PYTHONPATH"
echo "   - NSC_API_BASE=$NSC_API_BASE"
echo "   - Token chargé"
