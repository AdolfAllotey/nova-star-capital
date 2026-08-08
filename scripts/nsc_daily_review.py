from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request


DATA_DIR = Path("/opt/nsc/data/preprod")

EXECUTION_PLAN = DATA_DIR / "trading" / "execution_plan.json"
OPEN_POSITIONS = DATA_DIR / "trading" / "open_positions.json"
EXIT_EVENTS = DATA_DIR / "trading" / "exit_events.json"
PNL_STATE = DATA_DIR / "analysis" / "pnl_state.json"
PORTFOLIO_STATE = DATA_DIR / "portfolio" / "state" / "portfolio_state.json"
PORTFOLIO_STATE_ALT = DATA_DIR / "portfolio_state.json"
TOP_MOVERS = DATA_DIR / "market" / "top_movers_combined.json"

EQ_OFF_FILLS = DATA_DIR / "equities_offensive" / "execution" / "simulated_fills.jsonl"
EQ_OFF_AUDIT = DATA_DIR / "equities_offensive" / "reporting" / "audit_trail.jsonl"
DEF_SIGNAL = DATA_DIR / "defensive" / "defensive_signal.json"
DEF_STATE = DATA_DIR / "defensive" / "defensive_state.json"
BOND_STATE = DATA_DIR / "bonds" / "bond_state.json"
METALS_STATE = DATA_DIR / "metals" / "metals_state.json"
REBALANCE_PLAN = DATA_DIR / "portfolio" / "rebalance_plan.json"
FUNDING_PLAN = DATA_DIR / "portfolio" / "funding_plan.json"
DOC_HEALTH = DATA_DIR / "documentation" / "documentation_health.json"


def load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_jsonl(path: Path):
    rows = []
    try:
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def age_hours(ts, now):
    dt = parse_dt(ts)
    if not dt:
        return None
    return (now - dt).total_seconds() / 3600


def freshness_label(ts, now, warn_hours=24):
    h = age_hours(ts, now)
    if h is None:
        return "unknown"
    return "fresh" if h <= warn_hours else f"stale ({h:.1f}h)"


def load_portfolio_state():
    for path in (PORTFOLIO_STATE, PORTFOLIO_STATE_ALT):
        doc = load_json(path, {})
        if isinstance(doc, dict) and isinstance(doc.get("bricks"), dict):
            return doc

    try:
        with urllib.request.urlopen("http://localhost:8000/api/portfolio-state", timeout=3) as r:
            doc = json.loads(r.read().decode("utf-8"))
            if isinstance(doc, dict):
                return doc
    except Exception:
        pass

    return {}


def num(v, default=0.0):
    try:
        return float(v or default)
    except Exception:
        return default


def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def eur(v):
    return f"{num(v):,.2f} €".replace(",", " ")


def pct(v):
    return f"{num(v):.2f}%"


