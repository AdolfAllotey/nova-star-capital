"""
Stress Test Engine (light) – Nova Star Capital

Objectif : simuler des chocs de marché (-5%, -10%, -20%) sur les positions ouvertes
et mesurer l’impact sur le PnL et le risque global. Sortie :
data/analysis/stress_test_overview.json

Utilise :
- data/trading/open_positions.json
- data/trading/capital_allocation.json (total_capital)
- data/market/ohlcv_combined.json (prix actuels)

Version "hedge fund light" : simple, robuste, lisible.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger("stress_test_engine_light")

# ---------------------------------------------------------------------------
# Paths & constantes
# ---------------------------------------------------------------------------

def _detect_root_dir() -> Path:
    """
    Détecte le ROOT_DIR du projet en remontant jusqu'à trouver /src et /data.
    """
    p = Path(__file__).resolve()
    for _ in range(6):
        if (p / "src").exists() and (p / "data").exists():
            return p
        p = p.parent
    # fallback : parent direct de src/v2/analysis
    return Path(__file__).resolve().parents[3]


ROOT_DIR: Path = _detect_root_dir()
DATA_DIR: Path = ROOT_DIR / "data"

STRESS_OUTPUT_FILE: Path = DATA_DIR / "analysis" / "stress_test_overview.json"

# Scénarios de choc : (nom, choc en %)
STRESS_SCENARIOS = [
    ("mild_-5%", -0.05),
    ("moderate_-10%", -0.10),
    ("severe_-20%", -0.20),
]


# ---------------------------------------------------------------------------
# Modèles de données
# ---------------------------------------------------------------------------

@dataclass
class Position:
    symbol: str
    amount: float
    entry_price: float
    side: str = "long"  # "long" uniquement pour le moment
    pocket: Optional[str] = None  # trading / long_term / etc.


@dataclass
class ScenarioResult:
    name: str
    shock_pct: float
    pnl: float
    pnl_pct: float
    max_position_loss_pct: float


@dataclass
class StressTestOverview:
    timestamp: str
    nb_positions: int
    total_capital: float
    base_unrealized_pnl: float
    base_unrealized_pnl_pct: float
    scenarios: List[ScenarioResult]
    worst_scenario: Optional[ScenarioResult]
    stress_score: float
    risk_flag: str
    meta: Dict[str, Any]


# ---------------------------------------------------------------------------
# Utilitaires de chargement
# ---------------------------------------------------------------------------

def _load_open_positions() -> List[Position]:
    path = DATA_DIR / "trading" / "open_positions.json"
    raw = load_json_file(path, default=[])
    positions: List[Position] = []

    if not isinstance(raw, list):
        logger.warning(
            "[stress_test] open_positions.json n'est pas une liste (%s), ignoré.",
            type(raw),
        )
        return positions

    for item in raw:
        try:
            symbol = str(item.get("symbol") or item.get("token") or "").lower()
            if not symbol:
                continue
            amount = float(item.get("amount", 0.0))
            entry_price = float(item.get("entry_price", item.get("entry", 0.0)))
            if amount <= 0 or entry_price <= 0:
                # position invalide pour le stress test
                continue
            side = str(item.get("side", "long")).lower()
            pocket = item.get("pocket")
            positions.append(
                Position(
                    symbol=symbol,
                    amount=amount,
                    entry_price=entry_price,
                    side=side,
                    pocket=pocket,
                )
            )
        except Exception as exc:
            logger.warning(
                "[stress_test] Position invalide dans open_positions.json: %s (item=%s)",
                exc,
                item,
            )
    logger.info("[stress_test] %d positions ouvertes chargées.", len(positions))
    return positions


def _load_total_capital() -> float:
    alloc = load_capital_allocation(trading_dir=DATA_DIR / "trading", default={})
    total = float(alloc.get("total_budget", 0.0) or 0.0)
    if total <= 0:
        logger.warning("[stress_test] total_budget absent ou <= 0 dans capital_allocation.json, utilisation de 0.0.")
    return total

def _load_current_prices() -> Dict[str, float]:
    """
    Charge les prix actuels depuis ohlcv_combined.json.

    Format attendu flexible :
    - {"bitcoin": {"close": [...]} }
    - {"bitcoin": {"closes": [...]} }
    - {"bitcoin": {"price": 43000.0} }
    - {"bitcoin": 43000.0}
    """
    path = DATA_DIR / "market" / "ohlcv_combined.json"
    data = load_json_file(path, default={})
    prices: Dict[str, float] = {}

    if not isinstance(data, dict):
        logger.warning(
            "[stress_test] ohlcv_combined.json n'est pas un dict (%s), ignoré.",
            type(data),
        )
        return prices

    for symbol, payload in data.items():
        price: Optional[float] = None

        # Cas direct : nombre
        if isinstance(payload, (int, float)):
            price = float(payload)
        elif isinstance(payload, dict):
            # prix unique
            if "price" in payload:
                try:
                    price = float(payload["price"])
                except Exception:
                    price = None

            # ou dernière close
            if price is None:
                for key in ("close", "closes", "prices"):
                    seq = payload.get(key)
                    if isinstance(seq, list) and seq:
                        try:
                            price = float(seq[-1])
                            break
                        except Exception:
                            continue

        if price is not None and price > 0:
            prices[str(symbol).lower()] = price

    logger.info(
        "[stress_test] %d prix actuels chargés depuis ohlcv_combined.json.",
        len(prices),
    )
    return prices


# ---------------------------------------------------------------------------
# Logique de stress-test
# ---------------------------------------------------------------------------

def _compute_base_unrealized_pnl(
    positions: List[Position], prices: Dict[str, float]
) -> float:
    """
    PnL non réalisé actuel (mark-to-market).
    """
    total_pnl = 0.0
    for pos in positions:
        current_price = prices.get(pos.symbol)
        if current_price is None or current_price <= 0:
            continue
        if pos.side == "short":
            pnl = (pos.entry_price - current_price) * pos.amount
        else:
            pnl = (current_price - pos.entry_price) * pos.amount
        total_pnl += pnl
    return total_pnl


def _apply_scenario(
    positions: List[Position],
    prices: Dict[str, float],
    shock_pct: float,
    total_capital: float,
    name: str,
) -> ScenarioResult:
    """
    Applique un choc de prix uniforme à toutes les positions.
    shock_pct négatif = baisse des prix (ex: -0.10 = -10%).
    """
    total_pnl = 0.0
    max_position_loss_pct = 0.0

    for pos in positions:
        current_price = prices.get(pos.symbol)
        if current_price is None or current_price <= 0:
            continue

        shocked_price = current_price * (1.0 + shock_pct)

        # PnL scenario
        if pos.side == "short":
            pnl_scenario = (pos.entry_price - shocked_price) * pos.amount
        else:
            pnl_scenario = (shocked_price - pos.entry_price) * pos.amount

        total_pnl += pnl_scenario

        # perte % par rapport au capital total pour cette position
        if total_capital > 0:
            pos_loss_pct = pnl_scenario / total_capital * 100.0
            if pos_loss_pct < max_position_loss_pct:
                max_position_loss_pct = pos_loss_pct

    pnl_pct = (total_pnl / total_capital * 100.0) if total_capital > 0 else 0.0

    return ScenarioResult(
        name=name,
        shock_pct=shock_pct,
        pnl=total_pnl,
        pnl_pct=pnl_pct,
        max_position_loss_pct=max_position_loss_pct,
    )


def _compute_stress_score(scenarios: List[ScenarioResult]) -> float:
    """
    Convertit le pire scénario en score 0–100.

    Heuristique simple :
    - worst_loss_pct >= 0  → ~95
    - -5% → ~90
    - -10% → ~80
    - -20% → ~60
    - -30% → ~40
    - < -40% → plancher à 10
    """
    if not scenarios:
        return 100.0

    worst = min((s.pnl_pct for s in scenarios), default=0.0)
    # worst est typiquement négatif
    score = 100.0 + worst * 2.0  # -10% => 80, -20% => 60, etc.
    score = max(0.0, min(100.0, score))

    # On évite un 100 parfait si on a quand même des pertes non négligeables
    if worst < -1.0 and score > 95.0:
        score = 95.0

    return score


def _derive_risk_flag(stress_score: float) -> str:
    """
    Traduit le score en label de risque.
    """
    if stress_score >= 85:
        return "ok"
    if stress_score >= 65:
        return "watch"
    if stress_score >= 45:
        return "reduce"
    return "panic"


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

def run_stress_test() -> StressTestOverview:
    """
    Fonction principale de calcul du stress test.
    """
    logger.info(
        "[stress_test_engine_light] ROOT_DIR=%s, DATA_DIR=%s",
        ROOT_DIR,
        DATA_DIR,
    )

    positions = _load_open_positions()
    total_capital = _load_total_capital()
    prices = _load_current_prices()

    timestamp = datetime.now(timezone.utc).isoformat()

    if not positions or not prices:
        logger.warning(
            "[stress_test] Pas de positions (%d) ou pas de prix (%d), score trivial.",
            len(positions),
            len(prices),
        )
        overview = StressTestOverview(
            timestamp=timestamp,
            nb_positions=len(positions),
            total_capital=total_capital,
            base_unrealized_pnl=0.0,
            base_unrealized_pnl_pct=0.0,
            scenarios=[],
            worst_scenario=None,
            stress_score=100.0,
            risk_flag="ok",
            meta={
                "reason": "no_positions_or_prices",
                "nb_positions": len(positions),
                "nb_prices": len(prices),
            },
        )
        # Sauvegarde et retour
        _save_overview(overview)
        return overview

    base_pnl = _compute_base_unrealized_pnl(positions, prices)
    base_pnl_pct = (
        base_pnl / total_capital * 100.0 if total_capital > 0 else 0.0
    )

    # Scénarios
    scenario_results: List[ScenarioResult] = []
    for name, shock in STRESS_SCENARIOS:
        res = _apply_scenario(
            positions=positions,
            prices=prices,
            shock_pct=shock,
            total_capital=total_capital,
            name=name,
        )
        scenario_results.append(res)

    worst = (
        min(scenario_results, key=lambda s: s.pnl_pct)
        if scenario_results
        else None
    )

    stress_score = _compute_stress_score(scenario_results)
    risk_flag = _derive_risk_flag(stress_score)

    overview = StressTestOverview(
        timestamp=timestamp,
        nb_positions=len(positions),
        total_capital=total_capital,
        base_unrealized_pnl=base_pnl,
        base_unrealized_pnl_pct=base_pnl_pct,
        scenarios=scenario_results,
        worst_scenario=worst,
        stress_score=stress_score,
        risk_flag=risk_flag,
        meta={
            "nb_prices": len(prices),
            "scenario_names": [s.name for s in scenario_results],
        },
    )

    _save_overview(overview)
    return overview


def _save_overview(overview: StressTestOverview) -> None:
    """
    Sauvegarde le résultat dans stress_test_overview.json
    en le sérialisant proprement.
    """
    # conversion dataclasses -> dict
    payload: Dict[str, Any] = asdict(overview)
    # scenarios & worst_scenario sont déjà transformés par asdict
    save_json_file(STRESS_OUTPUT_FILE, payload)
    logger.info(
        "[stress_test_engine_light] Résultats sauvegardés dans %s (score=%.1f, risk_flag=%s).",
        STRESS_OUTPUT_FILE,
        overview.stress_score,
        overview.risk_flag,
    )


def main() -> None:
    run_stress_test()


if __name__ == "__main__":
    main()
