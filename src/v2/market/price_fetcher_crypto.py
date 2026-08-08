from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request


def _load_data_dir() -> Path:
    import sys

    if "--data-dir" in sys.argv:
        try:
            return Path(sys.argv[sys.argv.index("--data-dir") + 1]).expanduser().resolve()
        except Exception:
            pass

    env_dd = (os.getenv("NSC_DATA_DIR") or "").strip()
    if env_dd:
        return Path(env_dd).expanduser().resolve()

    return Path("/opt/nsc/data/preprod").resolve()


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


def _to_binance_symbol(sym: str) -> Optional[str]:
    s = str(sym or "").strip().upper()
    if not s:
        return None
    if s.endswith("USDT"):
        return s
    return f"{s}USDT"


def fetch_prices_binance(symbols: List[str]) -> Dict[str, float]:
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
                out[str(sym).upper()] = v
        except Exception as e:
            print(f"[price_fetcher_crypto] fetch failed for {sym}: {e}")
            continue
    return out


def _extract_symbols(items: Any) -> List[str]:
    out: List[str] = []
    if not isinstance(items, list):
        return out

    for it in items:
        if not isinstance(it, dict):
            continue

        candidate = (
            it.get("symbol")
            or it.get("token")
            or it.get("asset")
            or it.get("ticker")
        )
        if not candidate:
            continue

        s = str(candidate).strip().upper()
        if s.endswith("USDT"):
            s = s[:-4]
        if s and s.isascii() and s.replace("_", "").isalnum():
            out.append(s)

    return list(dict.fromkeys(out))


def _extract_symbols_from_selected(doc: Any) -> List[str]:
    if not isinstance(doc, dict):
        return []
    items = doc.get("items", [])
    return _extract_symbols(items)


def main() -> int:
    data_dir = _load_data_dir()
    trading_dir = data_dir / "trading"
    market_dir = data_dir / "market"

    prices_path = market_dir / "prices.json"
    crypto_spot_prices_path = market_dir / "crypto_spot_prices.json"

    selected_path = trading_dir / "selected_tokens.dynamic.json"
    sized_path = trading_dir / "sized_signals.json"
    candidates_path = data_dir / "analysis" / "signal_candidates.json"

    selected = _read_json(selected_path, default={}) or {}
    sized = _read_json(sized_path, default=[]) or []
    candidates = _read_json(candidates_path, default=[]) or []

    # PREPROD MULTI-SOURCE RULE:
    # Prices must cover the full actionable crypto universe:
    # selected dynamic tokens + signal candidates + sized signals.
    syms_selected = _extract_symbols_from_selected(selected)
    syms_candidates = _extract_symbols(candidates)
    syms_sized = _extract_symbols(sized)
    syms_trades = []

    syms = list(dict.fromkeys(syms_selected + syms_candidates + syms_sized))

    print(f"[price_fetcher_crypto] symbols_from_selected={syms_selected}")
    print(f"[price_fetcher_crypto] symbols_from_candidates={syms_candidates}")
    print(f"[price_fetcher_crypto] symbols_from_sized={syms_sized}")
    print(f"[price_fetcher_crypto] symbols_from_trades={syms_trades}")

    print(f"[price_fetcher_crypto] data_dir={data_dir}")
    print(f"[price_fetcher_crypto] selected_path={selected_path} exists={selected_path.exists()}")
    print(f"[price_fetcher_crypto] candidates_path={candidates_path} exists={candidates_path.exists()}")
    print(f"[price_fetcher_crypto] sized_path={sized_path} exists={sized_path.exists()}")
    print(f"[price_fetcher_crypto] symbols={syms}")

    prices = fetch_prices_binance(syms)

    legacy_obj = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "binance",
        "universe": os.getenv("NSC_UNIVERSE", "unknown"),
        "symbols": syms,
        "prices": prices,
    }

    _write_json(prices_path, legacy_obj)
    _write_json(crypto_spot_prices_path, prices)

    print(f"[price_fetcher_crypto] wrote {len(prices)} prices -> {prices_path}")
    print(f"[price_fetcher_crypto] wrote {len(prices)} prices -> {crypto_spot_prices_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
