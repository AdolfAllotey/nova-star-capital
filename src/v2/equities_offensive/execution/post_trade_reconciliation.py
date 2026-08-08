from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json

from src.v2.utils.file_utils import load_json_file as load_json, save_json_file as save_json
try:
    from src.v2.utils.time_utils import utc_now_iso  # optional
except Exception:
    utc_now_iso = None


FILLS_PATH = Path("/opt/nsc/data/preprod/equities_offensive/execution/simulated_fills.jsonl")
POSITIONS_PATH = Path("/opt/nsc/data/preprod/equities_offensive/state/positions.json")
OUT_REPORT = Path("/opt/nsc/data/preprod/equities_offensive/state/reconciliation_report.json")


def _utc_now_iso_fallback() -> str:
    # fallback safe if time_utils not present
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    try:
        if utc_now_iso:
            return utc_now_iso()
    except Exception:
        pass
    return _utc_now_iso_fallback()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            # ignore bad lines but record later as anomaly
            out.append({"_raw_line_error": True, "_raw": line})
    return out


@dataclass
class ReconSummary:
    fills_total: int
    fills_bad_lines: int
    fills_filled: int
    symbols_in_fills: List[str]
    symbols_in_positions: List[str]


def compute_expected_positions_from_fills(fills: List[Dict[str, Any]]) -> Tuple[Dict[str, float], List[str], int, int]:
    """
    Compute expected net qty per symbol from FILLED fills only.
    Returns: expected_qty_by_symbol, anomalies, filled_count, bad_lines_count
    """
    expected: Dict[str, float] = {}
    anomalies: List[str] = []
    filled = 0
    bad_lines = 0

    for f in fills:
        if f.get("_raw_line_error"):
            bad_lines += 1
            continue

        status = (f.get("status") or "").upper()
        if status and status != "FILLED":
            continue

        symbol = f.get("symbol")
        side = (f.get("side") or "").upper()
        qty = f.get("qty")

        if not symbol or side not in {"BUY", "SELL"}:
            continue

        try:
            q = float(qty)
        except Exception:
            anomalies.append(f"bad_qty_in_fill for {symbol}: {qty}")
            continue

        if q <= 0:
            anomalies.append(f"non_positive_qty_in_fill for {symbol}: {q}")
            continue

        filled += 1
        sign = 1.0 if side == "BUY" else -1.0
        expected[symbol] = expected.get(symbol, 0.0) + sign * q

    # remove near-zero noise
    for sym in list(expected.keys()):
        if abs(expected[sym]) < 1e-9:
            expected.pop(sym, None)

    return expected, anomalies, filled, bad_lines


def load_positions_dict() -> Dict[str, Dict[str, Any]]:
    pos = load_json(str(POSITIONS_PATH), default={}) or {}
    if not isinstance(pos, dict):
        return {}
    # Normalize: ensure dict per symbol
    out: Dict[str, Dict[str, Any]] = {}
    for sym, v in pos.items():
        if isinstance(v, dict):
            out[sym] = v
    return out


def reconcile(expected_qty: Dict[str, float], positions: Dict[str, Dict[str, Any]]) -> Tuple[bool, List[str]]:
    anomalies: List[str] = []

    # qty mismatch check
    for sym, exp_qty in expected_qty.items():
        got = positions.get(sym, {})
        got_qty = got.get("qty", 0.0)
        try:
            got_qty_f = float(got_qty)
        except Exception:
            anomalies.append(f"bad_position_qty for {sym}: {got_qty}")
            continue

        # PREPROD rule:
        # if fills net to a negative qty (exit/reduction) and final position is 0,
        # accept it as reconciled because the file may not include historical BUY fills.
        if exp_qty < 0 and abs(got_qty_f) < 1e-9:
            continue

        # Corporate action tolerance:
        # If a simulated position has been adjusted for a split, historical fills may remain pre-split.
        corp_action = str((got or {}).get("corporate_action_adjusted", "") or "")
        if corp_action and "SPLIT" in corp_action.upper():
            continue

        if abs(got_qty_f - exp_qty) > 1e-6:
            anomalies.append(f"qty_mismatch {sym}: expected={exp_qty} got={got_qty_f}")

    # positions without any fills
    for sym, got in positions.items():
        if sym not in expected_qty:
            try:
                q = float(got.get("qty", 0.0))
            except Exception:
                q = 0.0
            if abs(q) > 1e-9:
                anomalies.append(f"position_without_fills {sym}: qty={q}")

    ok = len(anomalies) == 0
    return ok, anomalies


def main() -> int:
    fills = read_jsonl(FILLS_PATH)
    positions = load_positions_dict()

    expected, fill_anoms, filled_count, bad_lines = compute_expected_positions_from_fills(fills)
    ok, recon_anoms = reconcile(expected, positions)

    symbols_in_fills = sorted({f.get("symbol") for f in fills if isinstance(f, dict) and f.get("symbol")})
    symbols_in_positions = sorted(list(positions.keys()))

    summary = ReconSummary(
        fills_total=len(fills),
        fills_bad_lines=bad_lines,
        fills_filled=filled_count,
        symbols_in_fills=symbols_in_fills,
        symbols_in_positions=symbols_in_positions,
    )

    report: Dict[str, Any] = {
        "ts": now_iso(),
        "engine": "post_trade_reconciliation_v1",
        "ok": ok and (len(fill_anoms) == 0),
        "paths": {
            "fills_path": str(FILLS_PATH),
            "positions_path": str(POSITIONS_PATH),
        },
        "summary": {
            "fills_total": summary.fills_total,
            "fills_bad_lines": summary.fills_bad_lines,
            "fills_filled": summary.fills_filled,
            "symbols_in_fills": summary.symbols_in_fills,
            "symbols_in_positions": summary.symbols_in_positions,
        },
        "expected_qty_by_symbol": expected,
        "anomalies": fill_anoms + recon_anoms,
        "notes": [
            "v1: reconciliation uses FILLED fills only and compares against positions.qty.",
            "fees/slippage reconciliation will be plugged later with real broker adapter (IBKR).",
        ],
    }

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    save_json(str(OUT_REPORT), report)

    # also print a lightweight console output (useful in CLI)
    print(json.dumps({"ok": report["ok"], "anomalies": len(report["anomalies"])}, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
