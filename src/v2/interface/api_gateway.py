
from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

SIGNALS_FILE = "data/v2/outputs/signals.json"
PERF_FILE = "data/v2/outputs/performance.json"

@app.route("/")
def home():
    return "🔐 API du bot crypto – V2"

@app.route("/signals", methods=["GET"])
def get_signals():
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, "r") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"error": "Aucun signal disponible"}), 404

@app.route("/performance", methods=["GET"])
def get_performance():
    if os.path.exists(PERF_FILE):
        with open(PERF_FILE, "r") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"error": "Aucune performance disponible"}), 404

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "OK", "version": "V2", "api": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
