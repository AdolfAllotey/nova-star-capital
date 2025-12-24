
# src/v2/api/internal_api.py

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
import os

app = FastAPI()

DATA_FOLDER = "data/v2"

@app.get("/")
def root():
    return {"message": "API interne du bot crypto - V2"}

@app.get("/signals")
def get_signals():
    path = os.path.join(DATA_FOLDER, "selection/selected_tokens.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return data
    return JSONResponse(status_code=404, content={"error": "Signaux non trouvés"})

@app.get("/simulation")
def get_simulation():
    path = os.path.join(DATA_FOLDER, "simulation/simulated_trades.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return data
    return JSONResponse(status_code=404, content={"error": "Simulation non trouvée"})

@app.get("/summary")
def get_summary():
    path = os.path.join(DATA_FOLDER, "llm/llm_summary.txt")
    if os.path.exists(path):
        with open(path) as f:
            return {"summary": f.read()}
    return JSONResponse(status_code=404, content={"error": "Résumé non trouvé"})
