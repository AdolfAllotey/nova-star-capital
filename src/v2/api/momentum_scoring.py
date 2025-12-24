# src/v2/api/momentum_scoring.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

@dataclass
class Candle:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float

# ----------------------------
# Helpers numériques (sans numpy)
# ----------------------------
def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b not in (0.0, 0) else default

def pct_change(series: Sequence[float]) -> List[float]:
    """Pour n valeurs, retourne n-1 variations en % successives."""
    out: List[float] = []
    for i in range(1, len(series)):
        prev = series[i-1]
        out.append(_safe_div(series[i] - prev, prev))
    return out

def ema(series: Sequence[float], span: int) -> List[float]:
    """EMA simple, renvoie une liste de même taille."""
    if not series:
        return []
    if span <= 1:
        return list(series)
    alpha = 2.0 / (span + 1.0)
    out = [series[0]]
    for x in series[1:]:
        out.append(alpha * x + (1 - alpha) * out[-1])
    return out

def simple_stdev(series: Sequence[float]) -> float:
    if not series:
        return 0.0
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / (n - 1)
    return math.sqrt(var)

def rsi(series: Sequence[float], period: int = 14) -> List[float]:
    """RSI classique (Wilder). Renvoie une liste alignée (les premières valeurs avant seed sont None)."""
    if len(series) < period + 1:
        return [None] * len(series)  # type: ignore
    deltas = [series[i] - series[i-1] for i in range(1, len(series))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    # moyenne initiale
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rs_values: List[Optional[float]] = [None] * (period)  # pas de RSI sur ces index
    # première RSI
    rs = _safe_div(avg_gain, avg_loss, default=float('inf') if avg_loss == 0 else 0.0)
    rsi_vals: List[Optional[float]] = [None] * (period)
    rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    # boucle Wilder
    for i in range(period, len(deltas)):
        gain = gains[i]
        loss = losses[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = _safe_div(avg_gain, avg_loss, default=float('inf') if avg_loss == 0 else 0.0)
        rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    # La taille de rsi_vals est len(deltas)+1 ; on veut l’aligner à len(series)
    # series: [p0, p1, ..., pn] ; deltas: n éléments ; rsi_vals: n+? déjà aligné avec un None seed
    # On s’assure qu’elle fait len(series)
    while len(rsi_vals) < len(series):
        rsi_vals.insert(0, None)

    return rsi_vals  # type: ignore

# ----------------------------
# Scoring
# ----------------------------
@dataclass
class ScoreDetail:
    momentum_lookback: int
    raw_return: float        # rendement relatif (prix_t / prix_{t-lookback} - 1)
    vol_window: int
    volatility: float        # écart-type des returns (sur window)
    rsi_period: int
    rsi_last: Optional[float]
    ema_fast: float
    ema_slow: float
    trend: float             # normalisé -1..+1
    mom_component: float     # 0..100
    rsi_component: float     # 0..100
    vol_component: float     # 0..100
    trend_component: float   # 0..100
    score: float             # 0..100

def _normalize_pos(x: float, lo: float, hi: float) -> float:
    """Ramène x dans [0,1] en coupant aux bornes."""
    if hi <= lo:
        return 0.0
    v = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, v))

def compute_momentum_score(
    closes: Sequence[float],
    momentum_lookback: int = 24,   # ~ 1 jour en 1h
    vol_window: int = 24,
    rsi_period: int = 14,
    ema_fast_span: int = 12,
    ema_slow_span: int = 26,
) -> ScoreDetail:
    """
    Combine 4 composantes pour un score 0..100 :
      - Momentum pur (return sur 'momentum_lookback')
      - RSI (80=surachat, 20=survente → on préfère 55-70)
      - Volatilité (plus faible = meilleur, tout en évitant 0)
      - Trend EMA (EMA12 vs EMA26)
    """
    n = len(closes)
    if n < max(momentum_lookback + 1, vol_window + 1, rsi_period + 1, ema_slow_span + 1):
        # Pas assez de données — score neutre
        return ScoreDetail(
            momentum_lookback=momentum_lookback, raw_return=0.0,
            vol_window=vol_window, volatility=0.0,
            rsi_period=rsi_period, rsi_last=None,
            ema_fast=closes[-1] if n else 0.0, ema_slow=closes[-1] if n else 0.0, trend=0.0,
            mom_component=50.0, rsi_component=50.0, vol_component=50.0, trend_component=50.0,
            score=50.0
        )

    # Momentum (return simple)
    raw_return = _safe_div(closes[-1] - closes[-1 - momentum_lookback],
                           closes[-1 - momentum_lookback])

    # Volatilité (écart-type des returns sur vol_window)
    rets = pct_change(closes[-vol_window:])
    volatility = abs(simple_stdev(rets))

    # RSI
    rsi_series = rsi(closes, rsi_period)
    rsi_last = rsi_series[-1] if rsi_series else None

    # Trend EMA
    ema_fast_series = ema(closes, ema_fast_span)
    ema_slow_series = ema(closes, ema_slow_span)
    ema_fast_last = ema_fast_series[-1]
    ema_slow_last = ema_slow_series[-1]
    trend_raw = _safe_div(ema_fast_last - ema_slow_last, ema_slow_last)
    # bornes raisonnables pour normaliser
    trend_norm = max(-1.0, min(1.0, trend_raw * 10))  # facteur ↑ pour donner de l’amplitude

    # ----------------------------
    # Normalisations → composantes 0..100
    # ----------------------------
    # Momentum: on coupe à [-10%, +10%] → 0..100
    mom_component = _normalize_pos(raw_return, -0.10, 0.10) * 100.0

    # RSI: on "récompense" 50..70 ; en dessous de 30 on pénalise, au-dessus de 80 on pénalise
    if rsi_last is None:
        rsi_component = 50.0
    else:
        if rsi_last < 30:
            rsi_component = _normalize_pos(rsi_last, 10, 30) * 60.0  # 10→0, 30→60
        elif rsi_last <= 70:
            rsi_component = _normalize_pos(rsi_last, 30, 70) * 100.0  # 30→0, 70→100
        else:
            # 70..90 → descend de 100 à 40
            rsi_component = 100.0 - _normalize_pos(rsi_last, 70, 90) * 60.0

    # Vol: on "récompense" faible vol. bornes 0..5% sur returns horaires std
    # 0% → 100 ; 5% → 0 ; au-delà → 0
    vol_component = (1.0 - _normalize_pos(volatility, 0.0, 0.05)) * 100.0

    # Trend: trend_norm -1..+1 → 0..100
    trend_component = ((trend_norm + 1.0) / 2.0) * 100.0

    # Poids (ajuste facilement)
    w_mom = 0.35
    w_rsi = 0.15
    w_vol = 0.20
    w_trend = 0.30

    score = (
        w_mom * mom_component
        + w_rsi * rsi_component
        + w_vol * vol_component
        + w_trend * trend_component
    )

    return ScoreDetail(
        momentum_lookback=momentum_lookback,
        raw_return=raw_return,
        vol_window=vol_window,
        volatility=volatility,
        rsi_period=rsi_period,
        rsi_last=rsi_last,
        ema_fast=ema_fast_last,
        ema_slow=ema_slow_last,
        trend=trend_norm,
        mom_component=mom_component,
        rsi_component=rsi_component,
        vol_component=vol_component,
        trend_component=trend_component,
        score=score,
    )
