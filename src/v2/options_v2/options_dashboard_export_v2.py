import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/opt/nsc/app/src/v2/options_v2/data")

STATUS_FILE = BASE / "options_v2_status.json"
METRICS_FILE = BASE / "options_v2_metrics.json"
LEADERBOARD_FILE = BASE / "options_v2_leaderboard.json"
REPORT_FILE = BASE / "options_v2_daily_report.json"
POSITIONS_FILE = BASE / "options_v2_positions.json"
DECISIONS_FILE = BASE / "options_v2_decisions.json"
OUTPUT_FILE = BASE / "options_v2_dashboard.json"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default



def build_daily_narrative(summary, insights, rejection_ratios):
    positions_open = summary.get("positions_open", 0)
    realized = summary.get("aggregate_realized_pnl_eur", 0)
    unrealized = summary.get("aggregate_unrealized_pnl_eur", 0)
    risk_open = summary.get("aggregate_estimated_risk_open_eur", 0)
    win_rate = summary.get("win_rate_pct", 0)

    top_strategy = insights.get("top_strategy_name") or "N/A"
    top_ticker = insights.get("top_ticker_name") or "N/A"
    top_blocker = insights.get("top_blocker_reason") or "N/A"

    if positions_open == 0:
        posture = "La brique Options US est actuellement en posture d’attente : aucune position n’est ouverte."
    else:
        posture = f"La brique Options US reste active avec {positions_open} position(s) ouverte(s)."

    blocker_line = f"Le principal frein opérationnel observé aujourd’hui est '{top_blocker}'."
    performance_line = f"La performance cumulée reste positive avec {realized} EUR réalisés et {unrealized} EUR non réalisés."
    risk_line = f"Le risque actuellement ouvert est de {risk_open} EUR."
    leader_line = f"Le moteur dominant sur la fenêtre observée est {top_strategy}, porté principalement par {top_ticker}."
    quality_line = f"Le win rate observé est de {win_rate}%."

    if positions_open == 0 and top_blocker == "cooldown_after_close":
        action_line = "En pratique, le moteur ne retrade pas immédiatement car il respecte sa discipline de cooldown après clôture."
    elif positions_open == 0 and top_blocker == "trade_risk_above_limit":
        action_line = "En pratique, le moteur reste sélectif car les nouvelles opportunités dépassent le budget de risque autorisé."
    elif positions_open > 0:
        action_line = "En pratique, le moteur est encore engagé et continue de surveiller l’évolution des positions ouvertes."
    else:
        action_line = "En pratique, le moteur reste sélectif et attend de meilleures conditions de réengagement."

    return " ".join([
        posture,
        leader_line,
        blocker_line,
        performance_line,
        risk_line,
        quality_line,
        action_line,
    ])

