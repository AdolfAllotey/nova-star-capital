from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


CRYPTO_PATH = Path("/opt/nsc/app/data/portfolio/lt_portfolio.json")
EQUITIES_PATH = Path("/opt/nsc/app/data/portfolio/long_term_positions.json")

OUTPUT_PATH = Path("/opt/nsc/app/data/portfolio/long_term_valuation.json")

COMPATIBILITY_OUTPUTS = [
    Path("/opt/nsc/app/data/portfolio/lt_portfolio_valuation.json"),
    Path("/opt/nsc/src/v2/data/reports/long_term_valuation.json"),
]

BINANCE_SYMBOLS = {
    "BTC": "BTCEUR",
    "ETH": "ETHEUR",
    "SOL": "SOLEUR",
    "BNB": "BNBEUR",
    "XRP": "XRPEUR",
    "AVAX": "AVAXEUR",
}

YAHOO_TICKERS = {
    "QQQ": {"ticker": "QQQ", "fallback_currency": "USD"},
    "MSFT": {"ticker": "MSFT", "fallback_currency": "USD"},
    "NVDA": {"ticker": "NVDA", "fallback_currency": "USD"},
    "META": {"ticker": "META", "fallback_currency": "USD"},
    "AMZN": {"ticker": "AMZN", "fallback_currency": "USD"},
    "SPY": {"ticker": "SPY", "fallback_currency": "USD"},
    "COST": {"ticker": "COST", "fallback_currency": "USD"},
    "BRK.B": {"ticker": "BRK-B", "fallback_currency": "USD"},
    "VIG": {"ticker": "VIG", "fallback_currency": "USD"},
    "KO": {"ticker": "KO", "fallback_currency": "USD"},
    "JNJ": {"ticker": "JNJ", "fallback_currency": "USD"},
    "ASML": {"ticker": "ASML", "fallback_currency": "USD"},
    "TSMC": {"ticker": "TSM", "fallback_currency": "USD"},
    "LVMH": {"ticker": "MC.PA", "fallback_currency": "EUR"},
    "VWCE": {"ticker": "VWCE.DE", "fallback_currency": "EUR"},
    "IEUR": {"ticker": "IEUR", "fallback_currency": "USD"},
    "NESN": {"ticker": "NESN.SW", "fallback_currency": "CHF"},
    "AI": {"ticker": "AI.PA", "fallback_currency": "EUR"},
    "NOVO_B": {"ticker": "NOVO-B.CO", "fallback_currency": "DKK"},
}

