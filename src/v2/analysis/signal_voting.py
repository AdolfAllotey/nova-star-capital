from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

# DATA_DIR dérivé de NSC_DATA_DIR
DATA_DIR = Path(get_data_dir()).resolve()

# Paramètres configurables via env
MIN_META_DEFAULT = float(os.getenv("NSC_SIGNAL_VOTING_MIN_META", "40.0"))
MAX_SIGNALS_DEFAULT = int(os.getenv("NSC_SIGNAL_VOTING_MAX_SIGNALS", "100"))
MARKET_MOMENTUM_MIN_CHG_24H = float(os.getenv("NSC_MARKET_MOMENTUM_MIN_CHG_24H", "30.0"))
MARKET_MOMENTUM_MAX_CHG_24H = float(os.getenv("NSC_MARKET_MOMENTUM_MAX_CHG_24H", "85.0"))
MARKET_MOMENTUM_MIN_PRICE = float(os.getenv("NSC_MARKET_MOMENTUM_MIN_PRICE", "0.001"))
MARKET_MOMENTUM_MAX_SIGNALS = int(os.getenv("NSC_MARKET_MOMENTUM_MAX_SIGNALS", "3"))
MARKET_MOMENTUM_STOPLOSS_COOLDOWN_HOURS = int(os.getenv("NSC_MARKET_MOMENTUM_STOPLOSS_COOLDOWN_HOURS", "12"))
SOCIAL_FALLBACK_MIN_SCORE = float(os.getenv("NSC_SOCIAL_FALLBACK_MIN_SCORE", "60.0"))
SOCIAL_FALLBACK_MIN_SOURCE_COUNT = int(os.getenv("NSC_SOCIAL_FALLBACK_MIN_SOURCE_COUNT", "2"))