def build_dashboard():
    status = load_json(STATUS_FILE, {})
    metrics = load_json(METRICS_FILE, {})
    leaderboard = load_json(LEADERBOARD_FILE, {})
    report = load_json(REPORT_FILE, {})
    positions = load_json(POSITIONS_FILE, [])
    decisions = load_json(DECISIONS_FILE, [])

    summary = metrics.get("summary", {})
    leaders = leaderboard.get("leaders", {})
    blockers = leaderboard.get("blockers", {})

    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    closed_positions = [p for p in positions if p.get("status") == "CLOSED"]

    top_strategy = (leaders.get("top_strategy_by_realized_pnl", []) or [{}])[0]
    top_ticker = (leaders.get("top_ticker_by_realized_pnl", []) or [{}])[0]
    top_reason = (blockers.get("top_rejection_reasons", []) or [{}])[0]

    decisions_ui = []
    for item in decisions[:10]:
        ticker = item.get("ticker", "N/A")
        strategy = item.get("strategy", "N/A")
        status_label = item.get("status", "UNKNOWN")
        reason = item.get("reason", "unknown_reason")
        decisions_ui.append({
            "ticker": ticker,
            "strategy": strategy,
            "status": status_label,
            "reason": reason,
            "sentence": f"{ticker} / {strategy} → {status_label} ({reason})"
        })

    rejection_ratios = report.get("blockers", {}).get("rejection_ratios", {}) if isinstance(report.get("blockers", {}), dict) else {}

    insights_payload = {
        "top_strategy_name": top_strategy.get("name"),
        "top_ticker_name": top_ticker.get("name"),
        "top_blocker_reason": top_reason.get("reason"),
    }

    previous_readiness_entry = load_last_readiness_entry()

    readiness_payload = build_readiness(
        summary=summary,
        blockers={
            "top_rejection_reasons": blockers.get("top_rejection_reasons", [])
        },
        insights=insights_payload
    )

    readiness_trend = build_readiness_trend(
        current_score=readiness_payload.get("score", 0),
        previous_entry=previous_readiness_entry
    )

    readiness_payload["trend"] = readiness_trend

    dashboard = {
        "ts": utc_now_iso(),
        "engine": "options_dashboard_export_v2",
        "module": "options_v2",
        "status": {
            "pipeline_status": status.get("status"),
            "version": status.get("version"),
            "mode": status.get("mode"),
            "message": status.get("message"),
        },
        "kpis": {
            "positions_open": summary.get("positions_open", 0),
            "positions_closed": summary.get("positions_closed", 0),
            "trades_total": summary.get("trades_total", 0),
            "close_trades_total": summary.get("close_trades_total", 0),
            "candidates_total": summary.get("candidates_total", 0),
            "candidates_approved": summary.get("candidates_approved", 0),
            "realized_pnl_eur": summary.get("aggregate_realized_pnl_eur", 0),
            "unrealized_pnl_eur": summary.get("aggregate_unrealized_pnl_eur", 0),
            "win_rate_pct": summary.get("win_rate_pct", 0),
            "estimated_risk_open_eur": summary.get("aggregate_estimated_risk_open_eur", 0),
            "opportunity_conversion_pct": rejection_ratios.get("opportunity_conversion_pct", 0),
        },
        "leaders": {
            "top_strategy_by_realized_pnl": leaders.get("top_strategy_by_realized_pnl", [])[:3],
            "top_ticker_by_realized_pnl": leaders.get("top_ticker_by_realized_pnl", [])[:5],
        },
        "blockers": {
            "top_rejection_reasons": blockers.get("top_rejection_reasons", [])[:5],
            "top_rejection_statuses": blockers.get("top_rejection_statuses", [])[:5],
            "rejection_ratios": rejection_ratios,
        },
        "positions": {
            "open": open_positions,
            "closed": closed_positions[:10],
        },
        "decisions": decisions[:10],
        "insights": {
            "top_strategy_name": top_strategy.get("name"),
            "top_strategy_realized_pnl_eur": top_strategy.get("realized_pnl_eur", 0),
            "top_ticker_name": top_ticker.get("name"),
            "top_ticker_realized_pnl_eur": top_ticker.get("realized_pnl_eur", 0),
            "top_blocker_reason": top_reason.get("reason"),
            "top_blocker_count": top_reason.get("count", 0),
            "decision_sentences": decisions_ui,
            "funnel": {
                "candidates_total": summary.get("candidates_total", 0),
                "candidates_approved": summary.get("candidates_approved", 0),
                "trades_total": summary.get("trades_total", 0),
                "close_trades_total": summary.get("close_trades_total", 0),
                "opportunity_conversion_pct": rejection_ratios.get("opportunity_conversion_pct", 0),
            },
            "daily_narrative": build_daily_narrative(
                summary=summary,
                insights={
                    "top_strategy_name": top_strategy.get("name"),
                    "top_ticker_name": top_ticker.get("name"),
                    "top_blocker_reason": top_reason.get("reason"),
                },
                rejection_ratios=rejection_ratios,
            ),
        },
        "delta": build_delta_summary(
            current=summary,
            previous=previous_snapshot if 'previous_snapshot' in locals() else None
        ),
        "readiness": build_readiness(
            summary=summary,
            blockers={
                "top_rejection_reasons": blockers.get("top_rejection_reasons", [])
            },
            insights=insights if 'insights' in locals() else {}
        ),
        "switch_policy": build_switch_policy(
            summary=summary,
            readiness=build_readiness(
                summary=summary,
                blockers={
                    "top_rejection_reasons": blockers.get("top_rejection_reasons", [])
                },
                insights=insights_payload
            ),
            anomalies=report.get("anomalies", []),
        ),
        "conclusion": report.get("conclusion", ""),
    }

    return dashboard


