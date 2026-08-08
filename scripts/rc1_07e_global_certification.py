from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request


ROOT = Path("/opt/nsc/app")
REACT_DIR = ROOT / "src/v2/interface/react"
REACT_SRC = REACT_DIR / "src"
API_BASE = "http://127.0.0.1:8000"

EXECUTION_PLAN = Path(
    "/opt/nsc/data/preprod/trading/execution_plan.json"
)
SIMULATED_PLAN = Path(
    "/opt/nsc/data/preprod/trading/execution_plan_simulated.json"
)

LONG_TERM_FILES = [
    ROOT / "data/portfolio/long_term_valuation.json",
    ROOT / "data/portfolio/lt_portfolio_valuation.json",
    Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json"),
]

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
REPORT_PATH = (
    ROOT
    / "data/audits"
    / f"rc1_07e_global_certification_{stamp}.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(command, cwd=None, timeout=180):
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {
            "returncode": 999,
            "stdout": "",
            "stderr": str(exc),
        }


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sha256(path: Path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def age_seconds(path: Path):
    try:
        return (
            datetime.now(timezone.utc).timestamp()
            - path.stat().st_mtime
        )
    except Exception:
        return None


def api_get(endpoint: str):
    url = f"{API_BASE}{endpoint}"

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )
            return {
                "ok": response.status == 200,
                "status": response.status,
                "engine": (
                    payload.get("engine")
                    if isinstance(payload, dict)
                    else None
                ),
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": 0,
            "error": str(exc),
        }


def check_service(name: str):
    enabled = run(
        ["systemctl", "is-enabled", name],
        timeout=20,
    )
    active = run(
        ["systemctl", "is-active", name],
        timeout=20,
    )

    enabled_value = enabled["stdout"].strip()
    active_value = active["stdout"].strip()

    return {
        "ok": (
            enabled_value in {"enabled", "static"}
            and active_value in {"active", "inactive"}
        ),
        "enabled": enabled_value,
        "active": active_value,
    }


def check_execution_plan(path: Path, expected_status: str):
    payload = read_json(path)

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "exists": path.exists(),
            "path": str(path),
        }

    governance = payload.get("governance", {}) or {}
    orders = payload.get("orders", []) or []

    return {
        "ok": (
            payload.get("status") == expected_status
            and isinstance(orders, list)
            and governance.get("hard_block") is False
            and governance.get("action_policy")
            == "SIMULATED_ONLY"
        ),
        "exists": True,
        "path": str(path),
        "status": payload.get("status"),
        "execution_mode": payload.get("execution_mode"),
        "orders_count": len(orders),
        "hard_block": governance.get("hard_block"),
        "action_policy": governance.get("action_policy"),
        "age_seconds": age_seconds(path),
    }


def check_long_term():
    results = {}
    hashes = []

    for path in LONG_TERM_FILES:
        payload = read_json(path)
        digest = sha256(path)

        if digest:
            hashes.append(digest)

        positions = (
            payload.get("positions", [])
            if isinstance(payload, dict)
            else []
        )
        quality = (
            payload.get("data_quality", {})
            if isinstance(payload, dict)
            else {}
        )

        results[str(path)] = {
            "ok": (
                isinstance(payload, dict)
                and payload.get("engine")
                == "long_term_consolidator_v2"
                and len(positions) == 17
                and quality.get("complete") is True
                and int(
                    quality.get("fallback_count", 0) or 0
                ) == 0
            ),
            "exists": path.exists(),
            "engine": (
                payload.get("engine")
                if isinstance(payload, dict)
                else None
            ),
            "positions_count": (
                len(positions)
                if isinstance(positions, list)
                else 0
            ),
            "complete": quality.get("complete"),
            "fallback_count": quality.get(
                "fallback_count"
            ),
            "provider_error_count": len(
                quality.get("provider_errors", []) or []
            ),
            "age_seconds": age_seconds(path),
            "sha256": digest,
        }

    alignment = len(hashes) == 3 and len(set(hashes)) == 1

    return {
        "ok": (
            alignment
            and all(
                item["ok"]
                for item in results.values()
            )
        ),
        "hash_alignment": alignment,
        "files": results,
    }


def active_frontend_files():
    for path in REACT_SRC.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix not in {".js", ".jsx"}:
            continue

        if "_archive" in path.parts:
            continue

        if ".bak" in path.name:
            continue

        yield path


