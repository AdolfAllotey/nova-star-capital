# src/v2/metrics/equity_curve_writer.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.v2.utils.file_utils import get_data_dir
from src.v2.utils.logger import get_logger

logger = get_logger("equity_curve_writer")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read_json(path: Path) -> Optional[Any]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[equity_curve] failed to read {path}: {e}")
        return None


def _try_extract_number(obj: Any, keys: list[str]) -> Optional[float]:
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, (int, float)):
                return float(v)
    return None


@dataclass
class EquityPoint:
    ts: str
    equity: float
    nav: float
    pnl_day: Optional[float] = None
    pnl_total: Optional[float] = None
    cash: Optional[float] = None
    positions_value: Optional[float] = None
    fees_total: Optional[float] = None
    source: str = "pipeline"
    run_id: Optional[str] = None


class EquityCurveWriter:
    """
    Writer robuste :
    - essaye de déduire l'equity depuis plusieurs fichiers.
    - fallback via NSC_INITIAL_EQUITY + pnl_total.
    - écrit en JSONL append-only.
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self.data_dir = Path(data_dir or get_data_dir())
        self.metrics_dir = self.data_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.metrics_dir / "equity_curve.jsonl"

    def _load_last_equity(self) -> Optional[float]:
        try:
            if not self.path.exists():
                return None
            # lit la dernière ligne non vide
            with self.path.open("rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size == 0:
                    return None
                # remonte jusqu'à trouver un \n
                offset = min(4096, size)
                f.seek(-offset, os.SEEK_END)
                chunk = f.read().decode("utf-8", errors="ignore")
            lines = [ln for ln in chunk.splitlines() if ln.strip()]
            if not lines:
                return None
            last = json.loads(lines[-1])
            if isinstance(last, dict) and isinstance(last.get("equity"), (int, float)):
                return float(last["equity"])
            return None
        except Exception as e:
            logger.warning(f"[equity_curve] failed to load last equity: {e}")
            return None

    def _resolve_from_known_files(self) -> Dict[str, Optional[float]]:
        """
        Ajuste ici si tu as déjà des fichiers plus précis.
        On met volontairement plusieurs chemins possibles.
        """
        candidates = [
            # portfolio/nav/equity éventuels
            self.data_dir / "portfolio" / "nav.json",
            self.data_dir / "portfolio" / "equity.json",
            self.data_dir / "portfolio" / "summary.json",
            # pnl éventuel
            self.data_dir / "pnl" / "pnl.json",
            self.data_dir / "pnl.json",
            # open positions / simulation
            self.data_dir / "open_positions.json",
            self.data_dir / "simulation" / "open_positions.json",
        ]

        nav = None
        equity = None
        cash = None
        positions_value = None
        pnl_total = None
        pnl_day = None
        fees_total = None

        for p in candidates:
            obj = _safe_read_json(p)
            if obj is None:
                continue

            # NAV / equity
            if nav is None:
                nav = _try_extract_number(obj, ["nav", "NAV", "equity", "equity_value", "portfolio_value", "total_value"])
            if equity is None:
                equity = _try_extract_number(obj, ["equity", "equity_value", "nav", "total_value", "portfolio_value"])

            # cash / positions
            if cash is None:
                cash = _try_extract_number(obj, ["cash", "cash_value", "available_cash", "free_cash"])
            if positions_value is None:
                positions_value = _try_extract_number(obj, ["positions_value", "positionsValue", "invested", "open_positions_value"])

            # pnl
            if pnl_total is None:
                pnl_total = _try_extract_number(obj, ["pnl_total", "pnlTotal", "total_pnl", "pnl"])
            if pnl_day is None:
                pnl_day = _try_extract_number(obj, ["pnl_day", "pnlDay", "daily_pnl", "pnl_24h"])
            if fees_total is None:
                fees_total = _try_extract_number(obj, ["fees_total", "feesTotal", "total_fees", "fees"])

        return {
            "nav": nav,
            "equity": equity,
            "cash": cash,
            "positions_value": positions_value,
            "pnl_total": pnl_total,
            "pnl_day": pnl_day,
            "fees_total": fees_total,
        }

    def write_point(self, source: str = "pipeline", run_id: Optional[str] = None) -> EquityPoint:
        resolved = self._resolve_from_known_files()

        nav = resolved["nav"]
        equity = resolved["equity"]
        cash = resolved["cash"]
        positions_value = resolved["positions_value"]
        pnl_total = resolved["pnl_total"]
        pnl_day = resolved["pnl_day"]
        fees_total = resolved["fees_total"]

        # 1) equity explicite
        if equity is None and nav is not None:
            equity = nav

        # 2) cash + positions_value
        if equity is None and cash is not None and positions_value is not None:
            equity = cash + positions_value

        # 3) initial_equity + pnl_total
        if equity is None and pnl_total is not None:
            try:
                initial = float(os.getenv("NSC_INITIAL_EQUITY", "10000"))
            except Exception:
                initial = 10000.0
            equity = initial + pnl_total

        # 4) fallback last equity
        if equity is None:
            last = self._load_last_equity()
            if last is not None:
                logger.warning("[equity_curve] no equity source found -> fallback to last_equity")
                equity = last
            else:
                logger.warning("[equity_curve] no equity source found -> fallback to NSC_INITIAL_EQUITY")
                equity = float(os.getenv("NSC_INITIAL_EQUITY", "10000"))

        if nav is None:
            nav = equity

        point = EquityPoint(
            ts=_utc_now_iso(),
            equity=float(equity),
            nav=float(nav),
            pnl_day=pnl_day,
            pnl_total=pnl_total,
            cash=cash,
            positions_value=positions_value,
            fees_total=fees_total,
            source=source,
            run_id=run_id,
        )

        # append JSONL
        payload = {
            "ts": point.ts,
            "equity": point.equity,
            "nav": point.nav,
            "pnl_day": point.pnl_day,
            "pnl_total": point.pnl_total,
            "cash": point.cash,
            "positions_value": point.positions_value,
            "fees_total": point.fees_total,
            "source": point.source,
            "run_id": point.run_id,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        return point


def write_equity_point(source: str = "pipeline", run_id: Optional[str] = None) -> Dict[str, Any]:
    writer = EquityCurveWriter()
    p = writer.write_point(source=source, run_id=run_id)
    return {
        "ts": p.ts,
        "equity": p.equity,
        "nav": p.nav,
        "pnl_day": p.pnl_day,
        "pnl_total": p.pnl_total,
        "cash": p.cash,
        "positions_value": p.positions_value,
        "fees_total": p.fees_total,
        "source": p.source,
        "run_id": p.run_id,
        "path": str(writer.path),
    }
