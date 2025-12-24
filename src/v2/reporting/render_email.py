from __future__ import annotations
import json, csv
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import OrderedDict

# Paths
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "src" / "v2" / "data"
REPORTS = DATA / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

JSON_IN   = REPORTS / "daily_report.json"
HTML_OUT  = REPORTS / "daily_report.html"
TEXT_OUT  = REPORTS / "daily_report.txt"
PNL_CSV   = DATA / "reporting" / "monthly_pnl.csv"

def now_paris():
    return datetime.now(ZoneInfo("Europe/Paris"))

def fmt_int(n: float | int) -> str:
    try:
        return f"{int(float(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def fmt_money(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return f"{v} USD"
    sign = "+" if v >= 0 else "−"
    return f"{sign}{abs(v):,.2f} USD".replace(",", " ")

def badge(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        v = 0.0
    if v > 0: return "🟢"
    if v < 0: return "🔴"
    return "⚪️"

def load_payload() -> dict:
    try:
        return json.loads(JSON_IN.read_text(encoding="utf-8"))
    except Exception:
        # Fallback minimal
        return {
            "generated_at": now_paris().isoformat(),
            "social": {"telegram": 0, "reddit": 0},
            "sentiment": {"score": 0.0, "generated_at": ""},
            "trades": {"last_48h": 0, "worst_count": 0},
            "pnl_usd": {"today": 0.0, "mtd": 0.0, "all_time": 0.0},
        }

def load_last_7_pnl(csv_path: Path = PNL_CSV):
    """
    Lit monthly_pnl.csv et retient LA DERNIÈRE valeur rencontrée pour chaque date,
    puis renvoie les 7 dernières dates (triées ascendant) + total.
    """
    if not csv_path.exists():
        return [], 0.0

    # On conserve la dernière valeur par date (ordre du fichier = append)
    last_by_date: "OrderedDict[str, float]" = OrderedDict()
    try:
        with csv_path.open(newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                d = (row.get("date") or "").strip()
                v = row.get("pnl_usd")
                if not d or v in (None, ""):
                    continue
                try:
                    val = float(v)
                except Exception:
                    continue
                last_by_date[d] = val  # overwrite => dernière occurrence gagnante
    except Exception:
        return [], 0.0

    # On prend les 7 dernières dates
    items = list(last_by_date.items())
    last7 = items[-7:]
    total7 = sum(v for _, v in last7)
    # On renvoie en ordre chronologique (ascendant)
    return last7, total7

def row_badge_class(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        v = 0.0
    return "pos" if v > 0 else "neg" if v < 0 else "neu"

def build_email_html(p: dict) -> str:
    d = now_paris()
    ds = d.strftime("%Y-%m-%d")
    tm = d.strftime("%H:%M")
    tg = fmt_int(p.get("social", {}).get("telegram", 0))
    rd = fmt_int(p.get("social", {}).get("reddit", 0))
    score = float(p.get("sentiment", {}).get("score", 0) or 0)
    score_gen = p.get("sentiment", {}).get("generated_at", "")
    trades48 = fmt_int(p.get("trades", {}).get("last_48h", 0))
    worst = fmt_int(p.get("trades", {}).get("worst_count", 0))
    pnl_today = float(p.get("pnl_usd", {}).get("today", 0) or 0)
    pnl_mtd   = float(p.get("pnl_usd", {}).get("mtd", 0) or 0)
    pnl_all   = float(p.get("pnl_usd", {}).get("all_time", 0) or 0)

    last7, total7 = load_last_7_pnl()

    # construit les lignes HTML du tableau 7j
    rows_html = ""
    for dstr, val in last7:
        rows_html += f"""
          <tr>
            <td class="td-date">{dstr}</td>
            <td class="td-pnl">
              <span class="pill {row_badge_class(val)}">{badge(val)}</span>
              <span class="amount">{fmt_money(val)}</span>
            </td>
          </tr>"""

    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Rapport quotidien — {ds}</title>
  <style>
    /* Reset email-friendly */
    body,table,td,div,p,a {{ margin:0; padding:0; }}
    img {{ border:0; height:auto; line-height:100%; outline:none; text-decoration:none; }}
    table {{ border-collapse:collapse !important; }}
    body {{ width:100% !important; height:100% !important; }}

    /* Container */
    .wrapper {{
      width:100%;
      background:#0b1220;
      background:linear-gradient(180deg,#0b1220 0%, #0e1629 100%);
      padding:24px 12px;
    }}
    @media (prefers-color-scheme: light) {{
      .wrapper {{ background:#f5f7fb; background-image:none; }}
    }}
    .card {{
      max-width:640px; margin:0 auto; background:#121a2b; border-radius:16px;
      border:1px solid rgba(255,255,255,0.06); overflow:hidden;
    }}
    @media (prefers-color-scheme: light) {{
      .card {{ background:#ffffff; border-color:#eaecef; }}
    }}
    .header {{
      padding:20px 24px; border-bottom:1px solid rgba(255,255,255,0.08);
      background:linear-gradient(90deg, rgba(0,167,255,.1), rgba(165,105,255,.1));
    }}
    @media (prefers-color-scheme: light) {{
      .header {{ border-bottom-color:#f0f2f5; }}
    }}
    .h1 {{
      font-family:ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica, Arial;
      font-size:22px; font-weight:700; color:#e6edf3; letter-spacing:.2px;
    }}
    @media (prefers-color-scheme: light) {{
      .h1 {{ color:#111827; }}
    }}
    .muted {{ color:#9fb0c3; font-size:13px; }}
    @media (prefers-color-scheme: light) {{
      .muted {{ color:#6b7280; }}
    }}
    .content {{ padding:20px 24px; }}
    .grid {{ width:100%; }}
    .tile {{
      width:100%; border:1px solid rgba(255,255,255,0.06); border-radius:12px;
      padding:16px; margin-bottom:12px;
      background:rgba(255,255,255,0.02);
    }}
    @media (prefers-color-scheme: light) {{
      .tile {{ background:#fff; border-color:#eef2f7; }}
    }}
    .tile h3 {{ margin:0 0 8px 0; font-size:16px; color:#e6edf3; }}
    @media (prefers-color-scheme: light) {{
      .tile h3 {{ color:#1f2937; }}
    }}
    .kv {{ font-size:14px; line-height:1.6; color:#d2dde9; }}
    @media (prefers-color-scheme: light) {{
      .kv {{ color:#374151; }}
    }}
    .pill {{
      display:inline-block; padding:2px 8px; border-radius:999px;
      font-size:12px; margin-right:6px; border:1px solid rgba(255,255,255,0.14);
      color:#e6edf3;
    }}
    .pill.pos {{ background:rgba(16,185,129,.15); border-color:rgba(16,185,129,.3); }}
    .pill.neg {{ background:rgba(239,68,68,.15);  border-color:rgba(239,68,68,.3); }}
    .pill.neu {{ background:rgba(148,163,184,.15); border-color:rgba(148,163,184,.3); }}

    /* Table 7 jours */
    .tbl7 {{ width:100%; }}
    .tbl7 th, .tbl7 td {{
      font-size:14px; padding:8px 10px; text-align:left;
      border-bottom:1px solid rgba(255,255,255,0.06);
      color:#d2dde9;
    }}
    .tbl7 th {{ font-weight:600; color:#e6edf3; }}
    .td-date {{ white-space:nowrap; }}
    .td-pnl .amount {{ font-variant-numeric: tabular-nums; }}
    .total-row td {{ font-weight:700; }}

    @media (prefers-color-scheme: light) {{
      .tbl7 th, .tbl7 td {{ color:#374151; border-bottom-color:#eef2f7; }}
      .pill {{ color:#111827; }}
    }}

    .footer {{
      padding:16px 24px; font-size:12px; color:#8aa0b6; text-align:center;
      border-top:1px solid rgba(255,255,255,0.08);
    }}
    @media (prefers-color-scheme: light) {{
      .footer {{ color:#6b7280; border-top-color:#f0f2f5; }}
    }}

    /* Mobile */
    @media only screen and (max-width: 520px) {{
      .content {{ padding:16px; }}
      .header {{ padding:16px; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card" role="article" aria-roledescription="email">
      <div class="header">
        <div class="h1">🌌 Rapport quotidien — {ds}</div>
        <div class="muted">Généré à {tm} (Europe/Paris)</div>
      </div>

      <div class="content">
        <table class="grid" role="presentation" cellpadding="0" cellspacing="0">
          <tr><td>
            <div class="tile">
              <h3>🛰️ Activité Social (48h)</h3>
              <div class="kv">Telegram : <strong>{tg}</strong> &nbsp;•&nbsp; Reddit : <strong>{rd}</strong></div>
            </div>

            <div class="tile">
              <h3>🧠 Sentiment</h3>
              <div class="kv">Score : <code>{score:.4f}</code></div>
              {"<div class='kv'>Calculé : " + score_gen + "</div>" if score_gen else ""}
            </div>

            <div class="tile">
              <h3>📊 Trades</h3>
              <div class="kv">Total (48h) : <strong>{trades48}</strong> &nbsp;•&nbsp; ⚠️ Pires trades : <strong>{worst}</strong></div>
            </div>

            <div class="tile">
              <h3>💹 PnL (USD)</h3>
              <div class="kv">
                Aujourd’hui : <strong>{fmt_money(pnl_today)}</strong>
                <span class="pill {'pos' if pnl_today>0 else 'neg' if pnl_today<0 else 'neu'}">{badge(pnl_today)}</span>
              </div>
              <div class="kv">
                Mois (MTD) : <strong>{fmt_money(pnl_mtd)}</strong>
                <span class="pill {'pos' if pnl_mtd>0 else 'neg' if pnl_mtd<0 else 'neu'}">{badge(pnl_mtd)}</span>
              </div>
              <div class="kv">
                Cumul : <strong>{fmt_money(pnl_all)}</strong>
                <span class="pill {'pos' if pnl_all>0 else 'neg' if pnl_all<0 else 'neu'}">{badge(pnl_all)}</span>
              </div>
            </div>

            <div class="tile">
              <h3>📆 PnL — 7 derniers jours</h3>
              <table class="tbl7" role="presentation" cellpadding="0" cellspacing="0" aria-label="PnL des 7 derniers jours">
                <thead>
                  <tr><th>Date</th><th>Résultat</th></tr>
                </thead>
                <tbody>
                  {rows_html}
                  <tr class="total-row">
                    <td>Total 7j</td>
                    <td><span class="pill {'pos' if total7>0 else 'neg' if total7<0 else 'neu'}">{badge(total7)}</span>
                        <span class="amount">{fmt_money(total7)}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

          </td></tr>
        </table>
      </div>

      <div class="footer">
        ✨ Nova Star — Email auto-généré • Réf: daily_report.html
      </div>
    </div>
  </div>
</body>
</html>"""
    return html

def build_text_fallback(p: dict) -> str:
    d = now_paris()
    ds = d.strftime("%Y-%m-%d")
    tm = d.strftime("%H:%M")
    tg = p.get("social", {}).get("telegram", 0)
    rd = p.get("social", {}).get("reddit", 0)
    score = float(p.get("sentiment", {}).get("score", 0) or 0)
    trades48 = p.get("trades", {}).get("last_48h", 0)
    worst = p.get("trades", {}).get("worst_count", 0)
    pnl = p.get("pnl_usd", {})
    last7, total7 = load_last_7_pnl()

    lines7 = "\n".join([f"  - {dstr}: {fmt_money(val)}" for dstr, val in last7])
    return (
        f"Rapport quotidien — {ds}\n"
        f"Gen: {tm} (Europe/Paris)\n"
        f"Social 48h: Telegram={tg}, Reddit={rd}\n"
        f"Sentiment: {score:.4f}\n"
        f"Trades 48h: {trades48} | Pires: {worst}\n"
        f"PnL: Today={fmt_money(pnl.get('today',0))}, "
        f"MTD={fmt_money(pnl.get('mtd',0))}, All={fmt_money(pnl.get('all_time',0))}\n"
        f"PnL 7j:\n{lines7}\n"
        f"Total 7j: {fmt_money(total7)}\n"
        f"Nova Star"
    )

def main():
    payload = load_payload()
    HTML_OUT.write_text(build_email_html(payload), encoding="utf-8")
    TEXT_OUT.write_text(build_text_fallback(payload), encoding="utf-8")
    print(json.dumps({"html": str(HTML_OUT), "text": str(TEXT_OUT)}))

if __name__ == "__main__":
    main()
