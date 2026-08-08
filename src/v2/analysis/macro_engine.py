from pathlib import Path
from datetime import datetime, timezone
import json
import yfinance as yf
import pandas as pd

OUT = Path("/opt/nsc/data/preprod/analysis/macro.json")

TICKERS = {
    "rates_10y": "^TNX",
    "dxy": "DX-Y.NYB",
    "gold": "GC=F",
}

def get_close(ticker):
    df = yf.download(
        ticker,
        period="160d",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if df is None or df.empty or "Close" not in df:
        return None

    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = pd.to_numeric(close, errors="coerce").dropna()
    return close if len(close) >= 60 else None

def compute_component(series, inverted=False):
    if series is None:
        return None, None, "missing"

    ma50 = float(series.rolling(50).mean().iloc[-1])
    last = float(series.iloc[-1])

    if last > ma50:
        score = -0.5 if not inverted else 0.3
        status = "above_ma50"
    else:
        score = 0.5 if not inverted else -0.3
        status = "below_ma50"

    return score, {"last": round(last, 4), "ma50": round(ma50, 4)}, status

def main():
    components = {}
    reasons = []
    total = 0.0
    usable = 0

    for key, ticker in TICKERS.items():
        series = get_close(ticker)

        # Pour l'or, hausse = stress/inflation hedge, donc score légèrement défensif si au-dessus MA50.
        inverted = key == "gold"
        score, values, status = compute_component(series, inverted=inverted)

        components[key] = {
            "ticker": ticker,
            "score": score,
            "status": status,
            "values": values,
        }

        if score is not None:
            total += score
            usable += 1
            reasons.append(f"{key}: {status}, score={score}")

    macro_score = round(total / usable, 4) if usable else 0.0

    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "yfinance",
        "engine": "macro_engine_v1",
        "score": macro_score,
        "status": "ok" if usable else "error",
        "usable": usable,
        "components": components,
        "reasons": reasons,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
