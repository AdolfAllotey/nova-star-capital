# src/v2/market/price_fetcher_crypto.py

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request


def _load_data_dir() -> Path:
    # CLI --data-dir has priority
    import sys
    if "--data-dir" in sys.argv:
        try:
            return Path(sys.argv[sys.argv.index("--data-dir") + 1]).expanduser().resolve()
        except Exception:
            pass

    # env fallback
    env_dd = (os.getenv("NSC_DATA_DIR") or "").strip()
    if env_dd:
        return Path(env_dd).expanduser().resolve()

    # default
    return Path("/opt/nsc/app/data").resolve()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _http_get_json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NSC/price_fetcher_crypto"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8", errors="replace")
    return json.loads(data)


def _normalize_symbol(sym: str) -> str:
    return str(sym or "").strip().lower()


def _to_binance_symbol(sym: str) -> Optional[str]:
    """
    Accepts: 'maticusdt', 'MATICUSDT', 'MATIC' -> returns 'MATICUSDT'
    For now we only support USDT pairs.
    """
    s = str(sym or "").strip().upper()
    if not s:
        return None
    if s.endswith("USDT"):
        return s
    # assume base asset, force USDT
    return f"{s}USDT"


def fetch_prices_binance(symbols: List[str]) -> Dict[str, float]:
    """
    Binance endpoint: /api/v3/ticker/price?symbol=XXX
    We'll call per symbol (simple & robust).
    """
    out: Dict[str, float] = {}
    for sym in symbols:
        bs = _to_binance_symbol(sym)
        if not bs:
            continue
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={bs}"
        try:
            obj = _http_get_json(url, timeout=10)
            px = obj.get("price")
            if px is None:
                continue
            v = float(px)
            if v > 0:
                # store in lowercase, keeping "maticusdt" style
                out[_normalize_symbol(sym if sym.lower().endswith("usdt") else bs)] = v
        except Exception:
            continue
    return out


def main() -> int:
    data_dir = _load_data_dir()
    trading_dir = data_dir / "trading"
    market_dir = data_dir / "market"
    prices_path = market_dir / "prices.json"

    # universe tokens source: sized_signals symbols OR selected_tokens.json if you prefer
    sized_path = trading_dir / "sized_signals.json"
    sized = _read_json(sized_path, default=[]) or []
    syms: List[str] = []
    if isinstance(sized, list):
        for it in sized:
            if isinstance(it, dict) and it.get("symbol"):
                syms.append(str(it["symbol"]))
    # dedup
    syms = list(dict.fromkeys(syms))

    prices = fetch_prices_binance(syms)

    obj = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "binance",
        "universe": os.getenv("NSC_UNIVERSE", "unknown"),
        "prices": prices,
    }
    _write_json(prices_path, obj)

    print(f"[price_fetcher_crypto] wrote {len(prices)} prices -> {prices_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
