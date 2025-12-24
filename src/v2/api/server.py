sudo cp -a /opt/nsc/app/src/v2/api/server.py /opt/nsc/app/src/v2/api/server.py.bak.$(date +%F-%H%M%S)

sudo tee /opt/nsc/app/src/v2/api/server.py >/dev/null <<'PY'
from fastapi import FastAPI, APIRouter
from slowapi.errors import RateLimitExceeded

# Module rate-limit (créé à l'étape 1)
from .rate_limit import limiter, rate_limit_handler

app = FastAPI(
    title="Nova Star Capital API",
    version="2025.10-preprod",
)

# --- SlowAPI: branchement global ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Raccourci décorateur (compat versions de slowapi)
try:
    from slowapi.decorator import limiter as limit
except Exception:
    from slowapi import limiter as limit  # fallback historique


# --- Endpoints publics ---
@app.get("/health")
@limit.exempt  # Pas de rate limit sur la sonde
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "env": "preprod",
    }

@app.get("/version")
@limit.limit("20/minute")  # exemple de limite
def version():
    return {"version": "2025.10-preprod"}


# --- Endpoints sécurisés ---
secure = APIRouter(prefix="/secure")

@secure.get("/version")
@limit.limit("10/minute")  # limite plus stricte
def secure_version():
    return {"version": "2025.10-preprod"}

app.include_router(secure)


# --- (facultatif) point d'entrée local pour uvicorn ---
# uvicorn v2: `uvicorn module:app` reste valide
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000)
PY
