
# src/v2/interface/internal_api.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI(title="Bot Crypto Ultra - API Interne")

# Autoriser tous les domaines (à restreindre si besoin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FOLDER = "data/v2"
SIGNALS_FILE = os.path.join(DATA_FOLDER, "signals/selected_tokens.json")
PNL_FILE = os.path.join(DATA_FOLDER, "performance/global_pnl.json")
USERS_FILE = "src/v2/config/users.json"

def read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

@app.get("/")
def root():
    return {"status": "API opérationnelle", "version": "v1"}

@app.get("/signals")
def get_signals():
    return read_json(SIGNALS_FILE)

@app.get("/performance")
def get_performance():
    return read_json(PNL_FILE)

@app.get("/users")
def get_users():
    return read_json(USERS_FILE)
