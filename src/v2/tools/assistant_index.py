# src/v2/tools/assistant_index.py
"""
Indexation des conversations ChatGPT pour Nova Star Capital.

- Lit l'export officiel ChatGPT (conversations.json ou un dossier d'export).
- Extrait les messages texte (user + assistant).
# NSC: hard-disable LLM calls in PREPROD when NSC_LLM_ENABLED=0
import os
if os.getenv('NSC_LLM_ENABLED','1').strip().lower() in ('0','false','no','n','off'):
    raise RuntimeError('LLM disabled (NSC_LLM_ENABLED=0)')
- Génère des embeddings via OpenAI (text-embedding-3-small).
- Sauvegarde l'index dans src/v2/data/reports/assistant_index.json.

⚠️ Nécessite :
    export OPENAI_API_KEY="sk-..."
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Tuple

from openai import OpenAI, RateLimitError, APIError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("assistant_index")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s INFO assistant_index: %(message)s")
)
if not logger.handlers:
    logger.addHandler(_handler)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Modèle d'embedding
EMBEDDING_MODEL = "text-embedding-3-small"

# Taille max approximative en caractères par texte
MAX_CHARS_PER_MSG = 3000

# Taille du batch d'embedding (réduite pour limiter les 429)
BATCH_SIZE = 32

# Nombre max de tentatives par batch en cas de RateLimitError
MAX_RETRIES_PER_BATCH = 8

# Index de sortie
OUTPUT_INDEX_PATH = "src/v2/data/reports/assistant_index.json"

# ---------------------------------------------------------------------------
# Helpers OpenAI
# ---------------------------------------------------------------------------


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY n'est pas défini dans l'environnement. "
            "export OPENAI_API_KEY='sk-...' avant de lancer l'indexation."
        )
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Lecture de l'export ChatGPT
# ---------------------------------------------------------------------------


def load_export(export_path: str) -> Any:
    """
    Charge l'export ChatGPT.

    - Si export_path est un dossier, on cherche conversations.json dedans.
    - Si export_path est un fichier .json, on le charge directement.
    """
    if os.path.isdir(export_path):
        json_path = os.path.join(export_path, "conversations.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(
                f"conversations.json introuvable dans {export_path}"
            )
        path = json_path
    else:
        path = export_path

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def normalize_conversations(raw: Any) -> List[Dict[str, Any]]:
    """
    L'export ChatGPT peut être :
    - soit un dict avec "conversations": [...]
    - soit une liste directe de conversations.
    On normalise en liste de conversations.
    """
    if isinstance(raw, dict) and "conversations" in raw:
        return raw["conversations"]
    if isinstance(raw, list):
        # cas des exports récents : liste directe
        return raw
    raise ValueError(
        "Format inattendu pour l'export ChatGPT (ni dict.conversations ni liste)."
    )


def extract_messages(raw: Any) -> List[Dict[str, Any]]:
    """
    Extrait tous les messages texte (user + assistant) de l'export.

    Retourne une liste :
    [
        {
            "conversation_id": str,
            "message_id": str,
            "role": "user"/"assistant"/"system",
            "text": "...",
            "title": "titre de la conversation ou vide",
            "create_time": <timestamp ou None>
        },
        ...
    ]
    """
    convs = normalize_conversations(raw)

    all_msgs: List[Dict[str, Any]] = []

    for conv in convs:
        conv_id = conv.get("conversation_id") or conv.get("id") or ""
        title = conv.get("title") or ""
        create_time = conv.get("create_time")

        mapping = conv.get("mapping") or {}
        for msg_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue

            role = msg.get("author", {}).get("role") or msg.get("role")
            if role not in ("user", "assistant", "system"):
                continue

            # contenu possible en plusieurs morceaux
            content_parts = msg.get("content", {}).get("parts") or []
            text = "\n".join(
                [str(part) for part in content_parts if isinstance(part, str)]
            ).strip()

            if not text:
                continue

            # On tronque les très longs messages pour éviter les 8k tokens
            if len(text) > MAX_CHARS_PER_MSG:
                text = text[:MAX_CHARS_PER_MSG]

            all_msgs.append(
                {
                    "conversation_id": conv_id,
                    "message_id": msg_id,
                    "role": role,
                    "text": text,
                    "title": title,
                    "create_time": create_time,
                }
            )

    return all_msgs


# ---------------------------------------------------------------------------
# Embeddings avec gestion robuste des rate limits
# ---------------------------------------------------------------------------


def embed_batch(
    client: OpenAI, texts: List[str], batch_start: int, total: int
) -> List[List[float]]:
    """
    Envoie un batch au modèle d'embedding, avec retries en cas de RateLimitError.
    """
    attempt = 0

    while True:
        try:
            resp = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            vectors = [item.embedding for item in resp.data]
            logger.info(
                "[index] Batch %d-%d / %d OK",
                batch_start,
                batch_start + len(texts) - 1,
                total,
            )
            return vectors

        except RateLimitError as e:
            attempt += 1
            if attempt > MAX_RETRIES_PER_BATCH:
                logger.error(
                    "[index] RateLimitError persistant après %d tentatives : %s",
                    attempt,
                    e,
                )
                raise

            wait = min(30.0, 2.0 * attempt)
            logger.warning(
                "[index] Rate limit (429) sur batch %d-%d, tentative %d/%d, "
                "attente %.1fs...",
                batch_start,
                batch_start + len(texts) - 1,
                attempt,
                MAX_RETRIES_PER_BATCH,
                wait,
            )
            time.sleep(wait)

        except APIError as e:
            # Erreur API non liée au rate limit
            logger.error("[index] APIError sur batch %d : %s", batch_start, e)
            raise

        except Exception as e:
            logger.error(
                "[index] Erreur inattendue sur batch %d : %s",
                batch_start,
                e,
            )
            raise


def build_embeddings(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construit l'index d'embeddings pour la liste de messages.
    Retourne un dict prêt à être sérialisé en JSON.
    """
    client = get_client()

    total = len(messages)
    logger.info("[index] Génération des embeddings pour %d messages", total)

    index_entries: List[Dict[str, Any]] = []

    for batch_start in range(0, total, BATCH_SIZE):
        batch = messages[batch_start : batch_start + BATCH_SIZE]
        texts = [m["text"] for m in batch]

        vectors = embed_batch(client, texts, batch_start, total)

        for msg, vec in zip(batch, vectors):
            index_entries.append(
                {
                    "conversation_id": msg["conversation_id"],
                    "message_id": msg["message_id"],
                    "role": msg["role"],
                    "title": msg["title"],
                    "create_time": msg["create_time"],
                    "embedding": vec,
                }
            )

        # Petit sleep pour lisser un peu la charge / evitar trop de 429
        time.sleep(0.1)

    return {
        "model": EMBEDDING_MODEL,
        "total_messages": total,
        "index_size": len(index_entries),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "entries": index_entries,
    }


# ---------------------------------------------------------------------------
# Sauvegarde
# ---------------------------------------------------------------------------


def save_index(index: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    logger.info("[index] Index sauvegardé → %s", path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Construit un index d'embeddings à partir d'un export ChatGPT."
    )
    parser.add_argument(
        "--export",
        type=str,
        default="/opt/nsc/chatgpt_exports/"
        "a458e0a6cb5416d697365cf882807ea5dd9baa5b122eccc57391f56f74e21d47-2025-11-20-20-56-02-bba986340c524064b8a8cb0bba413f95",
        help="Chemin vers le dossier ou fichier conversations.json de l'export ChatGPT",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=OUTPUT_INDEX_PATH,
        help=f"Chemin de sortie de l'index (défaut: {OUTPUT_INDEX_PATH})",
    )
    args = parser.parse_args()

    logger.info("[index] Utilisation de l'export : %s", args.export)

    data = load_export(args.export)
    messages = extract_messages(data)
    logger.info("[index] %d messages texte extraits", len(messages))

    index = build_embeddings(messages)
    save_index(index, args.output)


if __name__ == "__main__":
    main()
