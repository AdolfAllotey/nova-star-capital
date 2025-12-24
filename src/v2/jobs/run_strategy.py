# src/v2/jobs/run_strategy.py
from __future__ import annotations
import argparse, asyncio, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

DEFAULT_BASE = os.getenv("NSC_API_BASE", "http://127.0.0.1:8000")

async def fetch_json(client: httpx.AsyncClient, url: str, params: dict):
    r = await client.get(url, params=params)
    r.raise_for_status()
    return r.json()

async def main():
    p = argparse.ArgumentParser(description="Run strategy and persist results")
    p.add_argument("--base", default=DEFAULT_BASE, help="Base URL de l'API")
    p.add_argument("--tf", default="1h")
    p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT")
    p.add_argument("--lookback", type=int, default=96)
    p.add_argument("--out", default="/var/log/nsc/strategy")
    p.add_argument("--timeout", type=float, default=20.0)
    args = p.parse_args()

    base = args.base.rstrip("/")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts_run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    async with httpx.AsyncClient(timeout=args.timeout, follow_redirects=True) as client:
        # Sanity: service up ?
        ready = await fetch_json(client, f"{base}/ready", {})
        # Strategy mock=0 -> réel (via OHLCV_URL)
        strat = await fetch_json(
            client,
            f"{base}/api/strategy/top",
            {"mock": "0", "tf": args.tf, "limit": str(args.lookback)}
        )

    # Enrichit et sauvegarde
    payload = {
        "run_ts": ts_run,
        "base": base,
        "tf": args.tf,
        "lookback": args.lookback,
        "symbols": [s.strip() for s in args.symbols.split(",") if s.strip()],
        "ready": ready,
        "strategy": strat,
    }

    # Dossiers par jour
    day_dir = out_dir / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    # JSON brut
    json_path = day_dir / f"strategy_{ts_run}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    # CSV plat (symbol,score)
    picks = payload.get("strategy", {}).get("picks", [])
    csv_lines = ["symbol,score"]
    for p in picks:
        csv_lines.append(f'{p.get("symbol")},{p.get("score")}')
    (day_dir / f"picks_{ts_run}.csv").write_text("\n".join(csv_lines))

    # Log léger en stdout (utilisable par systemd-journald)
    print(f"[OK] run={ts_run} tf={args.tf} picks={len(picks)} ready={ready.get('ready')}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as e:
        print(f"[ERR] {e}", file=sys.stderr)
        raise
