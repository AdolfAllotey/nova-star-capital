"""
NSC - sitecustomize
Chargé automatiquement par Python au démarrage (si sur sys.path).
Objectif: bloquer TOUT appel HTTP vers api.openai.com quand NSC_LLM_ENABLED=0
(ou quand OPENAI_API_KEY est vide).
"""
import os, sys

def _is_disabled() -> bool:
    v = os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    if v in ("0", "false", "no", "n", "off"):
        return True
    # sécurité: si pas de clé, on considère disabled
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return True
    return False

def _is_openai(url) -> bool:
    s = str(url)
    return ("api.openai.com" in s) or ("/v1/chat/completions" in s) or ("/v1/responses" in s)

if _is_disabled():
    try:
        import httpx

        _orig_send = httpx.Client.send
        def _send(self, request, *a, **k):
            if _is_openai(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (sitecustomize; NSC_LLM_ENABLED=0 or no API key)")
            return _orig_send(self, request, *a, **k)
        httpx.Client.send = _send

        _orig_asend = httpx.AsyncClient.send
        async def _asend(self, request, *a, **k):
            if _is_openai(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (sitecustomize; NSC_LLM_ENABLED=0 or no API key)")
            return await _orig_asend(self, request, *a, **k)
        httpx.AsyncClient.send = _asend

        pass
    except ModuleNotFoundError as e:
        # httpx absent sur le Python système -> silencieux (pas bloquant)
        if getattr(e, "name", "") == "httpx":
            pass
        else:
            sys.stderr.write(f"[sitecustomize] failed to install hook: {e}\n")
    except Exception as e:
        sys.stderr.write(f"[sitecustomize] failed to install hook: {e}\n")