def generate_dashboard_export():
    data = build_dashboard()
    OUTPUT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def build_delta_summary(current, previous):
    if not previous:
        return {
            "status": "INIT",
            "message": "Première exécution, aucune comparaison disponible"
        }

    delta_realized = current.get("aggregate_realized_pnl_eur", 0) - previous.get("aggregate_realized_pnl_eur", 0)
    delta_trades = current.get("trades_total", 0) - previous.get("trades_total", 0)
    delta_positions_open = current.get("positions_open", 0) - previous.get("positions_open", 0)
    delta_positions_closed = current.get("positions_closed", 0) - previous.get("positions_closed", 0)

    if delta_realized > 0:
        status = "IMPROVING"
    elif delta_realized < 0:
        status = "DEGRADING"
    else:
        status = "STABLE"

    return {
        "status": status,
        "delta_realized_pnl_eur": delta_realized,
        "delta_trades": delta_trades,
        "delta_positions_open": delta_positions_open,
        "delta_positions_closed": delta_positions_closed,
    }


def build_readiness(summary, blockers, insights):
    base_score = 100
    score = base_score
    reasons = []
    penalties = []
    bonuses = []

    positions_open = summary.get("positions_open", 0)
    trades_total = summary.get("trades_total", 0)
    close_trades_total = summary.get("close_trades_total", 0)
    approved = summary.get("candidates_approved", 0)
    win_rate = summary.get("win_rate_pct", 0)
    realized = summary.get("aggregate_realized_pnl_eur", 0)
    risk_open = summary.get("aggregate_estimated_risk_open_eur", 0)

    reason_counts = {
        (item.get("reason") or item.get("status")): item.get("count", 0)
        for item in blockers.get("top_rejection_reasons", [])
        if isinstance(item, dict)
    }

    cooldown_count = reason_counts.get("cooldown_after_close", 0)
    risk_count = reason_counts.get("trade_risk_above_limit", 0)

    if cooldown_count > 0:
        score -= 25
        penalties.append({
            "label": "Cooldown after close",
            "impact": -25,
            "detail": f"{cooldown_count} rejet(s) liés au cooldown"
        })
        reasons.append("cooldown_after_close active")

    if risk_count > 0:
        score -= 20
        penalties.append({
            "label": "Risk budget blocking",
            "impact": -20,
            "detail": f"{risk_count} rejet(s) liés au budget risque"
        })
        reasons.append("risk budget blocking candidates")

    if approved == 0:
        score -= 15
        penalties.append({
            "label": "No approved candidates",
            "impact": -15,
            "detail": "aucun candidat approuvé sur le run courant"
        })
        reasons.append("no approved candidates")

    if close_trades_total < 3:
        score -= 10
        penalties.append({
            "label": "Limited trade history",
            "impact": -10,
            "detail": f"historique encore court ({close_trades_total} trade(s) clôturé(s))"
        })
        reasons.append("limited statistical history")

    if positions_open == 0 and trades_total == 0:
        score -= 10
        penalties.append({
            "label": "No active engagement",
            "impact": -10,
            "detail": "aucune activité ouverte ni nouveau trade"
        })
        reasons.append("no active engagement")

    if win_rate >= 60:
        score += 10
        bonuses.append({
            "label": "Strong win rate",
            "impact": 10,
            "detail": f"win rate à {win_rate}%"
        })
        reasons.append("historical quality remains strong")

    if realized > 0:
        score += 10
        bonuses.append({
            "label": "Positive realized PnL",
            "impact": 10,
            "detail": f"PnL réalisé positif ({realized} EUR)"
        })
        reasons.append("strategy remains profitable")

    if positions_open > 0:
        score += 5
        bonuses.append({
            "label": "Engine active",
            "impact": 5,
            "detail": f"{positions_open} position(s) ouverte(s)"
        })
        reasons.append("engine currently re-engaged")

    score = max(0, min(100, score))

    if score >= 75:
        status = "READY"
    elif score >= 40:
        status = "WAIT"
    else:
        status = "BLOCKED"

    if status == "READY":
        summary_sentence = "Le moteur options est exploitable immédiatement : qualité, activité et discipline sont alignées."
    elif status == "WAIT":
        summary_sentence = "Le moteur options est prometteur mais encore en phase d’observation contrôlée avant allocation réelle."
    else:
        summary_sentence = "Le moteur options reste trop immature ou trop contraint pour justifier une activation."

    return {
        "score": score,
        "status": status,
        "reasons": reasons[:8],
        "base_score": base_score,
        "penalties": penalties,
        "bonuses": bonuses,
        "summary_sentence": summary_sentence,
        "risk_open_eur": risk_open,
        "realized_pnl_eur": realized,
        "win_rate_pct": win_rate,
        "close_trades_total": close_trades_total,
    }