def check_frontend_lineage():
    hardcoded_pattern = re.compile(
        r"https://api\.preprod\.novastarcapital\.fr"
        r"|http://localhost:8000"
        r"|http://127\.0\.0\.1:8000"
    )
    legacy_pattern = re.compile(
        r"\bVITE_API_BASE_URL\b|\bVITE_API_URL\b"
    )
    static_pattern = re.compile(
        r"""fetch\s*\(\s*[`"']/data/"""
    )

    hardcoded = []
    legacy = []
    static_fetches = []

    canonical_api_file = (
        REACT_SRC / "lib/apiBase.js"
    ).resolve()

    for path in active_frontend_files():
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        if (
            path.resolve() != canonical_api_file
            and hardcoded_pattern.search(text)
        ):
            hardcoded.append(
                str(path.relative_to(ROOT))
            )

        # Compatibility variables are allowed only in the
        # canonical API compatibility layer.
        if (
            path.resolve() != canonical_api_file
            and legacy_pattern.search(text)
        ):
            legacy.append(
                str(path.relative_to(ROOT))
            )

        if static_pattern.search(text):
            static_fetches.append(
                str(path.relative_to(ROOT))
            )

    return {
        "ok": not hardcoded
        and not legacy
        and not static_fetches,
        "hardcoded_api": sorted(set(hardcoded)),
        "legacy_env": sorted(set(legacy)),
        "static_fetches": sorted(
            set(static_fetches)
        ),
    }


checks = {}

checks["services"] = {
    "api": check_service("nsc-api.service"),
    "long_term_timer": check_service(
        "nsc-long-term-refresh.timer"
    ),
}
checks["services"]["ok"] = all(
    item.get("ok")
    for key, item in checks["services"].items()
    if key != "ok"
)

checks["execution_plan"] = check_execution_plan(
    EXECUTION_PLAN,
    "ready",
)
checks["execution_plan_simulated"] = check_execution_plan(
    SIMULATED_PLAN,
    "simulated",
)

checks["long_term"] = check_long_term()

endpoints = [
    "/long-term",
    "/api/long-term",
    "/api/long-term/valuation",
    "/api/lt-curve",
    "/api/total-curve",
    "/dashboard/v3",
    "/api/portfolio-state",
]

checks["api_endpoints"] = {
    endpoint: api_get(endpoint)
    for endpoint in endpoints
}
checks["api_endpoints"]["ok"] = all(
    result.get("ok")
    for endpoint, result
    in checks["api_endpoints"].items()
    if endpoint != "ok"
)

checks["frontend_lineage"] = (
    check_frontend_lineage()
)

build = run(
    ["npm", "run", "build"],
    cwd=REACT_DIR,
    timeout=300,
)

checks["react_build"] = {
    "ok": build["returncode"] == 0,
    "returncode": build["returncode"],
    "stderr_tail": build["stderr"][-1000:],
}

failures = []

for name in (
    "services",
    "execution_plan",
    "execution_plan_simulated",
    "long_term",
    "api_endpoints",
    "frontend_lineage",
    "react_build",
):
    if not checks[name].get("ok"):
        failures.append(name)

verdict = "PASS" if not failures else "FAIL"

report = {
    "control": (
        "RC1_07E_GLOBAL_POST_REMEDIATION_CERTIFICATION"
    ),
    "verdict": verdict,
    "failure_count": len(failures),
    "failures": failures,
    "checks": checks,
    "audited_at_utc": utc_now(),
}

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)
REPORT_PATH.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print()
print("===== COMPACT RESULTS =====")
print(
    "SERVICES="
    + (
        "PASS"
        if checks["services"]["ok"]
        else "FAIL"
    )
)
print(
    "EXECUTION_PLAN="
    + (
        "PASS"
        if checks["execution_plan"]["ok"]
        else "FAIL"
    )
)
print(
    "EXECUTION_PLAN_SIMULATED="
    + (
        "PASS"
        if checks[
            "execution_plan_simulated"
        ]["ok"]
        else "FAIL"
    )
)
print(
    "LONG_TERM="
    + (
        "PASS"
        if checks["long_term"]["ok"]
        else "FAIL"
    )
)
print(
    "API_ENDPOINTS="
    + (
        "PASS"
        if checks["api_endpoints"]["ok"]
        else "FAIL"
    )
)
print(
    "FRONTEND_LINEAGE="
    + (
        "PASS"
        if checks["frontend_lineage"]["ok"]
        else "FAIL"
    )
)
print(
    "REACT_BUILD="
    + (
        "PASS"
        if checks["react_build"]["ok"]
        else "FAIL"
    )
)

print()
print("===== FINAL RESULT =====")
print(
    "CONTROL="
    "RC1_07E_GLOBAL_POST_REMEDIATION_CERTIFICATION"
)
print(f"FAILURE_COUNT={len(failures)}")
print(
    "FAILURES="
    + (
        ",".join(failures)
        if failures
        else "NONE"
    )
)
print(f"REPORT={REPORT_PATH}")
print(f"VERDICT={verdict}")
print(f"AUDITED_AT_UTC={report['audited_at_utc']}")

sys.exit(0 if verdict == "PASS" else 1)
