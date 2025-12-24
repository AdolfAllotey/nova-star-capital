
# src/v2/api/fastapi_server.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import glob

app = FastAPI()

# Utils
def load_latest_file(folder, ext):
    files = sorted(glob.glob(os.path.join(folder, f"*.{ext}")), reverse=True)
    if not files:
        return None
    return files[0]

@app.get("/status")
def get_status():
    return {"status": "✅ API opérationnelle", "version": "V2"}

@app.get("/report/latest", response_class=HTMLResponse)
def get_latest_report():
    report_path = load_latest_file("data/v2/reports/", "html")
    if report_path and os.path.exists(report_path):
        with open(report_path, "r") as f:
            return f.read()
    return HTMLResponse(content="Aucun rapport disponible", status_code=404)

@app.get("/signals")
def get_signals():
    signals_path = load_latest_file("data/v2/archive/allocations/", "json")
    if signals_path and os.path.exists(signals_path):
        with open(signals_path, "r") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={"error": "Aucun signal trouvé"}, status_code=404)

@app.get("/portfolio")
def get_portfolio():
    portfolio_path = "data/v2/portfolio/portfolio_balances.csv"
    if os.path.exists(portfolio_path):
        with open(portfolio_path, "r") as f:
            lines = f.readlines()
        header = lines[0].strip().split(",")
        last_row = lines[-1].strip().split(",")
        return dict(zip(header, last_row))
    return JSONResponse(content={"error": "Aucun solde disponible"}, status_code=404)

@app.get("/summary")
def get_llm_summary():
    summary_path = load_latest_file("data/v2/archive/summaries/", "txt")
    if summary_path and os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            return {"summary": f.read()}
    return JSONResponse(content={"error": "Aucun résumé trouvé"}, status_code=404)
