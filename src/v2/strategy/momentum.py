# /opt/nsc/app/src/v2/strategy/momentum.py
from typing import List, Dict
from statistics import pstdev
import math

def sma(values: List[float], period: int) -> List[float]:
    out = []
    acc = 0.0
    q = []
    for v in values:
        q.append(v)
        acc += v
        if len(q) > period:
            acc -= q.pop(0)
        out.append(acc / len(q) if q else None)
    return out

def backtest_momentum(ohlcv: List[Dict], fast: int = 20, slow: int = 50, fee_bp: float = 5.0):
    """
    Long-only: enter when SMA(fast) > SMA(slow), exit when SMA(fast) < SMA(slow).
    fee_bp = 5 -> 0.05% par trade
    """
    closes = [r["close"] for r in ohlcv]
    ts = [r["ts"] for r in ohlcv]
    sma_fast = sma(closes, fast)
    sma_slow = sma(closes, slow)

    in_pos = False
    entry = 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    trades = []
    rets = []

    for i in range(len(ohlcv)):
        if sma_fast[i] is None or sma_slow[i] is None:
            continue
        # signal
        long_sig = sma_fast[i] > sma_slow[i]
        if not in_pos and long_sig:
            in_pos = True
            entry = closes[i] * (1 + fee_bp/10000.0)
            trades.append({"ts": ts[i], "action":"BUY", "price": closes[i]})
        elif in_pos and not long_sig:
            # close
            exitp = closes[i] * (1 - fee_bp/10000.0)
            r = (exitp - entry) / entry
            equity *= (1.0 + r)
            trades.append({"ts": ts[i], "action":"SELL", "price": closes[i], "ret": r})
            rets.append(r)
            in_pos = False
            entry = 0.0

        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    # si on termine en position, on clôture à la dernière bougie
    if in_pos:
        exitp = closes[-1] * (1 - fee_bp/10000.0)
        r = (exitp - entry) / entry
        equity *= (1.0 + r)
        trades.append({"ts": ts[-1], "action":"SELL", "price": closes[-1], "ret": r})
        rets.append(r)

    pnl = equity - 1.0
    wins = sum(1 for r in rets if r > 0)
    win_rate = (wins / len(rets)) if rets else 0.0

    # Sharpe (simple) sur ret par trade (pas annualisé ici)
    if len(rets) >= 2 and pstdev(rets) > 0:
        sharpe = (sum(rets)/len(rets)) / pstdev(rets)
    else:
        sharpe = 0.0

    return {
        "trades": trades,
        "n_trades": len(rets),
        "equity_final": round(equity, 6),
        "pnl": round(pnl, 6),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_dd, 4),
        "sharpe_like": round(sharpe, 4),
    }
