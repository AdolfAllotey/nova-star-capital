# v2/api/security.py
import os
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Swagger "Authorize" (Bearer)
bearer_scheme = HTTPBearer(auto_error=False)

def require_bearer(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    # Option de bypass (dev)
    if os.getenv("API_DISABLE_AUTH", "").lower() in {"1", "true", "yes"}:
        return

    expected = os.getenv("NSC_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfigured: NSC_API_TOKEN missing")

    # 1) Query string (?token= ou ?access_token=) — accepté partout
    q = request.query_params
    q_token = q.get("token") or q.get("access_token")
    if q_token is not None:
        if q_token == expected:
            return
        raise HTTPException(status_code=403, detail="Invalid token")

    # 2) Header alternatif
    x_token = request.headers.get("x-api-token")
    if x_token is not None:
        if x_token == expected:
            return
        raise HTTPException(status_code=403, detail="Invalid token")

    # 3) Bearer standard
    if creds and (creds.scheme or "").lower() == "bearer":
        if creds.credentials == expected:
            return
        raise HTTPException(status_code=403, detail="Invalid token")

    # Rien fourni
    raise HTTPException(status_code=401, detail="Missing Bearer token")
