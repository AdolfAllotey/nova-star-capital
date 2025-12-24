# src/v2/tools/assistant_ask.py

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from openai import OpenAI

from .assistant_config import (
    ASSISTANT_INDEX_DIR,
    EMBEDDINGS_FILE,
    META_FILE,
    EMBEDDING_MODEL,
    CHAT_MODEL,
    TOP_K,
    MAX_CONTEXT_CHARS,
    OPENAI_API_KEY,
)

log = logging.getLogger("assistant_ask")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def load_index():
    if not EMBEDDINGS_FILE.exists() or not META_FILE.exists():
        raise FileNotFoundError(
            f"Index introuvable. Lance d'abord :\n"
            f"  python -m src.v2.tools.assistant_index"
        )

    embeddings = np.load(EMBEDDINGS_FILE)
    with META_FILE.open("r", encoding="utf-8") as f:
        meta = json.load(f)

    if len(meta) != embeddings.shape[0]:
        raise ValueError(
            f"Incohérence index : {len(meta)} meta vs {embeddings.shape[0]} embeddings"
        )

    log.info(f"[ask] Index chargé : {embeddings.shape[0]} passages")
    return embeddings, meta


def get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY n'est pas défini dans l'environnement. "
            "export OPENAI_API_KEY='sk-...' avant d'utiliser assistant_ask."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def embed_query(text: str) -> np.ndarray:
    client = get_client()
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
    )
    vec = np.array(resp.data[0].embedding, dtype="float32")
    return vec


def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    # a : (N, d), b : (d,)
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b) + 1e-9)
    return np.dot(a_norm, b_norm)


def build_context(
    meta: List[Dict[str, Any]],
    embeddings: np.ndarray,
    query_vec: np.ndarray,
) -> str:
    scores = cosine_sim(embeddings, query_vec)
    # tri décroissant
    top_idx = np.argsort(-scores)[: TOP_K * 3]  # on sur-sélectionne, on filtrera après

    snippets = []
    total_chars = 0

    for idx in top_idx:
        m = meta[int(idx)]
        text = m["text"].strip()
        title = m.get("title") or "Sans titre"
        role = m.get("role") or "unknown"
        score = float(scores[int(idx)])

        snippet = f"[{title} | {role} | score={score:.3f}]\n{text}\n"
        if text and (total_chars + len(snippet)) <= MAX_CONTEXT_CHARS:
            snippets.append(snippet)
            total_chars += len(snippet)
        if total_chars >= MAX_CONTEXT_CHARS:
            break

    context = "\n\n---\n\n".join(snippets)
    return context


def ask_llm(question: str, context: str) -> str:
    client = get_client()
    system_prompt = """
Tu es l'assistant technique de Nova Star Capital (NSC), un bot de trading multi-stratégies
(crypto v2 + préproduction, futures versions actions/oblig/ options).

Tu as accès à un CONTEXTE tiré de conversations passées entre l'utilisateur et ChatGPT
(conception du bot, architecture, modules Python, interface React, roadmap, fiscalité, etc.).

RÈGLES :
- Utilise le contexte fourni autant que possible pour rester cohérent avec la version actuelle du projet NSC.
- Si certaines infos ne sont pas dans le contexte, déduis-les de manière raisonnable mais indique
  clairement ce qui est certain vs. ce qui est une proposition.
- Quand tu produis du code :
  - Respecte l'architecture existante (src/v2/..., logs centralisés, OpenAI SDK v1.95+ avec OpenAI()).
  - Évite de casser les chemins et modules existants.
  - Commente clairement les parties importantes (hypothèses, TODO, paramètres).
- Réponds en français, de manière claire et pragmatique.
"""

    user_prompt = f"""
Question de l'utilisateur :
{question}

Contexte disponible (extraits de conversations précédentes) :
{context}
"""

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
    )

    return resp.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(
        description="Pose une question au pont assistant NSC (avec retrieval sur les conversations exportées)."
    )
    parser.add_argument(
        "question",
        nargs="+",
        help="Question à poser à l'assistant",
    )
    args = parser.parse_args()
    question = " ".join(args.question)

    embeddings, meta = load_index()
    q_vec = embed_query(question)
    context = build_context(meta, embeddings, q_vec)

    if not context:
        log.warning("[ask] Aucun contexte trouvé, réponse sans retrieval.")

    answer = ask_llm(question, context)
    print(answer)


if __name__ == "__main__":
    main()