FALLBACK_PRICES = {
    "BTC": {"price": 60000.0, "currency": "EUR"},
    "ETH": {"price": 3000.0, "currency": "EUR"},
    "SOL": {"price": 150.0, "currency": "EUR"},
    "BNB": {"price": 520.0, "currency": "EUR"},
    "XRP": {"price": 0.60, "currency": "EUR"},
    "AVAX": {"price": 35.0, "currency": "EUR"},
    "QQQ": {"price": 430.0, "currency": "USD"},
    "MSFT": {"price": 390.0, "currency": "USD"},
    "NVDA": {"price": 120.0, "currency": "USD"},
    "META": {"price": 480.0, "currency": "USD"},
    "AMZN": {"price": 175.0, "currency": "USD"},
    "SPY": {"price": 510.0, "currency": "USD"},
    "COST": {"price": 725.0, "currency": "USD"},
    "BRK.B": {"price": 410.0, "currency": "USD"},
    "VIG": {"price": 190.0, "currency": "USD"},
    "KO": {"price": 60.0, "currency": "USD"},
    "JNJ": {"price": 155.0, "currency": "USD"},
    "ASML": {"price": 950.0, "currency": "USD"},
    "TSMC": {"price": 145.0, "currency": "USD"},
    "LVMH": {"price": 820.0, "currency": "EUR"},
    "VWCE": {"price": 125.0, "currency": "EUR"},
    "IEUR": {"price": 58.0, "currency": "USD"},
    "NESN": {"price": 115.0, "currency": "CHF"},
    "AI": {"price": 185.0, "currency": "EUR"},
    "NOVO_B": {"price": 95.0, "currency": "DKK"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON source {path}: {exc}") from exc


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    json.loads(tmp_path.read_text(encoding="utf-8"))
    tmp_path.replace(path)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def fetch_binance_price(symbol_code: str) -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_code}"
    request = Request(url, headers={"User-Agent": "NSC-Long-Term/2.0"})

    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    price = safe_float(payload.get("price"), 0.0)
    if price <= 0:
        raise ValueError(f"Invalid Binance price for {symbol_code}")

    return price


def fetch_yahoo_quote(ticker: str) -> tuple[float, str | None]:
    encoded = quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
    request = Request(url, headers={"User-Agent": "NSC-Long-Term/2.0"})

    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = (((payload or {}).get("chart") or {}).get("result") or [None])[0] or {}
    meta = result.get("meta") or {}

    price = safe_float(meta.get("regularMarketPrice"), 0.0)
    currency = meta.get("currency")

    if price <= 0:
        raise ValueError(f"Invalid Yahoo price for {ticker}")

    return price, str(currency).upper() if currency else None


def fetch_fx_to_eur(currency: str) -> tuple[float, str]:
    currency = str(currency or "EUR").upper()

    if currency == "EUR":
        return 1.0, "identity"

    ticker = f"{currency}EUR=X"

    try:
        rate, returned_currency = fetch_yahoo_quote(ticker)
        if rate > 0:
            return rate, f"yahoo_{ticker}_{returned_currency or 'unknown'}"
    except Exception:
        pass

    fallback_rates = {
        "USD": 0.92,
        "CHF": 1.04,
        "DKK": 0.134,
        "GBP": 1.17,
    }

    if currency in fallback_rates:
        return fallback_rates[currency], f"fallback_{currency}_eur"

    raise RuntimeError(f"No FX conversion available for currency={currency}")


def resolve_price_eur(symbol: str, asset_class: str) -> dict[str, Any]:
    symbol = str(symbol or "").upper().strip()

    if not symbol:
        raise ValueError("Missing symbol")

    if asset_class == "crypto" and symbol in BINANCE_SYMBOLS:
        try:
            price = fetch_binance_price(BINANCE_SYMBOLS[symbol])
            return {
                "price_eur": price,
                "native_price": price,
                "native_currency": "EUR",
                "fx_to_eur": 1.0,
                "price_source": "binance_eur",
                "fallback_used": False,
            }
        except Exception:
            pass

    if symbol in YAHOO_TICKERS:
        config = YAHOO_TICKERS[symbol]
        ticker = config["ticker"]
        fallback_currency = config["fallback_currency"]

        try:
            native_price, returned_currency = fetch_yahoo_quote(ticker)
            native_currency = returned_currency or fallback_currency
            fx_rate, fx_source = fetch_fx_to_eur(native_currency)

            return {
                "price_eur": native_price * fx_rate,
                "native_price": native_price,
                "native_currency": native_currency,
                "fx_to_eur": fx_rate,
                "price_source": f"yahoo:{ticker}:{fx_source}",
                "fallback_used": False,
            }
        except Exception:
            pass

    fallback = FALLBACK_PRICES.get(symbol)

    if not fallback:
        raise RuntimeError(f"No price provider or fallback configured for symbol={symbol}")

    native_price = safe_float(fallback.get("price"), 0.0)
    native_currency = str(fallback.get("currency") or "EUR").upper()
    fx_rate, fx_source = fetch_fx_to_eur(native_currency)

    if native_price <= 0:
        raise RuntimeError(f"Invalid fallback price for symbol={symbol}")

    return {
        "price_eur": native_price * fx_rate,
        "native_price": native_price,
        "native_currency": native_currency,
        "fx_to_eur": fx_rate,
        "price_source": f"fallback:{symbol}:{fx_source}",
        "fallback_used": True,
    }


def normalize_crypto_positions(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Crypto LT source must be a JSON object")

    raw_positions = payload.get("positions") or {}

    if not isinstance(raw_positions, dict):
        raise RuntimeError("Crypto LT positions must be a symbol-keyed object")

    normalized = []

    for symbol, raw in raw_positions.items():
        if not isinstance(raw, dict):
            continue

        normalized.append({
            "position_id": f"lt_crypto_{str(symbol).upper()}",
            "symbol": str(symbol).upper(),
            "asset_name": str(symbol).upper(),
            "asset_class": "crypto",
            "bucket": "crypto_lt",
            "source_brick": "crypto",
            "invested_eur": safe_float(raw.get("invested_eur"), 0.0),
            "units": safe_float(raw.get("units"), 0.0),
            "avg_price_eur": safe_float(raw.get("avg_price_eur"), 0.0),
            "allocation_weight": safe_float(raw.get("weight"), 0.0),
            "custody_type": "simulated_portfolio",
            "custody_location": "PREPROD",
            "custody_status": "simulated",
            "status": "SIMULATED",
            "execution_mode": "SIMULATED_ONLY",
        })

    return normalized


def normalize_equity_positions(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Equities LT source must be a JSON object")

    raw_positions = payload.get("positions") or []

    if not isinstance(raw_positions, list):
        raise RuntimeError("Equities LT positions must be a list")

    normalized = []

    for raw in raw_positions:
        if not isinstance(raw, dict):
            continue

        row = dict(raw)
        row["asset_class"] = str(row.get("asset_class") or "equity")
        row["bucket"] = str(row.get("bucket") or "equities_lt")
        row["execution_mode"] = "SIMULATED_ONLY"
        row["simulation_status"] = "PREPROD_OBSERVATION"
        normalized.append(row)

    return normalized


def aggregate(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for row in rows:
        group = str(row.get(key) or "unknown")

        bucket = result.setdefault(group, {
            key: group,
            "invested_eur": 0.0,
            "market_value_eur": 0.0,
            "pnl_eur": 0.0,
            "positions": 0,
        })

        bucket["invested_eur"] += safe_float(row.get("invested_eur"), 0.0)
        bucket["market_value_eur"] += safe_float(row.get("market_value_eur"), 0.0)
        bucket["pnl_eur"] += safe_float(row.get("pnl_eur"), 0.0)
        bucket["positions"] += 1

    for bucket in result.values():
        bucket["invested_eur"] = round(bucket["invested_eur"], 6)
        bucket["market_value_eur"] = round(bucket["market_value_eur"], 6)
        bucket["pnl_eur"] = round(bucket["pnl_eur"], 6)

    return result


def main() -> dict[str, Any]:
    crypto_payload = read_json(CRYPTO_PATH, {})
    equities_payload = read_json(EQUITIES_PATH, {})

    source_positions = (
        normalize_crypto_positions(crypto_payload)
        + normalize_equity_positions(equities_payload)
    )

    enriched_positions = []
    provider_errors = []
    fallback_symbols = []

    for position in source_positions:
        symbol = str(position.get("symbol") or "").upper()
        asset_class = str(position.get("asset_class") or "unknown")

        try:
            price = resolve_price_eur(symbol, asset_class)
        except Exception as exc:
            provider_errors.append({
                "symbol": symbol,
                "error": str(exc),
            })
            continue

        invested_eur = safe_float(position.get("invested_eur"), 0.0)
        units = safe_float(position.get("units"), 0.0)
        current_price_eur = safe_float(price.get("price_eur"), 0.0)

        market_value_eur = units * current_price_eur
        pnl_eur = market_value_eur - invested_eur
        pnl_pct = pnl_eur / invested_eur if invested_eur > 0 else 0.0

        if price.get("fallback_used"):
            fallback_symbols.append(symbol)

        enriched_positions.append({
            **position,
            "current_price_eur": round(current_price_eur, 6),
            "native_price": round(safe_float(price.get("native_price"), 0.0), 6),
            "native_currency": price.get("native_currency"),
            "fx_to_eur": round(safe_float(price.get("fx_to_eur"), 1.0), 8),
            "market_value_eur": round(market_value_eur, 6),
            "pnl_eur": round(pnl_eur, 6),
            "pnl_pct": round(pnl_pct, 6),
            "price_source": price.get("price_source"),
            "fallback_used": bool(price.get("fallback_used")),
            "last_price_update": utc_now(),
        })

    expected_count = len(source_positions)
    valued_count = len(enriched_positions)

    if valued_count != expected_count:
        raise RuntimeError(
            f"Incomplete valuation: expected={expected_count}, "
            f"valued={valued_count}, errors={provider_errors}"
        )

    invested_total = sum(
        safe_float(row.get("invested_eur"), 0.0)
        for row in enriched_positions
    )
    market_total = sum(
        safe_float(row.get("market_value_eur"), 0.0)
        for row in enriched_positions
    )
    pnl_total = market_total - invested_total
    pnl_pct_total = pnl_total / invested_total if invested_total > 0 else 0.0

    crypto_count = sum(
        1 for row in enriched_positions
        if row.get("asset_class") == "crypto"
    )
    equity_count = sum(
        1 for row in enriched_positions
        if row.get("asset_class") == "equity"
    )

    result = {
        "status": "ok",
        "engine": "long_term_consolidator_v2",
        "environment": "PREPROD",
        "execution_mode": "SIMULATED_ONLY",
        "currency": "EUR",
        "source_files": {
            "crypto_lt": str(CRYPTO_PATH),
            "equities_lt": str(EQUITIES_PATH),
        },
        "source_position_counts": {
            "crypto_lt": crypto_count,
            "equities_lt": equity_count,
            "total": valued_count,
        },
        "totals": {
            "invested_eur": round(invested_total, 6),
            "cost_basis_eur": round(invested_total, 6),
            "market_value_eur": round(market_total, 6),
            "current_value_eur": round(market_total, 6),
            "pnl_eur": round(pnl_total, 6),
            "profit_eur": round(pnl_total, 6),
            "unrealized_pnl_eur": round(pnl_total, 6),
            "pnl_pct": round(pnl_pct_total, 6),
            "unrealized_pnl_pct": round(pnl_pct_total, 6),
            "positions": valued_count,
            "assets_count": valued_count,
        },
        "by_asset_class": aggregate(enriched_positions, "asset_class"),
        "by_source_brick": aggregate(enriched_positions, "source_brick"),
        "positions": enriched_positions,
        "data_quality": {
            "expected_positions": expected_count,
            "valued_positions": valued_count,
            "complete": valued_count == expected_count,
            "fallback_symbols": sorted(set(fallback_symbols)),
            "fallback_count": len(fallback_symbols),
            "provider_errors": provider_errors,
        },
        "updated_at": utc_now(),
    }

    write_json_atomic(OUTPUT_PATH, result)

    for compatibility_path in COMPATIBILITY_OUTPUTS:
        compatibility_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(OUTPUT_PATH, compatibility_path)

        copied = read_json(compatibility_path, {})
        if copied.get("engine") != "long_term_consolidator_v2":
            raise RuntimeError(
                f"Compatibility publication failed: {compatibility_path}"
            )

    return result


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
