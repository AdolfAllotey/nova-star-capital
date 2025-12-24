sudo tee /opt/nsc/app/src/v2/api/rate_limit.py >/dev/null <<'PY'
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

# Limites par défaut (ajuste selon tes besoins)
# Exemples: "100/minute", "1000/hour"
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", None)
    headers = {}
    if retry_after is not None:
        try:
            headers["Retry-After"] = str(int(retry_after))
        except Exception:
            pass
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
        headers=headers,
    )
PY
