# -*- coding: utf-8 -*-
"""
Backtest SMA crossover sur données OHLCV fournies par l'API v2.

- Lit le token dans NSC_API_TOKEN (obligatoire)
- Base API dans NSC_API_BASE (defaut: http://127.0.0.1:8000)
- Sauvegardes dans src/v2/data/reports/backtests/<symbol>_<tf>_<ts>/

Exemples:
  PYTHONPATH=src python -m v2.strategy.backtest \
    --symbols BTCUSDT,ETHUSDT --tf 15m,1h --days 30 \
    --fees 0.0004 --slippage 0.0002 --sma-fast 10 --sma-slow 20
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import requests

# --- plotting en mode serveur (PNG) ---
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


logger = logging.getLogger("v2.strategy.backtest")
if not logger.handlers:
    _h = logging.StreamHandler()
    _fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

THIS_FILE = Path(__file__).resolve()
V2_DIR = THIS_FILE.parents[1]
REPORTS_DIR = V2_DIR / "data" / "reports" / "backtests"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# nb de barres par jour
TF_BARS_PER_DAY: Dict[str, int] = {
    "1m": 1440,
    "5m": 288,
    "15m": 96,
    "30m": 48,
    "1h": 24,
    "4h": 6,
    "1d": 1,
}

# limites prudentes pour éviter 422 côté API (peuvent être ajustées)
TF_MAX_LIMIT: Dict[str, int] = {
    "1m": 1000,
    "5m": 2000,
    "15m": 2000,
    "30m": 2000,
    "1h": 1000,
    "4h": 1000,
    "1d": 1000,
}


# ---------- utilitaires ----------

def iso_utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def compute_limit(tf: str, days: int, user_limit: int | None) -> int:
    """Calcule un limit « safe » pour l’API en fonction du TF & des jours."""
    if user_limit and user_limit > 0:
        # l’utilisateur force la main
        return user_limit
    bars_per_day = TF_BARS_PER_DAY.get(tf)
    if not bars_per_day:
        # fallback conservateur
        return 1000
    needed = days * bars_per_day
    # petit buffer pour les extrémités
    needed = int(needed * 1.05) + 1
    # clamp par TF_MAX_LIMIT
    cap = TF_MAX_LIMIT.get(tf, 2000)
    return min(needed, cap)


def fetch_ohlcv(symbol: str, tf: str, days: int, limit: int | None,
                base_url: str, token: str) -> pd.DataFrame:
    """Récupère l’OHLCV via /api/ohlcv (format json)."""
    url = f"{base_url.rstrip('/')}/api/ohlcv"
    final_limit = compute_limit(tf, days, limit)
    params = {
        "symbol": symbol,
        "tf": tf,
        "format": "json",
        "limit": str(final_limit),
    }
    headers = {"Authorization": f"Bearer {token}"}
    logger.info(f"GET {url} {params}")
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data)
    if df.empty:
        raise RuntimeError("Aucune donnée renvoyée par l'API.")
    # normalisation
    if "timestamp" not in df.columns:
        raise RuntimeError("Colonne 'timestamp' absente.")
    # assure un datetime index
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def run_sma_strategy(df: pd.DataFrame, sma_fast: int, sma_slow: int,
                     fees: float, slippage: float) -> Tuple[pd.DataFrame, pd.Series]:
    """
    SMA crossover long-only:
      - position = 1 si SMA_fast > SMA_slow, sinon 0
      - PnL = position.shift(1) * close_pct_change
      - coûts: sur changement de position, on retranche (fees + slippage)
    Renvoie (summary_df, equity_series) où summary_df contient les colonnes clés.
    """
    d = df.copy()
    d["close"] = d["close"].astype(float)

    d["sma_fast"] = d["close"].rolling(sma_fast, min_periods=sma_fast).mean()
    d["sma_slow"] = d["close"].rolling(sma_slow, min_periods=sma_slow).mean()

    d["signal"] = (d["sma_fast"] > d["sma_slow"]).astype(int)
    d["position"] = d["signal"]

    d["ret"] = d["close"].pct_change().fillna(0.0)
    d["gross"] = d["ret"] * d["position"].shift(1).fillna(0.0)

    # coût sur les changements (aller/retour ≈ 2 x fees/slippage, mais on reste simple)
    turn = d["position"].diff().abs().fillna(0.0)
    # on retire fees+slippage à chaque flip (comme un coût fixe par entrée/sortie)
    d["cost"] = turn * (fees + slippage)

    d["net"] = d["gross"] - d["cost"]

    # equity (base = 1)
    d["equity"] = (1.0 + d["net"]).cumprod()

    # pour expo & trades
    trades = int(turn.sum())
    exposure = 100.0 * d["position"].mean()

    # pack summary de base
    summary_cols = [
        "timestamp",
        "open", "high", "low", "close", "volume",
        "sma_fast", "sma_slow", "signal", "position",
        "ret", "gross", "cost", "net", "equity"
    ]
    summary_df = d[summary_cols].copy()

    return summary_df, summary_df["equity"]


def metrics_from_equity(df_summary: pd.DataFrame, tf: str) -> Dict[str, float]:
    """
    Calcule des métriques à partir d’une série d’équité & du TF:
      - retour total, annualisé (approx), Sharpe, Sortino, MaxDD, win rate, n_trades, exposition.
    """
    d = df_summary.copy()

    # index temporel (évite les erreurs de resample "on=")
    d = d.set_index("timestamp")

    eq = d["equity"].astype(float)
    if eq.empty:
        raise RuntimeError("equity vide")

    # daily equity pour des stats cohérentes
    daily_eq = eq.resample("1D").last().dropna()
    daily_ret = daily_eq.pct_change().dropna()

    total_ret = float(eq.iloc[-1] - 1.0)

    # annualisation approx selon TF (nombre de barres / jour)
    bars_per_day = TF_BARS_PER_DAY.get(tf, 24)
    bars = len(eq)
    if bars > 0:
        years = (bars / bars_per_day) / 365.0
        ann_return = (float(eq.iloc[-1]) ** (1.0 / max(years, 1e-9))) - 1.0 if years > 0 else 0.0
    else:
        ann_return = 0.0

    mean = daily_ret.mean()
    vol = daily_ret.std()
    sharpe = float(mean / vol * math.sqrt(252)) if vol and vol > 0 else 0.0

    neg = daily_ret[daily_ret < 0]
    down_vol = neg.std()
    sortino = float(mean / down_vol * math.sqrt(252)) if down_vol and down_vol > 0 else 0.0

    # max drawdown
    roll_max = eq.cummax()
    dd = (eq / roll_max) - 1.0
    mdd = float(dd.min())

    # win rate & trades (proxy: nb de flips)
    position = d["position"]
    turns = position.diff().abs().fillna(0.0)
    n_trades = int(turns.sum())
    # gain journalier > 0
    win_rate = float((daily_ret > 0).mean()) if not daily_ret.empty else 0.0
    exposure = float(position.mean() * 100.0)

    return {
        "ret_total": total_ret,
        "ret_annualized": ann_return,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "win_rate": win_rate,
        "n_trades": n_trades,
        "exposure_pct": exposure,
        "bars": bars,
        "days_inferred": float(bars) / float(TF_BARS_PER_DAY.get(tf, 24)),
    }


def save_equity_png(equity_csv_path: Path, out_png: Path) -> None:
    """Trace la courbe d’equity à partir de equity.csv et sauve en PNG."""
    try:
        df_eq = pd.read_csv(equity_csv_path, parse_dates=["timestamp"])
        if df_eq.empty:
            logger.warning(f"Aucune donnée equity pour {equity_csv_path}")
            return
        plt.figure(figsize=(10, 4))
        plt.plot(df_eq["timestamp"], df_eq["equity"])
        plt.title("Évolution de l'équité")
        plt.xlabel("Date")
        plt.ylabel("Équité (base = 1.0)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(out_png, dpi=120)
        plt.close()
        logger.info(f"PNG equity sauvegardé → {out_png}")
    except Exception as e:
        logger.exception(f"Echec génération equity.png: {e}")


def run_for(symbol: str, tf: str, args: argparse.Namespace,
            base_url: str, token: str) -> None:
    # fetch
    df = fetch_ohlcv(symbol, tf, args.days, args.limit, base_url, token)

    # backtest
    summary_df, equity = run_sma_strategy(
        df, args.sma_fast, args.sma_slow, args.fees, args.slippage
    )
    metrics = metrics_from_equity(summary_df, tf)

    # dossier de sortie
    ts = iso_utc_now()
    run_id = f"{symbol}_{tf}_{ts}"
    run_dir = REPORTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # fichiers
    raw_path = run_dir / "ohlcv.json"
    summary_path = run_dir / "summary.csv"
    metrics_path = run_dir / "metrics.json"
    equity_path = run_dir / "equity.csv"
    equity_png = run_dir / "equity.png"

    # save raw json
    raw_path.write_text(pd.DataFrame(df).to_json(orient="records"), encoding="utf-8")

    # save summary
    # remet timestamp en col simple
    out_summary = summary_df.reset_index()[summary_df.columns]
    out_summary.to_csv(summary_path, index=False)

    # save metrics
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # save equity.csv (timestamp + equity)
    eq_df = out_summary[["timestamp", "equity"]].copy()
    eq_df.to_csv(equity_path, index=False)

    # PNG
    save_equity_png(equity_path, equity_png)

    # log lisible
    def pct(x: float) -> str:
        return f"{x*100:.2f}%"

    logger.info(
        "Metrics tf=%s | Ret=%s Ann=%s Sharpe=%.2f Sortino=%.2f MDD=%s "
        "Win=%.1f%% Trades=%d Expo=%.1f%%",
        tf,
        pct(metrics["ret_total"]),
        pct(metrics["ret_annualized"]),
        metrics["sharpe"],
        metrics["sortino"],
        pct(metrics["max_drawdown"]),
        metrics["win_rate"] * 100.0,
        metrics["n_trades"],
        metrics["exposure_pct"],
    )
    logger.info("[%s %s] sauvegardé → %s", symbol, tf, run_dir)


# ---------- CLI ----------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest SMA crossover (v2)")
    p.add_argument("--symbols", type=str, default="BTCUSDT",
                   help="Liste de symboles séparés par des virgules (ex: BTCUSDT,ETHUSDT)")
    p.add_argument("--tf", type=str, default="1h",
                   help="Liste de timeframes séparés par des virgules (ex: 15m,1h)")
    p.add_argument("--days", type=int, default=30, help="Fenêtre de backtest (jours)")
    p.add_argument("--limit", type=int, default=None,
                   help="Override du paramètre limit envoyé à l'API (optionnel)")
    p.add_argument("--fees", type=float, default=0.0004, help="Frais (par trade)")
    p.add_argument("--slippage", type=float, default=0.0002, help="Slippage (par trade)")
    p.add_argument("--sma-fast", dest="sma_fast", type=int, default=10, help="Période SMA rapide")
    p.add_argument("--sma-slow", dest="sma_slow", type=int, default=20, help="Période SMA lente")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    token = os.getenv("NSC_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("NSC_API_TOKEN manquant dans l'environnement.")

    base_url = os.getenv("NSC_API_BASE", "http://127.0.0.1:8000").strip()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    tfs = [t.strip() for t in args.tf.split(",") if t.strip()]

    logger.info(
        "Backtest start - symbols=%s tf=%s days=%s limit=%s sma=(%s,%s) fees=%s slippage=%s",
        symbols, tfs, args.days, args.limit, args.sma_fast, args.sma_slow, args.fees, args.slippage
    )

    for sym in symbols:
        for tf in tfs:
            try:
                run_for(sym, tf, args, base_url, token)
            except Exception as e:
                logger.exception(f"Erreur sur {sym} {tf}: {e}")

    logger.info("Backtest terminé.")


if __name__ == "__main__":
    main()