def run_pam_snapshot():
    try:
        import subprocess
        subprocess.run(
            ["/opt/nsc-venv/bin/python", "/opt/nsc/app/src/v2/activity_monitor/activity_monitor.py"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

def run_market_memory_snapshot():
    try:
        import subprocess
        subprocess.run(
            ["/opt/nsc-venv/bin/python", "/opt/nsc/app/src/v2/market_memory/market_memory_engine.py"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass



def load_market_memory():
    from pathlib import Path
    import json

    path = Path("/opt/nsc/data/preprod/market_memory/market_memory.json")

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def print_market_memory():
    mm = load_market_memory()

    print()
    print("16) MARKET MEMORY")
    print("------------------------------")

    if not mm:
        print("Market Memory unavailable.")
        return

    print(f"Assets tracked : {mm.get('assets_count',0)}")
    print()
    assets = mm.get("top_assets", []) or []
    tradables = [a for a in assets if a.get("tradable") or "TRADABLE" in str(a.get("current_verdict", ""))]
    persistent = sorted(assets, key=lambda a: (a.get("observations_count") or 0), reverse=True)
    strongest = sorted(assets, key=lambda a: (a.get("current_meta_rank") or 0), reverse=True)
    fading = [
        a for a in assets
        if isinstance(a.get("max_gain_24h"), (int, float))
        and isinstance(a.get("current_chg_24h"), (int, float))
        and a.get("max_gain_24h") - a.get("current_chg_24h") >= 20
    ]

    print("Market Memory Insight:")
    print(f"  - Most persistent      : {persistent[0].get('symbol') if persistent else '-'} | obs={persistent[0].get('observations_count') if persistent else '-'}")
    print(f"  - Best tradable        : {tradables[0].get('symbol') if tradables else '-'} | verdict={tradables[0].get('current_verdict') if tradables else '-'}")
    print(f"  - Strongest meta asset : {strongest[0].get('symbol') if strongest else '-'} | meta={strongest[0].get('current_meta_rank') if strongest else '-'}")
    print(f"  - Momentum fading      : {fading[0].get('symbol') if fading else 'none'}")
    print()

    for asset in assets[:10]:

        symbol = asset.get("symbol","-")
        obs = asset.get("observations_count","-")
        gain = asset.get("max_gain_24h")
        current = asset.get("current_chg_24h")
        verdict = asset.get("current_verdict","-")
        meta = asset.get("current_meta_rank")

        gain_txt = f"{gain:.2f}%" if isinstance(gain,(int,float)) else "-"
        cur_txt = f"{current:.2f}%" if isinstance(current,(int,float)) else "-"
        meta_txt = f"{meta:.2f}" if isinstance(meta,(int,float)) else "-"

        print(
            f"{symbol:8s}"
            f" Obs:{obs:3} "
            f" Max:{gain_txt:>8} "
            f" Now:{cur_txt:>8} "
            f" Meta:{meta_txt:>6} "
            f"{verdict}"
        )



def print_executive_market_brief():
    doc_health = load_json(DOC_HEALTH, {})
    import json
    from pathlib import Path

    def load(path, default):
        try:
            p = Path(path)
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
        except Exception:
            return default

    mm = load("/opt/nsc/data/preprod/market_memory/market_memory.json", {})
    meta_val = load("/opt/nsc/data/preprod/discovery/meta_validation.json", {})
    rankings = load("/opt/nsc/data/preprod/discovery/meta_rankings.json", {})
    pam = load("/opt/nsc/app/data/preprod/activity/activity_dashboard.json", {})
    exec_plan = load("/opt/nsc/data/preprod/trading/execution_plan.json", {})

    assets = mm.get("top_assets", []) or []
    top = (rankings.get("items") or [{}])[0]
    pam_summary = pam.get("summary", {})
    engines = pam.get("engines", []) or []
    execution_orders = exec_plan.get("orders", []) or []

    crypto = next((e for e in engines if e.get("id") == "crypto"), {})
    crypto_current = float(crypto.get("capital_pct") or 0)
    crypto_target = float(crypto.get("target_pct") or 0)
    crypto_gap = round(crypto_current - crypto_target, 2)

    top_symbol = top.get("symbol", "-")
    execution_symbols = {
        str(o.get("symbol") or o.get("pair") or "").upper().replace("USDT", "")
        for o in execution_orders
    }

    fading = [
        a for a in assets
        if isinstance(a.get("max_gain_24h"), (int, float))
        and isinstance(a.get("current_chg_24h"), (int, float))
        and a.get("max_gain_24h") - a.get("current_chg_24h") >= 20
    ]

    leader_in_execution = top_symbol in execution_symbols if top_symbol != "-" else False
    warnings = []

    if crypto_gap > 5:
        warnings.append(f"Crypto exposure is {crypto_gap:.2f} pts above target.")
    if fading:
        warnings.append(f"Momentum fading detected on {fading[0].get('symbol')}.")
    if top_symbol != "-" and not leader_in_execution:
        warnings.append(f"Top Meta asset {top_symbol} is not currently visible in execution orders.")
    if meta_val.get("strategy_drift") is True:
        warnings.append("Meta Validation reports strategy drift.")

    try:
        from datetime import datetime, timezone
        out = Path("/opt/nsc/data/preprod/market_brief/executive_market_brief.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": "executive_market_brief_v2",
            "market_posture": pam.get("status", "unknown"),
            "portfolio_health": pam_summary.get("portfolio_health"),
            "activity_score": pam_summary.get("activity_score"),
            "meta_alignment": meta_val.get("decision_alignment_score"),
            "top_opportunity": top_symbol,
            "top_verdict": top.get("verdict"),
            "leader_in_execution": leader_in_execution,
            "crypto_current_pct": crypto_current,
            "crypto_target_pct": crypto_target,
            "crypto_gap_pct": crypto_gap,
            "market_memory_assets": mm.get("assets_count", 0),
            "alerts": warnings,
            "pipeline_health": meta_val.get("pipeline_health"),
            "execution_quality": meta_val.get("execution_quality"),
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        hist = Path("/opt/nsc/data/preprod/market_brief/history")
        hist.mkdir(parents=True, exist_ok=True)
        stamp = payload["generated_at"].replace(":", "").replace("-", "").split(".")[0]
        (hist / f"executive_market_brief_{stamp}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass

    print()
    print("17) DOCUMENTATION CENTER")
    print("------------------------------")
    print(f"Documentation health : {pct(doc_health.get('documentation_health'))}")
    print(f"Coverage score       : {pct(doc_health.get('coverage_score'))}")
    print(f"Documents indexed    : {doc_health.get('documents_count', 0)}")
    print(f"Status               : {doc_health.get('status', 'unknown')}")
    print(f"Missing metadata     : classification={doc_health.get('missing_classification', 0)} | status={doc_health.get('missing_status', 0)}")
    print(f"Too short documents  : {doc_health.get('too_short_documents', 0)}")
    print()

    print("18) EXECUTIVE MARKET BRIEF")
    print("-------------------------")
    print(f"Market posture      : {pam.get('status', 'unknown')}")
    print(f"Portfolio health    : {pam_summary.get('portfolio_health', '-')}%")
    print(f"Activity score      : {pam_summary.get('activity_score', '-')}%")
    print(f"Meta alignment      : {meta_val.get('decision_alignment_score', '-')}%")
    print(f"Top opportunity     : {top_symbol} | {top.get('verdict', '-')}")
    print(f"Leader in execution : {'yes' if leader_in_execution else 'no'}")
    print(f"Crypto allocation   : {crypto_current:.2f}% / target {crypto_target:.2f}% | gap {crypto_gap:+.2f} pts")
    print(f"Market memory       : {mm.get('assets_count', 0)} assets tracked")

    print()
    print("Alerts:")
    if warnings:
        for w in warnings:
            print(f"  - {w}")
    else:
        print("  - none")

    print()
    print("Synthesis:")
    if warnings:
        print(
            f"  NSC remains in monitored simulated mode, but {len(warnings)} market/portfolio point(s) require monitoring. "
            f"Market Memory tracks {mm.get('assets_count', 0)} assets, with {top_symbol} leading the Meta Ranking. "
            f"Pipeline health is {meta_val.get('pipeline_health', 'unknown')} and execution quality is {meta_val.get('execution_quality', 'unknown')}."
        )
    else:
        print(
            f"  NSC remains in monitored simulated mode. Market Memory tracks {mm.get('assets_count', 0)} assets, "
            f"with {top_symbol} currently leading the Meta Ranking. Pipeline health is {meta_val.get('pipeline_health', 'unknown')} "
            f"and execution quality is {meta_val.get('execution_quality', 'unknown')}."
        )

def run_executive_decision_snapshot():
    try:
        import subprocess
        subprocess.run(
            ["/opt/nsc-venv/bin/python", "/opt/nsc/app/src/v2/executive_decision/executive_decision_engine.py"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def load_executive_decision():
    from pathlib import Path
    import json
    path = Path("/opt/nsc/data/preprod/executive_decision/executive_decision.json")
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None

def print_executive_decision():
    d = load_executive_decision()

    print()
    print("19) EXECUTIVE DECISION")
    print("----------------------")

    if not d:
        print("Executive Decision unavailable.")
        return

    history = d.get("history", []) or []
    decision = d.get("decision", "-")
    same = [h for h in history if h.get("decision") == decision]
    stability = round((len(same) / len(history)) * 100, 2) if history else 0

    changes = 0
    for i in range(1, len(history)):
        if history[i].get("decision") != history[i-1].get("decision"):
            changes += 1

    streak = 0
    for h in history:
        if h.get("decision") == decision:
            streak += 1
        else:
            break

    score = float(d.get("decision_score") or 0)
    confidence_loss = round(max(0, 100 - score), 2)

    print(f"Decision          : {decision}")
    print(f"Recommended asset : {d.get('recommended_symbol','-')}")
    print(f"Decision score    : {score:.2f}/100")
    print(f"Confidence loss   : {confidence_loss:.2f} pts")
    print(f"Execution ready   : {d.get('execution_ready')}")
    print(f"Leader in exec    : {d.get('leader_in_execution')}")
    print(f"Risk level        : {d.get('risk_level','-')}")
    print(f"Crypto gap        : {d.get('crypto_gap_pct','-')} pts")
    print(f"Decision stability: {stability:.2f}% | changes={changes} | streak={decision} x{streak}")
    print()
    print("Top decision drivers:")
    for driver in (d.get("drivers") or [])[:5]:
        print(f"  - {driver.get('driver','-')} | weight={driver.get('weight','-')} | value={driver.get('value','-')}")
    print()
    print("Narrative:")
    print(f"  {d.get('narrative','-')}")


def main():
    run_pam_snapshot()
    run_market_memory_snapshot()
    run_executive_decision_snapshot()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=1)

    execution = load_json(EXECUTION_PLAN, {})
    opens = load_json(OPEN_POSITIONS, [])
    exits = load_json(EXIT_EVENTS, [])
    pnl = load_json(PNL_STATE, {})
    portfolio = load_portfolio_state()
    movers = load_json(TOP_MOVERS, {})

    eq_off_fills = load_jsonl(EQ_OFF_FILLS)
    eq_off_audit = load_jsonl(EQ_OFF_AUDIT)
    def_signal = load_json(DEF_SIGNAL, {})
    def_state = load_json(DEF_STATE, {})
    bond_state = load_json(BOND_STATE, {})
    metals_state = load_json(METALS_STATE, {})
    rebalance = load_json(REBALANCE_PLAN, {})
    funding = load_json(FUNDING_PLAN, {})
    doc_health = load_json(DOC_HEALTH, {})

    if not isinstance(opens, list):
        opens = []
    if not isinstance(exits, list):
        exits = []

    recent_exits = []
    for e in exits:
        ts = parse_dt(e.get("timestamp") or e.get("ts") or e.get("closed_at"))
        if ts and ts >= since:
            recent_exits.append(e)

    orders = execution.get("orders", []) if isinstance(execution.get("orders"), list) else []
    bricks = portfolio.get("bricks", {}) if isinstance(portfolio.get("bricks"), dict) else {}

    pnl_summary = pnl.get("summary", {}) if isinstance(pnl, dict) else {}

    stale = [e for e in recent_exits if e.get("exit_type") == "stale_plan_cleanup"]
    trading_exits = [e for e in recent_exits if e.get("exit_type") != "stale_plan_cleanup"]
    realized_24h = sum(num(e.get("pnl")) for e in trading_exits)

    winners = [e for e in trading_exits if num(e.get("pnl")) > 0]
    losers = [e for e in trading_exits if num(e.get("pnl")) < 0]

    recent_stale_2h = []
    stale_since = now - timedelta(minutes=90)
    for e in stale:
        ts = parse_dt(e.get("timestamp") or e.get("ts") or e.get("closed_at"))
        if ts and ts >= stale_since:
            recent_stale_2h.append(e)

    resolved_exits_24h = len(winners) + len(losers)
    win_rate_24h = (len(winners) / resolved_exits_24h * 100.0) if resolved_exits_24h > 0 else 0.0

    by_strategy = defaultdict(float)
    by_exit_type = Counter()
    by_symbol = defaultdict(float)

    for e in trading_exits:
        by_strategy[e.get("strategy") or "unknown"] += num(e.get("pnl"))
        by_exit_type[e.get("exit_type") or "unknown"] += 1
        by_symbol[e.get("symbol") or "unknown"] += num(e.get("pnl"))

    recent_eq_fills = []
    for f in eq_off_fills:
        ts = parse_dt(f.get("ts") or f.get("timestamp"))
        if ts and ts >= since:
            recent_eq_fills.append(f)

    eq_buy = sum(1 for f in recent_eq_fills if str(f.get("side")).upper() == "BUY")
    eq_sell = sum(1 for f in recent_eq_fills if str(f.get("side")).upper() == "SELL")
    eq_symbols = sorted({str(f.get("symbol")) for f in recent_eq_fills if f.get("symbol")})

    print("\n==============================")
    print("NSC DAILY REVIEW — PREPROD")
    print("==============================")
    print(f"Generated UTC : {now.isoformat(timespec='seconds')}")
    print(f"Window        : last 24h")
    print()

    print("1) GLOBAL CRYPTO PNL")
    print("--------------------")
    print(f"Realized PnL total   : {eur(pnl_summary.get('realized_pnl_eur'))}")
    print(f"Unrealized PnL total : {eur(pnl_summary.get('unrealized_pnl_eur'))}")
    print(f"Total crypto PnL     : {eur(pnl_summary.get('total_pnl_eur'))}")
    print(f"Open positions       : {pnl_summary.get('open_positions_count', len(opens))}")
    print(f"Win rate 24h         : {pct(win_rate_24h)}")
    print(f"24h realized PnL     : {eur(realized_24h)}")
    print()

    print("2) ACTIONS REALISEES SUR 24H")
    print("----------------------------")
    print(f"Trading exits 24h     : {len(trading_exits)}")
    print(f"Technical cleanup 24h : {len(stale)}")
    print(f"Winners               : {len(winners)}")
    print(f"Losers                : {len(losers)}")
    print(f"Stale cleanup         : {len(stale)}")
    print()

    print("3) TOP WINNERS / LOSERS 24H")
    print("---------------------------")
    sorted_symbols = sorted(by_symbol.items(), key=lambda x: x[1])
    print("Worst:")
    for sym, value in sorted_symbols[:5]:
        print(f"  - {sym}: {eur(value)}")
    print("Best:")
    for sym, value in sorted_symbols[-5:][::-1]:
        print(f"  - {sym}: {eur(value)}")
    print()

    print("4) STRATEGIES 24H")
    print("----------------")
    for strat, value in sorted(by_strategy.items(), key=lambda x: x[1]):
        print(f"  - {strat}: {eur(value)}")
    print()

    print("5) EXIT TYPES 24H")
    print("----------------")
    for k, v in by_exit_type.most_common():
        print(f"  - {k}: {v}")
    print()

    print("6) EXECUTION PLAN ACTUEL")
    print("-----------------------")
    gov = execution.get("governance", {}) if isinstance(execution.get("governance"), dict) else {}
    print(f"Generated at     : {execution.get('generated_at')}")
    print(f"Governance mode  : {gov.get('mode')}")
    print(f"Action policy    : {gov.get('action_policy') or execution.get('execution_mode')}")
    print(f"Hard block       : {gov.get('hard_block')}")
    print(f"Orders           : {len(orders)}")
    print(f"Estimated notional: {eur(sum(num(o.get('notional_eur') or o.get('notional')) for o in orders))}")
    print()

    print("Current orders:")
    for o in orders[:10]:
        print(
            f"  - {o.get('symbol')} | {o.get('strategy')} | "
            f"{o.get('exchange')} | {eur(o.get('notional_eur') or o.get('notional'))} | "
            f"score={o.get('meta_score') or o.get('meta_score_pro')} | "
            f"mode={o.get('execution_mode')}"
        )
    print()

    print("7) POSITIONS OUVERTES")
    print("--------------------")
    for p in opens:
        print(
            f"  - {p.get('symbol')} | {p.get('strategy')} | "
            f"notional={eur(p.get('notional_eur'))} | "
            f"unrealized={eur(p.get('unrealized_pnl'))} | "
            f"{pct(p.get('unrealized_pnl_pct'))}"
        )
    print()

    print("8) PORTFOLIO BRICKS — SUMMARY")
    print("-----------------------------")
    if not bricks:
        print("  - No portfolio bricks loaded.")
    else:
        for key, b in sorted(bricks.items()):
            target_w = num(b.get("target_weight_snapshot")) * 100
            current_w = num(b.get("current_weight_estimate")) * 100
            exposure = b.get("current_exposure_eur")
            confidence = num(b.get("confidence"))
            confidence_pct = confidence * 100 if confidence <= 1 else confidence
            role = b.get("portfolio_role") or "-"
            regime = b.get("regime") or "-"
            status = b.get("status") or "-"

            print(
                f"  - {key:<20} | "
                f"status={status:<16} | "
                f"target={target_w:>5.2f}% | "
                f"current={current_w:>5.2f}% | "
                f"exposure={eur(exposure):>12} | "
                f"regime={regime} | "
                f"confidence={confidence_pct:.1f}% | "
                f"role={role}"
            )
    print()

    print("9) NON-CRYPTO BRICKS ACTIVITY")
    print("-----------------------------")

    last_eq_audit = eq_off_audit[-1] if eq_off_audit else {}
    eq_kpis = last_eq_audit.get("kpis", {}) if isinstance(last_eq_audit.get("kpis"), dict) else {}
    print("Offensive equities:")
    print(f"  - 24h fills        : {len(recent_eq_fills)} | buys={eq_buy} | sells={eq_sell}")
    print(f"  - Symbols touched  : {', '.join(eq_symbols[:10]) if eq_symbols else '-'}")
    print(f"  - Open positions   : {eq_kpis.get('open_positions', '-')}")
    print(f"  - Orders final     : {eq_kpis.get('execution_orders_final', '-')}")
    print(f"  - Market regime    : {eq_kpis.get('market_regime', '-')}")
    print(f"  - Audit freshness  : {freshness_label(last_eq_audit.get('ts'), now)}")
    print()

    print("Defensive equities:")
    print(f"  - Signal freshness : {freshness_label(def_signal.get('generated_at'), now)}")
    print(f"  - State freshness  : {freshness_label(def_state.get('generated_at'), now)}")
    print(f"  - Target exposure  : {pct(num(def_signal.get('target_exposure')) * 100)}")
    print(f"  - Confidence       : {pct(num(def_signal.get('confidence')) * 100)}")
    print(f"  - Positions        : {len(def_state.get('positions', [])) if isinstance(def_state.get('positions'), list) else '-'}")
    print()

    print("Bonds / precious metals:")
    print(f"  - Bonds freshness  : {freshness_label(bond_state.get('generated_at'), now, warn_hours=72)} | PnL={eur(bond_state.get('pnl_eur'))}")
    print(f"  - Metals freshness : {freshness_label(metals_state.get('generated_at'), now, warn_hours=72)} | PnL={eur(metals_state.get('pnl_eur'))}")
    print()

    reb_summary = rebalance.get("summary", {}) if isinstance(rebalance.get("summary"), dict) else {}
    print("Rebalance / funding:")
    print(f"  - Rebalance status : {rebalance.get('status', '-')}")
    print(f"  - Proposed actions : {reb_summary.get('actions_proposed', '-')}/{reb_summary.get('actions_total', '-')}")
    print(f"  - Manual approval  : {rebalance.get('manual_approval_required', '-')}")
    print(f"  - Funding status   : {funding.get('status', '-')}")
    print(f"  - Execution allowed: {funding.get('execution_allowed', '-')}")
    print()

    print("10) DISCOVERY / PERSISTENCE")
    print("---------------------------")
    persistence = load_json(DATA_DIR / "discovery" / "persistence_opportunities.json", {})
    tradable = load_json(DATA_DIR / "discovery" / "tradable_opportunities.json", {})
    discovery_summary = load_json(DATA_DIR / "discovery" / "discovery_summary.json", {})

    p_items = persistence.get("items", []) if isinstance(persistence.get("items"), list) else []
    t_items = tradable.get("items", []) if isinstance(tradable.get("items"), list) else []
    active_sources = discovery_summary.get("sources_active", []) if isinstance(discovery_summary.get("sources_active"), list) else []
    missing_sources = discovery_summary.get("sources_missing", []) if isinstance(discovery_summary.get("sources_missing"), list) else []

    print(f"Persistence opportunities : {persistence.get('count', len(p_items))}")
    print(f"Tradable opportunities    : {tradable.get('count', len(t_items))}")
    print(f"Active discovery sources  : {', '.join([str(s.get('source')) for s in active_sources]) if active_sources else '-'}")
    print(f"Missing discovery sources : {', '.join([str(s.get('source')) for s in missing_sources]) if missing_sources else '-'}")

    if p_items:
        print("Top persistence opportunities:")
        for x in p_items[:5]:
            print(
                f"  - {x.get('symbol')} | score={x.get('opportunity_score')} | "
                f"chg24h={pct(x.get('chg_24h'))} | delta={x.get('gain_delta')} | "
                f"sources={','.join(x.get('sources', [])) if isinstance(x.get('sources'), list) else '-'}"
            )
    else:
        print("Top persistence opportunities: -")

    if t_items:
        print("Tradable opportunities:")
        for x in t_items[:5]:
            print(
                f"  - {x.get('symbol')} | score={x.get('opportunity_score')} | "
                f"chg24h={pct(x.get('chg_24h'))} | pair={x.get('pair')}"
            )
    else:
        print("Tradable opportunities: none currently")

    print()

    print("11) META RANKING")
    print("----------------")
    meta = load_json(DATA_DIR / "discovery" / "meta_rankings.json", {})
    meta_items = meta.get("items", []) if isinstance(meta.get("items"), list) else []

    print(f"Meta rankings count : {meta.get('count', len(meta_items))}")
    print(f"Recommended count   : {meta.get('recommended_count', 0)}")
    print(f"Mode                : {meta.get('mode', '-')}")

    if meta_items:
        print("Top meta-ranked tokens:")
        for x in meta_items[:8]:
            flags = x.get("risk_flags", [])
            flags_txt = ",".join(flags) if isinstance(flags, list) and flags else "-"
            exp = x.get("explainability", {}) if isinstance(x.get("explainability"), dict) else {}
            breakdown = exp.get("breakdown", {}) if isinstance(exp.get("breakdown"), dict) else {}
            verdict = x.get("verdict") or exp.get("verdict") or "-"

            print(
                f"  - {x.get('symbol')} | rank={x.get('meta_rank')} | verdict={verdict} | "
                f"tradable={x.get('tradable')} | chg24h={pct(x.get('chg_24h'))} | flags={flags_txt}"
            )
            print(
                f"      drivers: discovery={breakdown.get('discovery', 0)} | "
                f"persistence={breakdown.get('persistence', 0)} | "
                f"social={breakdown.get('social', 0)} | "
                f"momentum={breakdown.get('momentum', 0)} | "
                f"sources={breakdown.get('sources', 0)}"
            )
    else:
        print("Top meta-ranked tokens: -")

    print()

    print("12) META VALIDATION")
    print("-------------------")
    validation = load_json(DATA_DIR / "discovery" / "meta_validation.json", {})
    coverage = validation.get("coverage", {}) if isinstance(validation.get("coverage"), dict) else {}

    print(f"Engine               : {validation.get('engine', '-')}")
    print(f"Pipeline health      : {validation.get('pipeline_health', '-')}")
    print(f"Decision alignment   : {pct(validation.get('decision_alignment_score'))}")
    print(f"Opportunity coverage : {pct(validation.get('opportunity_coverage_score'))}")
    print(f"Execution quality    : {validation.get('execution_quality', '-')}")
    print(f"Strategy drift       : {validation.get('strategy_drift', '-')}")

    print(
        f"Coverage             : {coverage.get('matched_top20', '-')}/"
        f"{coverage.get('execution_orders', '-')} orders matched Top 20 Meta"
    )

    exec_symbols = validation.get("execution_symbols", [])
    matched = validation.get("matched_top_tradable", [])
    missing_hc = validation.get("missing_high_conviction", [])

    print(f"Execution symbols    : {', '.join(exec_symbols) if isinstance(exec_symbols, list) and exec_symbols else '-'}")
    print(f"Matched tradables    : {', '.join(matched) if isinstance(matched, list) and matched else '-'}")

    hist = load_json(DATA_DIR / "discovery" / "meta_validation_history_summary.json", {})
    if hist:
        print("Trend:")
        print(f"  - History count          : {hist.get('history_count', '-')}")
        print(f"  - Avg decision alignment : {pct(hist.get('avg_decision_alignment'))}")
        print(f"  - Avg opportunity cover. : {pct(hist.get('avg_opportunity_coverage'))}")
        print(f"  - Drift count            : {hist.get('drift_count', '-')}")
        print(f"  - Healthy ratio          : {pct(hist.get('healthy_ratio'))}")

    health = load_json(DATA_DIR / "discovery" / "meta_health_monitor.json", {})
    if health:
        alerts = health.get("alerts", [])
        alerts_txt = ", ".join(alerts) if isinstance(alerts, list) and alerts else "-"
        print("Health Monitor:")
        print(f"  - Status                 : {health.get('status', '-')}")
        print(f"  - Severity               : {health.get('severity', '-')}")
        print(f"  - Alerts                 : {alerts_txt}")
        print(f"  - Summary                : {health.get('summary', '-')}")

    if isinstance(missing_hc, list) and missing_hc:
        print("Missing high conviction:")
        for x in missing_hc[:5]:
            print(f"  - {x.get('symbol')} | rank={x.get('meta_rank')} | verdict={x.get('verdict')}")
    else:
        print("Missing high conviction: none")

    print()

    try:
        pam_path = Path("/opt/nsc/app/data/preprod/activity/activity_dashboard.json")
        pam = json.loads(pam_path.read_text(encoding="utf-8")) if pam_path.exists() else {}
    except Exception:
        pam = {}
    print("13) TOP MOVERS")
    print("--------------")
    items = movers.get("items", []) if isinstance(movers.get("items"), list) else []
    for m in items[:10]:
        print(
            f"  - {m.get('symbol')} | {m.get('source')} | "
            f"{pct(m.get('chg_24h'))} | pair={m.get('pair')}"
        )
    print()

    print()
    print("14) PORTFOLIO ACTIVITY MONITOR")
    print("------------------------------")
    pam_summary = pam.get("summary", {}) if isinstance(pam, dict) else {}
    pam_engines = pam.get("engines", []) if isinstance(pam, dict) else []
    pam_alerts = pam.get("alerts", []) if isinstance(pam, dict) else []

    print(f"Status              : {pam.get('status', '-') if isinstance(pam, dict) else '-'}")
    print(f"Portfolio health    : {pam_summary.get('portfolio_health', '-')}%")
    print(f"Activity score      : {pam_summary.get('activity_score', '-')}%")
    print(f"Capital deployment  : {pam_summary.get('capital_deployment_pct', '-')}%")
    print(f"Investment engines  : {pam_summary.get('investment_engines_active', '-')}/{pam_summary.get('investment_engines_total', '-')}")
    print(f"Alerts              : {pam_summary.get('alerts_count', len(pam_alerts))}")

    print()
    print("Investment engines:")
    for e in pam_engines:
        if e.get("group") != "investment":
            continue
        print(
            f"  - {e.get('id'):20} | "
            f"health={e.get('health_score', '-')} | "
            f"activity={e.get('activity_score', '-')} | "
            f"capital={float(e.get('capital_pct', 0)):6.2f}% | "
            f"target={float(e.get('target_pct', 0)):6.2f}% | "
            f"orders={e.get('orders_count', 0)} | "
            f"fills={e.get('fills_count', 0)} | "
            f"positions={e.get('positions_count', 0)}"
        )

    if pam_alerts:
        print()
        print("PAM alerts:")
        for a in pam_alerts[:8]:
            print(f"  - {a.get('severity', '-')} | {a.get('engine', '-')} | {a.get('type', '-')} | {a.get('message', '-')}")
    else:
        print()
        print("PAM alerts: none")
    print("15) POINTS DE CONTROLE")
    print("----------------------")
    if num(pnl_summary.get("total_pnl_eur")) < 0:
        print("  ⚠ Crypto encore négative : surveiller sélection momentum / stop-loss / stale cleanup.")
    if len(recent_stale_2h) >= 3:
        print(f"  ⚠ Stale cleanup récent élevé ({len(recent_stale_2h)}/90min) : vérifier rotation excessive ou nettoyage trop agressif.")
    elif len(stale) >= 10:
        print(f"  ℹ Beaucoup de stale_plan_cleanup sur 24h ({len(stale)}), mais seulement {len(recent_stale_2h)} sur 90min : tendance à surveiller.")
    if orders and all(str(o.get("execution_mode")).upper() == "SIMULATED_ONLY" for o in orders):
        print("  ✅ Préprod safe : tous les ordres restent simulés.")
    if len(bricks) > 1 and len(orders) > 0:
        print("  ℹ Les ordres actuels visibles concernent surtout la crypto : vérifier demain si les autres briques agissent selon régime.")
    if len(recent_eq_fills) == 0:
        print("  ℹ Aucun fill actions offensives sur 24h : normal si poche déjà positionnée, à surveiller.")
    if p_items and not t_items:
        print(f"  ℹ Discovery : {len(p_items)} opportunité(s) persistante(s) externe(s), mais aucune tradable confirmée Binance/MEXC → observation only.")
    if t_items:
        print(f"  ✅ Discovery : {len(t_items)} opportunité(s) persistante(s) tradable(s) détectée(s) et éligible(s) au pipeline.")
    best_tradable_meta = None
    for x in meta_items:
        if x.get("tradable") is True and "extreme_pump" not in (x.get("risk_flags") or []):
            best_tradable_meta = x
            break

    if best_tradable_meta:
        print(
            f"  ℹ Meta Ranking : meilleur token tradable = {best_tradable_meta.get('symbol')} "
            f"| verdict={best_tradable_meta.get('verdict')} "
            f"| rank={best_tradable_meta.get('meta_rank')} "
            f"| chg24h={pct(best_tradable_meta.get('chg_24h'))}."
        )
    if validation:
        health = validation.get("pipeline_health")
        align = validation.get("decision_alignment_score")
        drift = validation.get("strategy_drift")
        quality = validation.get("execution_quality")

        if health == "healthy" and drift is False:
            print(
                f"  ✅ Meta Validation : pipeline healthy | alignment={pct(align)} | "
                f"quality={quality} | drift=False."
            )
        elif drift is True:
            print(
                f"  ⚠ Meta Validation : strategy drift détecté | alignment={pct(align)} | "
                f"health={health} | quality={quality}."
            )
        else:
            print(
                f"  ℹ Meta Validation : health={health} | alignment={pct(align)} | "
                f"quality={quality} | drift={drift}."
            )

    health_monitor = load_json(DATA_DIR / "discovery" / "meta_health_monitor.json", {})

    if isinstance(health_monitor, dict) and health_monitor:
        hm_status = str(health_monitor.get("status") or "")
        hm_severity = str(health_monitor.get("severity") or "")
        hm_alerts = health_monitor.get("alerts") or []

        if hm_status == "healthy":
            print("  ✅ Meta Health Monitor : healthy.")
        elif hm_status == "warming_up":
            print(
                f"  ℹ Meta Health Monitor : warming up "
                f"({health_monitor.get('history_count', 0)} run(s))."
            )
        elif hm_severity in ("warning", "critical"):
            alerts = ", ".join(hm_alerts) if isinstance(hm_alerts, list) else "-"
            print(
                f"  ⚠ Meta Health Monitor : status={hm_status} | "
                f"severity={hm_severity} | alerts={alerts}."
            )
        else:
            print(
                f"  ℹ Meta Health Monitor : status={hm_status} | "
                f"severity={hm_severity}."
            )
        order_symbols = {
            str(o.get("symbol") or "").replace("usdt", "").replace("USDT", "").upper()
            for o in orders
            if isinstance(o, dict)
        }
        best_symbol = str(best_tradable_meta.get("symbol") or "").upper()

        if best_symbol in order_symbols:
            print(f"  ✅ Alignement Meta/Execution : {best_symbol} est bien présent dans l'Execution Plan.")
        else:
            print(f"  ⚠ Alignement Meta/Execution : {best_symbol} est le meilleur tradable Meta, mais absent de l'Execution Plan.")
    if freshness_label(bond_state.get("generated_at"), now, warn_hours=72).startswith("stale"):
        print("  ⚠ Bonds state stale : vérifier timer/state updater obligations.")
    if freshness_label(metals_state.get("generated_at"), now, warn_hours=72).startswith("stale"):
        print("  ⚠ Metals state stale : vérifier timer/state updater precious metals.")
    print()

    print_market_memory()
    print_executive_market_brief()
    print_executive_decision()

    print("==============================")
    print("END DAILY REVIEW")
    print("==============================")


if __name__ == "__main__":
    main()