READINESS_HISTORY_PATH = Path("/opt/nsc/app/src/v2/options_v2/data/options_v2_readiness_history.jsonl")

def load_last_readiness_entry():
    if not READINESS_HISTORY_PATH.exists():
        return None
    try:
        lines = [line.strip() for line in READINESS_HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        import json
        return json.loads(lines[-1])
    except Exception:
        return None

def append_readiness_history(entry):
    import json
    READINESS_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with READINESS_HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def build_readiness_trend(current_score, previous_entry):
    if not previous_entry:
        return {
            "previous_score": None,
            "delta_score": 0,
            "trend": "INIT",
            "trend_sentence": "Première mesure de readiness disponible."
        }

    previous_score = previous_entry.get("score", 0)
    delta = round(current_score - previous_score, 2)

    if delta > 3:
        trend = "IMPROVING"
        sentence = "Le readiness score progresse de manière visible."
    elif delta < -3:
        trend = "DEGRADING"
        sentence = "Le readiness score se dégrade et nécessite une revue."
    else:
        trend = "STABLE"
        sentence = "Le readiness score reste globalement stable."

    return {
        "previous_score": previous_score,
        "delta_score": delta,
        "trend": trend,
        "trend_sentence": sentence
    }


def build_switch_policy(summary, readiness, anomalies):
    score = readiness.get("score", 0)
    trend = (readiness.get("trend") or {}).get("trend", "INIT")
    close_trades = summary.get("close_trades_total", 0)
    win_rate = summary.get("win_rate_pct", 0)
    has_anomalies = bool(anomalies)

    if score < 50 or close_trades < 3:
        maturity = "OBSERVE"
        replace_v1 = False
        recommendation = "Continuer l’observation de la V2. Remplacement V1 non autorisé."
    elif score < 70 or close_trades < 5 or win_rate < 50:
        maturity = "PROMISING"
        replace_v1 = False
        recommendation = "La V2 devient crédible mais doit encore tourner en parallèle avec V1."
    elif score < 85 or close_trades < 8 or win_rate < 55 or has_anomalies:
        maturity = "SWITCH_CANDIDATE"
        replace_v1 = True
        recommendation = "La V2 est candidate sérieuse au remplacement de V1 en préprod officielle."
    else:
        if trend == "DEGRADING":
            maturity = "SWITCH_CANDIDATE"
            replace_v1 = True
            recommendation = "La V2 est globalement prête mais la tendance récente demande prudence avant bascule définitive."
        else:
            maturity = "OFFICIAL_READY"
            replace_v1 = True
            recommendation = "La V2 peut devenir la version officielle en préprod sans réserve majeure."

    return {
        "maturity_level": maturity,
        "replace_v1_allowed": replace_v1,
        "recommendation": recommendation,
        "criteria_snapshot": {
            "readiness_score": score,
            "close_trades_total": close_trades,
            "win_rate_pct": win_rate,
            "trend": trend,
            "anomalies_count": len(anomalies) if isinstance(anomalies, list) else 0,
        }
    }
