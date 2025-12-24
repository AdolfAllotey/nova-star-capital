# src/v2/tools/assistant_config.py
"""
Config centralisée pour le pont assistant NSC.
"""

import os
from pathlib import Path

# Racine où tu as copié l'export ChatGPT
# Exemple actuel : /opt/nsc/chatgpt_exports/a458e0a6cb54.../
CHATGPT_EXPORT_ROOT = Path("/opt/nsc/chatgpt_exports")

# Dossier où l'index sera stocké
ASSISTANT_INDEX_DIR = Path("/opt/nsc/assistant_index")

# Fichiers d'index
EMBEDDINGS_FILE = ASSISTANT_INDEX_DIR / "embeddings.npy"
META_FILE = ASSISTANT_INDEX_DIR / "meta.json"

# Modèles OpenAI
EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4.1-mini"  # tu pourras monter en gamme si besoin

# Paramètres de retrieval
TOP_K = 12              # nombre de passages max
MAX_CONTEXT_CHARS = 12000  # taille max du contexte concaténé

# Clé OpenAI : tu peux la mettre dans l'environnement
# export OPENAI_API_KEY="sk-..."
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
