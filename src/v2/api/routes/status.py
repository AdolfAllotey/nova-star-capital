from fastapi import APIRouter
import os, time, platform, socket

router = APIRouter(tags=["meta"])
_STARTED_AT = time.time()

@router.get("/status")
def status():
    # Alias stable pour l'UI (Go/No-Go) — même payload que /metrics
    return metrics()

@router.get("/metrics")
def metrics():
    return {
        "app":"nsc-api",
        "env": os.getenv("NSC_ENV","preprod"),
        "version":"1.0.0",
        "host": socket.gethostname(),
        "platform": f"{platform.system()}-{platform.release()}",
        "python": platform.python_version(),
        "uptime_s": round(time.time()-_STARTED_AT, 2),
        "status":"ok",
    }