def _load_momentum_scores(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge momentum_scores.json en gérant les deux formats possibles :
    - ancien format : liste directe de scores
    - nouveau format : objet { "stats": ..., "scores": [...] }
    """
    path = data_dir / "analysis" / "momentum_scores.json"
    raw = load_json_file(path, default=[])

    if isinstance(raw, list):
        logger.info(
            "[signal_voting] momentum_scores.json chargé (format liste brute), n=%d",
            len(raw),
        )
        return raw

    if isinstance(raw, dict):
        scores = raw.get("scores") or raw.get("symbols") or []
        if not isinstance(scores, list):
            logger.warning(
                "[signal_voting] momentum_scores.json: clé 'scores' non-liste ou absente (type=%s).",
                type(scores),
            )
            return []
        logger.info(
            "[signal_voting] momentum_scores.json chargé (format objet), n=%d, stats=%s",
            len(scores),
            raw.get("stats"),
        )
        return scores

    logger.warning(
        "[signal_voting] momentum_scores.json invalide (type=%s), aucun score exploitable.",
        type(raw),
    )
    return []




def _load_recent_stoploss_symbols(data_dir: Path) -> set:
    path = data_dir / "trading" / "exit_events.json"
    rows = load_json_file(path, default=[]) or []
    if not isinstance(rows, list):
        return set()

    since = datetime.now(timezone.utc) - timedelta(hours=MARKET_MOMENTUM_STOPLOSS_COOLDOWN_HOURS)
    blocked = set()

    for e in rows:
        if not isinstance(e, dict):
            continue
        if e.get("exit_type") != "stop_loss":
            continue

        ts = e.get("timestamp") or e.get("ts") or e.get("closed_at")
        if not ts:
            continue

        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue

        if dt < since:
            continue

        sym = str(e.get("symbol") or "").lower().strip()
        if sym:
            blocked.add(sym)

    return blocked


def _load_market_momentum_signals(data_dir: Path) -> List[Dict[str, Any]]:
    selected_path = data_dir / "trading" / "selected_tokens.dynamic.json"
    raw = load_json_file(selected_path, default={}) or {}
    items = raw.get("items", []) if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return []

    signals: List[Dict[str, Any]] = []
    seen = set()
    stoploss_blocked = _load_recent_stoploss_symbols(data_dir)

    for it in items:
        if not isinstance(it, dict):
            continue
        if not bool(it.get("market_momentum")):
            continue

        token = str(it.get("token") or "").strip().upper()
        if not token:
            continue

        try:
            chg_24h = float(it.get("chg_24h") or 0.0)
        except Exception:
            chg_24h = 0.0

        if chg_24h < MARKET_MOMENTUM_MIN_CHG_24H:
            continue

        symbol = str(it.get("pair") or f"{token}USDT").lower()
        if symbol in seen:
            continue

        if symbol in stoploss_blocked:
            logger.info(
                "[signal_voting] market_momentum cooldown skip: %s recent stop_loss within %sh",
                symbol,
                MARKET_MOMENTUM_STOPLOSS_COOLDOWN_HOURS,
            )
            continue

        seen.add(symbol)

        try:
            price = float(it.get("price") or 0.0)
        except Exception:
            price = 0.0

        if chg_24h > MARKET_MOMENTUM_MAX_CHG_24H:
            logger.info(
                "[signal_voting] market_momentum rejected extreme pump: %s chg_24h=%.2f > %.2f",
                token, chg_24h, MARKET_MOMENTUM_MAX_CHG_24H,
            )
            continue

        if price > 0 and price < MARKET_MOMENTUM_MIN_PRICE:
            logger.info(
                "[signal_voting] market_momentum rejected low price: %s price=%s < %.6f",
                token, price, MARKET_MOMENTUM_MIN_PRICE,
            )
            continue

        quality_score = 50.0 + min(chg_24h, 70.0) * 0.4
        meta_score = max(45.0, min(78.0, quality_score))

        signals.append({
            "symbol": symbol,
            "side": "buy",
            "strategy": "market_momentum",
            "meta_score": round(meta_score, 4),
            "momentum_score": round(meta_score, 4),
            "early_pump_score": None,
            "momentum_regime": "quality_market_mover",
            "market_momentum": True,
            "source": "selected_tokens.dynamic.market_momentum.option_b",
            "token": token,
            "pair": it.get("pair"),
            "price": price,
            "chg_24h": chg_24h,
            "quality_filters": {
                "min_chg_24h": MARKET_MOMENTUM_MIN_CHG_24H,
                "max_chg_24h": MARKET_MOMENTUM_MAX_CHG_24H,
                "min_price": MARKET_MOMENTUM_MIN_PRICE,
                "max_signals": MARKET_MOMENTUM_MAX_SIGNALS,
            },
            "reason": (
                f"option_b market_momentum quality filter ok: "
                f"chg_24h={chg_24h:.2f}% between "
                f"{MARKET_MOMENTUM_MIN_CHG_24H:.2f}% and {MARKET_MOMENTUM_MAX_CHG_24H:.2f}%"
            ),
        })

    # Controlled fallback:
    # Use social fallback only when no valid market_momentum gainer exists.
    # Important: social fallback must never evict valid market_momentum gainers.
    if len(signals) == 0:
        social_candidates = []
        for it in items:
            if not isinstance(it, dict):
                continue
            if bool(it.get("market_momentum")):
                continue

            token = str(it.get("token") or "").strip().upper()
            if not token:
                continue

            symbol = f"{token}USDT".lower()
            if symbol in seen or symbol in stoploss_blocked:
                continue

            try:
                score = float(it.get("score") or 0.0)
            except Exception:
                score = 0.0

            try:
                source_count = int(it.get("source_count") or 0)
            except Exception:
                source_count = 0

            if score < SOCIAL_FALLBACK_MIN_SCORE:
                continue
            if source_count < SOCIAL_FALLBACK_MIN_SOURCE_COUNT:
                continue

            social_candidates.append((score, source_count, it, symbol, token))

        social_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        for score, source_count, it, symbol, token in social_candidates:
            if len(signals) >= MARKET_MOMENTUM_MAX_SIGNALS:
                break

            seen.add(symbol)
            meta_score = max(60.0, min(74.0, score))

            signals.append({
                "symbol": symbol,
                "side": "buy",
                "strategy": "market_momentum",
                "meta_score": round(meta_score, 4),
                "momentum_score": round(meta_score, 4),
                "early_pump_score": None,
                "momentum_regime": "social_momentum_fallback",
                "market_momentum": False,
                "source": "selected_tokens.dynamic.social_fallback",
                "token": token,
                "pair": symbol.upper(),
                "price": None,
                "chg_24h": None,
                "quality_filters": {
                    "fallback": "social_momentum",
                    "min_score": SOCIAL_FALLBACK_MIN_SCORE,
                    "min_source_count": SOCIAL_FALLBACK_MIN_SOURCE_COUNT,
                    "max_signals": MARKET_MOMENTUM_MAX_SIGNALS,
                },
                "reason": (
                    f"social fallback: score={score:.2f}, "
                    f"source_count={source_count}, used because market gainers were below target"
                ),
            })

            logger.info(
                "[signal_voting] social fallback injected: %s score=%.2f source_count=%s",
                symbol, score, source_count
            )

    signals.sort(key=lambda s: float(s.get("meta_score") or 0.0), reverse=True)
    return signals[:MARKET_MOMENTUM_MAX_SIGNALS]

def compute_signals(
    data_dir: Path,
    min_meta: float = MIN_META_DEFAULT,
    max_signals: int = MAX_SIGNALS_DEFAULT,
) -> List[Dict[str, Any]]:
    """
    Génère des signaux à partir des scores de momentum.

    Règles simples (Version Saison 2 / 2.5) :
    - On part de momentum_scores.json (nouveau format supporté)
    - On garde les assets avec meta_score >= min_meta
    - On trie par meta_score décroissant
    - On limite à max_signals
    - On crée des signaux 'buy' stratégie 'momentum'
    """
    analysis_dir = data_dir / "analysis"

    logger.info(
        "[signal_voting] Calcul des signaux (signal voting) à partir du momentum: "
        "min_meta=%.2f, max_signals=%d",
        min_meta,
        max_signals,
    )

    scores = _load_momentum_scores(data_dir)
    if not scores:
        logger.warning(
            "[signal_voting] Aucun score de momentum exploitable, aucun signal généré."
        )
        signals: List[Dict[str, Any]] = []
        save_json_file(analysis_dir / "signal_votes.json", signals)
        save_json_file(analysis_dir / "signal_candidates.json", signals)
        return signals

    # Normalisation minimale + filtrage
    candidates: List[Dict[str, Any]] = []
    for row in scores:
        symbol = row.get("symbol")
        if not symbol:
            continue

        meta = row.get("meta_score")
        if meta is None:
            # fallback sur momentum_score si meta_score absent
            meta = row.get("momentum_score")

        if meta is None:
            logger.debug(
                "[signal_voting] Ligne ignorée (pas de meta_score/momentum_score): %s",
                row,
            )
            continue

        if meta < min_meta:
            continue

        signal = {
            "symbol": symbol,
            "side": "buy",
            "strategy": "momentum",
            "meta_score": float(meta),
            "momentum_score": float(row.get("momentum_score", meta)),
            "early_pump_score": row.get("early_pump_score"),
            "momentum_regime": row.get("momentum_regime"),
            "reason": f"momentum meta={meta:.2f} >= {min_meta:.2f}",
        }
        candidates.append(signal)

    # Tri par meta_score décroissant
    candidates.sort(key=lambda s: s.get("meta_score", 0.0), reverse=True)

    if max_signals and len(candidates) > max_signals:
        candidates = candidates[:max_signals]

    logger.info(
        "[signal_voting] Signaux générés: total_scores=%d, candidats=%d (min_meta=%.2f)",
        len(scores),
        len(candidates),
        min_meta,
    )

    # Pour l’instant, signal_votes = signal_candidates
    save_json_file(analysis_dir / "signal_votes.json", candidates)
    save_json_file(analysis_dir / "signal_candidates.json", candidates)

    return candidates

def _load_momentum_scores(data_dir: Path) -> List[Dict[str, Any]]:
    """
    Charge momentum_scores.json en gérant les formats :
    - ancien format : liste directe de scores
    - format objet : { "stats": ..., "scores": [...] }
    - nouveau format (dict) : { "stats": ..., "scores": { "bitcoin": {...}, ... } }
    """
    path = data_dir / "analysis" / "momentum_scores.json"
    raw = load_json_file(path, default=[])

    # Ancien format : liste directe
    if isinstance(raw, list):
        logger.info("[signal_voting] momentum_scores.json chargé (format liste), n=%d", len(raw))
        return raw

    if not isinstance(raw, dict):
        logger.warning("[signal_voting] Format inattendu pour %s: type=%s", path, type(raw))
        return []

    scores_blob = raw.get("scores", [])
    stats = raw.get("stats", {}) if isinstance(raw.get("stats", {}), dict) else {}

    score_list: List[Dict[str, Any]] = []

    # Format objet avec liste
    if isinstance(scores_blob, list):
        score_list = [x for x in scores_blob if isinstance(x, dict)]

    # Format objet avec dict {symbol: payload}
    elif isinstance(scores_blob, dict):
        for sym, payload in scores_blob.items():
            if not isinstance(payload, dict):
                continue
            row = dict(payload)
            row["symbol"] = sym
            score_list.append(row)

    else:
        logger.warning(
            "[signal_voting] momentum_scores.json: clé 'scores' invalide (type=%s).",
            type(scores_blob),
        )
        return []

    logger.info(
        "[signal_voting] momentum_scores.json chargé (format objet), n=%d, stats=%s",
        len(score_list),
        stats,
    )
    return score_list


def compute_signals(
    data_dir: Path,
    min_meta: float = MIN_META_DEFAULT,
    max_signals: int = MAX_SIGNALS_DEFAULT,
) -> List[Dict[str, Any]]:
    analysis_dir = data_dir / "analysis"

    logger.info(
        "[signal_voting] Calcul des signaux (signal voting) à partir du momentum: min_meta=%.2f, max_signals=%d",
        min_meta,
        max_signals,
    )

    scores = _load_momentum_scores(data_dir)

    if not scores:
        logger.warning("[signal_voting] Aucun score de momentum exploitable, aucun signal généré.")
        save_json_file(analysis_dir / "signal_votes.json", [])
        save_json_file(analysis_dir / "signal_candidates.json", [])
        return []

    # Normalisation minimale + filtrage
    candidates: List[Dict[str, Any]] = []
    for row in scores:
        symbol = row.get("symbol")
        if not symbol:
            continue

        meta = row.get("meta_score")
        if meta is None:
            meta = row.get("momentum_score")

        if meta is None:
            logger.debug("[signal_voting] Ligne ignorée (pas de meta_score/momentum_score): %s", row)
            continue

        if float(meta) < float(min_meta):
            continue

        signal = {
            "symbol": symbol,
            "side": "buy",
            "strategy": "momentum",
            "meta_score": float(meta),
            "momentum_score": float(row.get("momentum_score", meta)),
            "early_pump_score": row.get("early_pump_score"),
            "momentum_regime": row.get("momentum_regime"),
            "reason": f"momentum meta={float(meta):.2f} >= {float(min_meta):.2f}",
        }
        candidates.append(signal)

    # Inject market movers selected by token_selector_v2_2.
    # They may not exist in OHLCV yet, but must remain visible for PREPROD inspection.
    market_signals = _load_market_momentum_signals(data_dir)
    existing_symbols = {str(s.get("symbol", "")).lower() for s in candidates if isinstance(s, dict)}
    injected = 0
    for sig in market_signals:
        sym = str(sig.get("symbol", "")).lower()
        if sym and sym not in existing_symbols:
            candidates.append(sig)
            existing_symbols.add(sym)
            injected += 1

    if injected:
        logger.info("[signal_voting] market_momentum injected=%d", injected)

    # Tri par meta_score décroissant
    candidates.sort(key=lambda s: s.get("meta_score", 0.0), reverse=True)

    if max_signals and len(candidates) > max_signals:
        candidates = candidates[:max_signals]

    logger.info(
        "[signal_voting] Signaux générés: total_scores=%d, candidats=%d (min_meta=%.2f)",
        len(scores),
        len(candidates),
        min_meta,
    )

    save_json_file(analysis_dir / "signal_votes.json", candidates)
    save_json_file(analysis_dir / "signal_candidates.json", candidates)
    return candidates
def main() -> None:
    signals = compute_signals(DATA_DIR)
    logger.info(
        "[signal_voting] Terminé, %d signaux sauvegardés dans signal_votes.json et signal_candidates.json",
        len(signals),
    )


if __name__ == "__main__":
    main()
