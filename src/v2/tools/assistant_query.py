# /opt/nsc/app/src/v2/tools/assistant_query.py

import os
import json
import pickle
import numpy as np

from openai import OpenAI
from fastapi import HTTPException

INDEX_PATH = "/opt/nsc/app/src/v2/tools/assistant_index.pkl"
EXPORT_PATH = "/opt/nsc/chatgpt_exports/messages.jsonl"

EMBEDDING_MODEL = "text-embedding-3-small"
GPT_MODEL = "gpt-4.1-mini"

def load_index():
    if not os.path.exists(INDEX_PATH):
        raise HTTPException(status_code=500, detail="Index introuvable. Lance assistant_index d’abord.")
    
    with open(INDEX_PATH, "rb") as f:
        data = pickle.load(f)

    return data["vectors"], data["texts"]

def embed(client: OpenAI, text: str) -> np.ndarray:
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(resp.data[0].embedding, dtype="float32")

def search_knn(query_vec: np.ndarray, matrix: np.ndarray, k: int = 3):
    sims = np.dot(matrix, query_vec) / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec) + 1e-9)
    idx = np.argsort(sims)[::-1][:k]
    return idx, sims[idx]

def ask_question(question: str) -> dict:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Load vectors + texts
    vectors, texts = load_index()

    # Embed query
    q_vec = embed(client, question)

    # KNN
    idxs, scores = search_knn(q_vec, vectors, k=3)

    retrieved = [
        {
            "score": float(scores[i]),
            "text": texts[idxs[i]]
        }
        for i in range(len(idxs))
    ]

    # Compose prompt
    context = "\n---\n".join([r["text"] for r in retrieved])

    system = (
        "Tu es l'assistant interne de Nova Star Capital. "
        "Tu dois répondre strictement à partir du CONTEXTE fourni. "
        "Si quelque chose n'est pas présent dans le contexte, dis-le."
    )

    user_prompt = f"""
CONTEXT:
{context}

QUESTION:
{question}

Réponds de manière synthétique et précise.
"""

    resp = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ]
    )

    answer = resp.choices[0].message.content

    return {
        "question": question,
        "answer": answer,
        "sources": retrieved
    }
