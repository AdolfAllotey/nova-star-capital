
# src/v2/api/api_server.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Bot Crypto Ultra API", version="1.0")

# 🔁 Exemples de données fictives
sample_signals = [
    {"token": "BTC", "score": 95, "sentiment": 0.8},
    {"token": "ETH", "score": 90, "sentiment": 0.75}
]

sample_performance = {
    "total_pnl": 3200,
    "roi_pct": 12.5
}

sample_report = {
    "summary": "Journée très positive avec un gain cumulé de 3200€. BTC et ETH surperforment.",
    "alerts": ["Alerte performance sur SOL"]
}

@app.get("/signals")
def get_signals():
    return {"signals": sample_signals}

@app.get("/performance")
def get_performance():
    return {"performance": sample_performance}

@app.get("/report")
def get_report():
    return sample_report

# 🔧 Démarrage local (à exécuter via: uvicorn src.v2.api.api_server:app --reload)
if __name__ == "__main__":
    uvicorn.run("src.v2.api.api_server:app", host="0.0.0.0", port=8000, reload=True)
