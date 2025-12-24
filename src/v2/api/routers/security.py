# /opt/nsc/app/src/v2/api/routers/security.py
from fastapi import HTTPException, Request
import base64
import os

USER = os.getenv("NSC_BASIC_USER", "adrien")
PASS = os.getenv("NSC_BASIC_PASS", "monpass")

def require_basic_auth(func):
    async def wrapper(*args, **kwargs):
        # args[0] sera Request si utilisé comme dependency; ici on reste simple
        for a in args:
            if isinstance(a, Request):
                req = a
                break
        else:
            req = kwargs.get("request")
        if not req:
            raise HTTPException(500, "Request missing")

        auth = req.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate":"Basic"})
        try:
            decoded = base64.b64decode(auth.split(" ",1)[1]).decode()
        except Exception:
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate":"Basic"})
        u, _, p = decoded.partition(":")
        if u != USER or p != PASS:
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate":"Basic"})
        return await func(*args, **kwargs)
    return wrapper
