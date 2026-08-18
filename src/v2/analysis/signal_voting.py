from __future__ import annotations

import os
from pathlib import Path
from collections import Counter
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



# ============================================================
# RC2 META RANKING EXECUTION ELIGIBILITY GATE V1
#
# Meta Ranking is part of the institutional decision chain,
# not a reporting-only artifact.
#
# Execution eligibility:
#   GOOD_CANDIDATE  -> eligible
#   WATCH_TRADABLE  -> eligible
#
# Fail closed when:
#   - ranking is missing;
#   - verdict is not execution-eligible;
#   - tradability is not confirmed;
#   - observation_only is true;
#   - Meta Ranking carries risk flags.
#
# Meta Validation remains downstream and verifies alignment
# after the decision.
# ============================================================

META_EXECUTION_ALLOWED_VERDICTS = {
    "GOOD_CANDIDATE",
    "WATCH_TRADABLE",
}


def _normalize_meta_symbol(value) -> str:
    symbol = str(value or "").strip().upper()

    if symbol.endswith("USDT"):
        symbol = symbol[:-4]

    return symbol


def _load_meta_ranking_map(
    data_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    path = (
        data_dir
        / "discovery"
        / "meta_rankings.json"
    )

    raw = load_json_file(
        path,
        default={},
    ) or {}

    if not isinstance(raw, dict):
        return {}

    items = raw.get("items", [])

    if not isinstance(items, list):
        return {}

    out: Dict[str, Dict[str, Any]] = {}

    for row in items:
        if not isinstance(row, dict):
            continue

        symbol = _normalize_meta_symbol(
            row.get("symbol")
            or row.get("pair")
        )

        if not symbol:
            continue

        out[symbol] = row

    return out


def _meta_execution_eligibility(
    ranking: Dict[str, Any] | None,
):
    """
    Pure strategic eligibility contract.

    Returns:
        allowed: bool
        reason: str
        context: dict
    """
    if not isinstance(ranking, dict):
        return (
            False,
            "missing_meta_ranking",
            {},
        )

    verdict = str(
        ranking.get("verdict") or ""
    ).strip().upper()

    tradable = (
        ranking.get("tradable") is True
    )

    observation_only = bool(
        ranking.get("observation_only", False)
    )

    risk_flags = ranking.get("risk_flags") or []

    if not isinstance(risk_flags, list):
        risk_flags = [risk_flags]

    risk_flags = [
        str(x)
        for x in risk_flags
        if str(x).strip()
    ]

    context = {
        "meta_rank": ranking.get("meta_rank"),
        "verdict": verdict or None,
        "recommended": ranking.get(
            "recommended"
        ),
        "tradable": tradable,
        "observation_only": observation_only,
        "risk_flags": risk_flags,

        # RC2 Meta Decision Lineage Contract V1
        # Preserve the complete strategic decision context
        # produced by Meta Ranking V2.
        "execution_eligible": bool(
            ranking.get("execution_eligible", False)
        ),
        "execution_confirmed": bool(
            ranking.get("execution_confirmed", False)
        ),
        "decision_chg_24h": ranking.get(
            "decision_chg_24h"
        ),
        "momentum_source": ranking.get(
            "momentum_source"
        ),
        "execution_pair": ranking.get(
            "execution_pair"
        ),
        "execution_source": ranking.get(
            "execution_source"
        ),
        "cross_source_direction_conflict": bool(
            ranking.get(
                "cross_source_direction_conflict",
                False,
            )
        ),
    }

    if not tradable:
        return (
            False,
            "meta_not_tradable",
            context,
        )

    if observation_only:
        return (
            False,
            "meta_observation_only",
            context,
        )

    if risk_flags:
        return (
            False,
            "meta_risk_flags",
            context,
        )

    if verdict not in (
        META_EXECUTION_ALLOWED_VERDICTS
    ):
        return (
            False,
            "meta_verdict_not_eligible",
            context,
        )

    return (
        True,
        "meta_execution_eligible",
        context,
    )


def _apply_meta_execution_gate(
    candidates: List[Dict[str, Any]],
    data_dir: Path,
) -> List[Dict[str, Any]]:
    rankings = _load_meta_ranking_map(
        data_dir
    )

    eligible: List[Dict[str, Any]] = []

    blocked = Counter()

    for signal in candidates:
        if not isinstance(signal, dict):
            continue

        token = _normalize_meta_symbol(
            signal.get("symbol")
            or signal.get("token")
            or signal.get("asset")
        )

        ranking = rankings.get(token)

        (
            allowed,
            reason,
            context,
        ) = _meta_execution_eligibility(
            ranking
        )

        if not allowed:
            blocked[reason] += 1

            logger.info(
                "[signal_voting] "
                "meta execution gate blocked "
                "symbol=%s reason=%s context=%s",
                signal.get("symbol"),
                reason,
                context,
            )

            continue

        enriched = dict(signal)

        enriched[
            "meta_execution_gate"
        ] = {
            "status": "eligible",
            "reason": reason,
            **context,
        }

        # Preserve institutional Meta Ranking values explicitly
        # through sizing and execution for auditability.
        enriched[
            "meta_rank"
        ] = context.get("meta_rank")

        enriched[
            "meta_verdict"
        ] = context.get("verdict")

        enriched[
            "meta_recommended"
        ] = context.get("recommended")

        # RC2 Meta Decision Lineage Contract V1.
        # Keep Meta Ranking execution semantics explicit
        # outside the nested gate for downstream engines.
        enriched[
            "execution_eligible"
        ] = context.get("execution_eligible")

        enriched[
            "execution_confirmed"
        ] = context.get("execution_confirmed")

        enriched[
            "decision_chg_24h"
        ] = context.get("decision_chg_24h")

        enriched[
            "momentum_source"
        ] = context.get("momentum_source")

        enriched[
            "execution_pair"
        ] = context.get("execution_pair")

        enriched[
            "execution_source"
        ] = context.get("execution_source")

        enriched[
            "cross_source_direction_conflict"
        ] = context.get(
            "cross_source_direction_conflict"
        )

        # Deliberately distinct from Risk Engine Pro
        # risk_flag / risk_score fields.
        enriched[
            "meta_risk_flags"
        ] = list(
            context.get("risk_flags") or []
        )

        eligible.append(enriched)

    logger.info(
        "[signal_voting] meta execution gate "
        "input=%d eligible=%d blocked=%d "
        "blocked_reasons=%s",
        len(candidates),
        len(eligible),
        len(candidates) - len(eligible),
        dict(blocked),
    )

    return eligible

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

    # ------------------------------------------------------------
    # RC2 institutional strategic eligibility.
    #
    # Meta Ranking must govern execution eligibility BEFORE
    # ranking/truncation, sizing and execution.
    # ------------------------------------------------------------
    candidates = _apply_meta_execution_gate(
        candidates,
        data_dir,
    )

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
