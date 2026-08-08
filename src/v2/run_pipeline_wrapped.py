#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ROOT = Path("/opt/nsc/app")
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# ----------------------------
# NSC: hard-disable outbound OpenAI calls (httpx/requests hook)
# ----------------------------
def _llm_disabled() -> bool:
    v = os.getenv("NSC_LLM_ENABLED", "1").strip().lower()
    return v in ("0", "false", "no", "n", "off")

def _is_openai_url(url) -> bool:
    s = str(url)
    return ("api.openai.com" in s) or ("/v1/chat/completions" in s) or ("/v1/responses" in s)

def _install_openai_blockers() -> None:
    # block httpx
    try:
        import httpx  # type: ignore
        _orig_send = httpx.Client.send
        def _send(self, request, *a, **k):
            if _is_openai_url(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (NSC_LLM_ENABLED=0)")
            return _orig_send(self, request, *a, **k)
        httpx.Client.send = _send

        _orig_asend = httpx.AsyncClient.send
        async def _asend(self, request, *a, **k):
            if _is_openai_url(getattr(request, "url", "")):
                raise RuntimeError("OpenAI HTTP blocked (NSC_LLM_ENABLED=0)")
            return await _orig_asend(self, request, *a, **k)
        httpx.AsyncClient.send = _asend
    except Exception:
        pass

    # block requests (fallback)
    try:
        import requests  # type: ignore
        _orig = requests.sessions.Session.request
        def _req(self, method, url, *a, **k):
            if _is_openai_url(url):
                raise RuntimeError("OpenAI HTTP blocked (NSC_LLM_ENABLED=0)")
            return _orig(self, method, url, *a, **k)
        requests.sessions.Session.request = _req
    except Exception:
        pass

# ----------------------------
# Lock (non-blocking)
# ----------------------------
LOCK_PATH = Path("/opt/nsc/data/preprod/state/nsc-preprod-pipeline.lock")

def _acquire_lock_nonblocking() -> int | None:
    """
    Returns an OS fd if lock acquired, else None.
    """
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o664)
    try:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            os.close(fd)
            return None
    except Exception:
        # If fcntl unavailable (unlikely on Linux), close and run without lock
        try:
            os.close(fd)
        except Exception:
            pass
        return -1  # sentinel: no lock mechanism



def _refresh_market_conditions() -> None:
    """
    Refresh market regime and market conditions before rebuilding the master portfolio layer.
    """
    import subprocess

    env = os.environ.copy()
    env["PYTHONPATH"] = "/opt/nsc/app:" + env.get("PYTHONPATH", "")

    steps = [
        ("market_regime_detector", "src.v2.analysis.market_regime_detector"),
        ("market_conditions_engine_pro", "src.v2.analysis.market_conditions_engine_pro"),
    ]

    for label, module in steps:
        print(f"[wrapper][market] start {label}")
        subprocess.run(
            [sys.executable, "-m", module],
            cwd=str(APP_ROOT),
            env=env,
            check=True,
        )
        print(f"[wrapper][market] ok {label}")


def _refresh_master_layer() -> None:
    """
    Refresh the master portfolio layer after the global PREPROD pipeline:
    target -> state -> rebalance/funding -> coherence audit.
    Uses subprocess execution because some master modules are script-style.
    """
    import subprocess

    steps = [
        (
            "portfolio_adapters",
            "/opt/nsc/app/src/v2/portfolio/adapters/run_all_portfolio_adapters.py",
        ),
        ("portfolio_engine_v1", "/opt/nsc/app/src/v2/portfolio/portfolio_engine_v1.py"),
        ("portfolio_state_builder", "/opt/nsc/app/src/v2/portfolio/portfolio_state_builder.py"),
        ("master_rebalance_builder", "/opt/nsc/app/src/v2/portfolio/master_rebalance_builder.py"),
        ("master_coherence_audit", "/opt/nsc/app/src/v2/portfolio/master_coherence_audit.py"),
        ("orchestration_status_builder", "/opt/nsc/app/src/v2/portfolio/orchestration_status_builder.py"),
        ("check_orchestration_consistency", "/opt/nsc/app/src/v2/portfolio/check_orchestration_consistency.py"),
        ("global_orchestration_audit", "/opt/nsc/app/src/v2/portfolio/global_orchestration_audit.py"),
        ("supervision_gate_builder", "/opt/nsc/app/src/v2/portfolio/supervision_gate_builder.py"),
        ("institutional_supervision_summary", "/opt/nsc/app/src/v2/portfolio/institutional_supervision_summary.py"),
        (
            "executive_decision_engine_v2",
            "/opt/nsc/app/src/v2/executive_decision/executive_decision_engine.py",
        ),
        (
            "executive_decision_master_audit",
            "/opt/nsc/app/src/v2/audits/executive_decision_master_audit.py",
        ),
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = "/opt/nsc/app:" + env.get("PYTHONPATH", "")

    for label, script_path in steps:
        print(f"[wrapper][master] start {label}")
        subprocess.run(
            [sys.executable, script_path],
            cwd=str(APP_ROOT),
            env=env,
            check=True,
        )
        print(f"[wrapper][master] ok {label}")

def main() -> int:
    if _llm_disabled():
        print("[wrapper] NSC_LLM_ENABLED=0 -> blocking OpenAI via httpx/requests")
        _install_openai_blockers()

    fd = _acquire_lock_nonblocking()
    if fd is None:
        print("[wrapper] LOCKED: pipeline already running")
        return 0

    try:
        from src.v2.run_pipeline import main as pipeline_main
        rc = int(pipeline_main() or 0)
        if rc == 0:
            _refresh_master_layer()
        else:
            print(f"[wrapper][master] skipped because pipeline rc={rc}")
        return rc
    finally:
        # keep fd open during run; close at end
        if fd not in (-1, None):
            try:
                os.close(fd)
            except Exception:
                pass

if __name__ == "__main__":
    raise SystemExit(main())
