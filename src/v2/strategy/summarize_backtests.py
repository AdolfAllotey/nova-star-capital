# -*- coding: utf-8 -*-
"""
Consolide les résultats des backtests (metrics.json) en un tableau synthétique.

Entrées:
  - Dossiers: src/v2/data/reports/backtests/<SYMBOL>_<TF>_<TS>/metrics.json

Sorties:
  - CSV: src/v2/data/reports/backtests/_summary/summary.csv (trié par sharpe desc)
  - Markdown: src/v2/data/reports/backtests/_summary/summary.md
"""

from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd

REPORTS_DIR = Path(__file__).resolve().parents[1] / "data" / "reports" / "backtests"
OUT_DIR = REPORTS_DIR / "_summary"
OUT_DIR.mkdir(parents=True, exist_ok=True)

rows = []
pattern = re.compile(r"^(?P<symbol>[A-Z0-9]+)_(?P<tf>[0-9]+[smhdw])_(?P<ts>\d{8}T\d{6}Z)$")

for d in REPORTS_DIR.iterdir():
    if not d.is_dir() or d.name.startswith("_"):
        continue
    m = pattern.match(d.name)
    if not m:
        continue
    metrics_path = d / "metrics.json"
    if not metrics_path.exists():
        continue

    with metrics_path.open("r") as f:
        metrics = json.load(f)

    rows.append({
        "symbol": m["symbol"],
        "tf": m["tf"],
        "ts": m["ts"],
        "trades": metrics.get("trades"),
        "winrate": metrics.get("winrate"),
        "pnl_pct": metrics.get("pnl_pct"),
        "max_dd_pct": metrics.get("max_dd_pct"),
        "sharpe": metrics.get("sharpe"),
        "avg_trade_return_pct": metrics.get("avg_trade_return_pct"),
        "eq_final": metrics.get("eq_final"),
    })

if not rows:
    print("Aucun metrics.json trouvé. Lance d'abord des backtests.")
    raise SystemExit(1)

df = pd.DataFrame(rows)
# Tri principal par Sharpe, puis PnL %
df = df.sort_values(by=["sharpe", "pnl_pct"], ascending=[False, False])

# Sauvegardes
csv_path = OUT_DIR / "summary.csv"
md_path = OUT_DIR / "summary.md"

df.to_csv(csv_path, index=False)

# Markdown
headers = ["symbol", "tf", "ts", "trades", "winrate", "pnl_pct", "max_dd_pct", "sharpe", "avg_trade_return_pct", "eq_final"]
md = "| " + " | ".join(headers) + " |\n"
md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
for _, r in df.iterrows():
    md += "| " + " | ".join(str(r[h]) if pd.notna(r[h]) else "" for h in headers) + " |\n"

md_path.write_text(md, encoding="utf-8")

print(f"✅ Consolidation terminée.")
print(f"   CSV : {csv_path}")
print(f"   MD  : {md_path}")
