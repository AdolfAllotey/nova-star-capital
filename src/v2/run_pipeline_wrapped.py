
# [NSC] hard-disable outbound OpenAI calls (httpx send hook)
import os as _os
def _nsc_llm_disabled() -> bool:
    v = _os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    return v in ("0","false","no","n","off")

def _nsc_is_openai_url(url) -> bool:
    s = str(url)
    return ("api.openai.com" in s) or ("/v1/chat/completions" in s) or ("/v1/responses" in s)

if _nsc_llm_disabled():
    try:
        import httpx as _httpx

        _orig_send = _httpx.Client.send
        def _send(self, request, *a, **k):
            if _nsc_is_openai_url(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (NSC_LLM_ENABLED=0)")
            return _orig_send(self, request, *a, **k)
        _httpx.Client.send = _send

        _orig_asend = _httpx.AsyncClient.send
        async def _asend(self, request, *a, **k):
            if _nsc_is_openai_url(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (NSC_LLM_ENABLED=0)")
            return await _orig_asend(self, request, *a, **k)
        _httpx.AsyncClient.send = _asend
    except Exception:
        pass
import os

def llm_disabled() -> bool:
    v = os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    return v in ("0", "false", "no", "n", "off")

def is_openai_url(url) -> bool:
    s = str(url)
    return ("api.openai.com" in s) or ("/v1/chat/completions" in s) or ("/v1/responses" in s)

if llm_disabled():
    print("[wrapper] NSC_LLM_ENABLED=0 -> blocking OpenAI via httpx/requests")
    # block httpx
    try:
        import httpx
        _orig = httpx.Client.request
        def _req(self, method, url, *a, **k):
            if is_openai_url(url):
                raise RuntimeError("OpenAI hard-disabled by wrapper (NSC_LLM_ENABLED=0)")
            return _orig(self, method, url, *a, **k)
        httpx.Client.request = _req
    except Exception:
        pass

    # block requests (fallback)
    try:
        import requests
        _orig2 = requests.sessions.Session.request
        def _req2(self, method, url, *a, **k):
            if is_openai_url(url):
                raise RuntimeError("OpenAI hard-disabled by wrapper (NSC_LLM_ENABLED=0)")
            return _orig2(self, method, url, *a, **k)
        requests.sessions.Session.request = _req2
    except Exception:
        pass

import os


from src.v2.run_pipeline import main
raise SystemExit(main())
