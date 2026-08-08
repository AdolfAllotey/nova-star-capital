from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd
import yfinance as yf

TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","AVGO","TSLA","BRK-B",
    "JPM","LLY","V","MA","XOM","COST","NFLX","WMT","PG","JNJ",
    "HD","ABBV","KO","BAC","ORCL","PLTR","CRM","CVX","AMD","PEP",
    "CSCO","TMO","MRK","MCD","ABT","LIN","DIS","INTU","IBM","GE"
]

OUT = Path("/opt/nsc/data/preprod/analysis/breadth.json")

def main():
    rows = []
    usable = 0
    above = 0
    errors = []

    for ticker in TICKERS:
        try:
            df = yf.download(
                ticker,
                period="320d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )

            if df is None or df.empty or len(df) < 210:
                errors.append({"ticker": ticker, "error": "not_enough_data", "rows": 0 if df is None else len(df)})
                continue

            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            ma200 = close.rolling(200).mean()
            last_close = float(close.iloc[-1])
            last_ma200 = float(ma200.iloc[-1])

            if not last_close or not last_ma200:
                errors.append({"ticker": ticker, "error": "invalid_last_values"})
                continue

            is_above = last_close > last_ma200
            usable += 1
            above += 1 if is_above else 0

            rows.append({
                "ticker": ticker,
                "close": round(last_close, 4),
                "ma200": round(last_ma200, 4),
                "above_ma200": is_above,
            })

        except Exception as e:
            errors.append({"ticker": ticker, "error": repr(e)})

    pct = (above / usable) if usable else None

    payload = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "yfinance",
        "universe": "us_large_caps_proxy",
        "tickers_total": len(TICKERS),
        "tickers_usable": usable,
        "above_ma200_count": above,
        "breadth_pct_above_ma200": pct,
        "status": "ok" if pct is not None else "error",
        "rows": rows,
        "errors": errors[:20],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
