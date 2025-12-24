# src/v2/tools/trello_sync.py

from __future__ import annotations

import os
import sys
import logging
from typing import List, Dict, Any

import requests

# Logger simple (tu peux le brancher sur ton logger centralisé si tu veux)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_env(name: str, required: bool = True, default: str | None = None) -> str:
    """Récupère une variable d'environnement, avec gestion d'erreur lisible."""
    value = os.getenv(name, default)
    if required and not value:
        logger.error("Variable d'environnement manquante: %s", name)
        raise SystemExit(1)
    return value


TRELLO_KEY = get_env("TRELLO_KEY", required=True)
TRELLO_TOKEN = get_env("TRELLO_TOKEN", required=True)
TRELLO_LIST_ID = get_env("TRELLO_LIST_ID", required=True)


# ---------------------------------------------------------------------------
# Définition des cartes
# ---------------------------------------------------------------------------

SEASON2_CARDS: List[Dict[str, str]] = [
    {
        "name": "S2 – Momentum Engine 4.0",
        "desc": (
            "Implémenter Momentum Engine 4.0 avec scores institutionnels, "
            "vetos, pondérations avancées et intégration dans le meta-score "
            "et le risk engine."
        ),
    },
    {
        "name": "S2 – Volatility Engine Pro",
        "desc": (
            "Construire un Volatility Engine Pro (régimes de volatilité, "
            "volatility state machine, intégration au sizing et au kill-switch)."
        ),
    },
    {
        "name": "S2 – Liquidity Engine Pro",
        "desc": (
            "Suivi de la liquidité (orderbook proxy, profondeur, impact), "
            "scoring de liquidité et vetos en cas de conditions défavorables."
        ),
    },
    {
        "name": "S2 – Cycle Engine Pro",
        "desc": (
            "Détection des phases de cycle (accumulation, markup, distribution, "
            "markdown) et intégration dans le meta-score / risk engine."
        ),
    },
    {
        "name": "S2 – Story Engine Pro",
        "desc": (
            "Analyse avancée du narratif (hype, narratif en construction, "
            "fin de cycle narratif) avec impact sur les signaux et la taille."
        ),
    },
    {
        "name": "S2 – Sector Engine Pro",
        "desc": (
            "Sector Engine Pro : rotation sectorielle, force relative sectorielle, "
            "détection des poches chaudes/froides."
        ),
    },
    {
        "name": "S2 – Cross-Asset Engine Pro",
        "desc": (
            "Cross-Asset Engine Pro : intégration signaux macro, indices, taux, "
            "dollar, et impact sur le régime global crypto."
        ),
    },
    {
        "name": "S2 – Flow Engine Pro",
        "desc": (
            "Flow Engine Pro : flux on-chain, whales, CEX/DEX, produits dérivés, "
            "et scoring des flux pour les signaux."
        ),
    },
    {
        "name": "S2 – Meta-Score Engine Pro",
        "desc": (
            "Meta-Score Engine Pro : agrégation institutionnelle des moteurs "
            "(momentum, liquidité, cycle, story, flows, volatilité, etc.)."
        ),
    },
    {
        "name": "S2 – Weak Signals Engine Pro",
        "desc": (
            "Weak Signals Engine Pro : agrégation de signaux faibles, weak_watch, "
            "weak_avoid, et intégration au kill-switch / risk console."
        ),
    },
]

# Saison 2.5 – Engines / Risk (déjà vus dans la roadmap)
SEASON25_ENGINES_CARDS: List[Dict[str, str]] = [
    {
        "name": "S2.5 – Strategy Selector (Sniper / Whale / Momentum)",
        "desc": (
            "Mettre en place strategy_selector.py : backtest glissant 30j des "
            "stratégies (Sniper / Whale / Momentum), pondération dynamique et "
            "export strategy_weights.json."
        ),
    },
    {
        "name": "S2.5 – Orderflow Adapter",
        "desc": (
            "Développer orderflow_adapter.py : snapshots carnet d’ordres (top5), "
            "order-imbalance, détection simple de spoofing, blocage si spread "
            "trop large ou spoof probable."
        ),
    },
    {
        "name": "S2.5 – Sentiment Early Pump Score",
        "desc": (
            "Étendre sentiment_analyzer + scrapers pour calculer un early_pump_score "
            "(messages/min, qualité des sources) et l’utiliser dans les conditions "
            "d’entrée Momentum."
        ),
    },
    {
        "name": "S2.5 – Risk Controller (Market Regime / Risk ON-OFF)",
        "desc": (
            "Intégrer le Market Regime (risk_on/off) dans risk_controller.py : "
            "réduction de taille, trailing renforcé et pause trading en cas de "
            "drawdown ou régime défavorable."
        ),
    },
]

# Saison 2.5 – Améliorations produit (interface / features V2.5)
SEASON25_PRODUCT_CARDS: List[Dict[str, str]] = [
    {
        "name": "V2.5 Produit – Interface Freemium / Premium + Telegram",
        "desc": (
            "Déployer une interface simplifiée (React + API) permettant : création "
            "de compte, ajout d’identifiant Telegram, choix des alertes (KOLs, whales, "
            "pump, etc.), réception des signaux et page Upgrade vers plan Premium "
            "(Stripe)."
        ),
    },
    {
        "name": "V2.5 Produit – Signal Dispatcher Telegram",
        "desc": (
            "Implémenter signal_dispatcher.py pour router les signaux vers les bons "
            "utilisateurs (Freemium / Premium) selon leurs préférences et l’état du "
            "governor / kill-switch."
        ),
    },
    {
        "name": "V2.5 Produit – Cost Tracker et Profitability",
        "desc": (
            "Finaliser cost_tracker.py + CostTracker.jsx et Profitability.jsx pour "
            "le suivi mensuel des coûts (APIs, serveurs, stockage) et la rentabilité "
            "mensuelle/annuelle (monthly_pnl.json, monthly_costs.json)."
        ),
    },
    {
        "name": "V2.5 Produit – Interface NSC V2.5 (polish UI/UX)",
        "desc": (
            "Moderniser l’interface : dark mode amélioré, navigation fluide, "
            "multi-pages (Dashboard, Settings, Signals, Profitability, Worst Trades), "
            "préparation multi-stratégie et multi-utilisateur."
        ),
    },
]

# Saison 3 – Engines institutionnels (résumé des épisodes S3 déjà vus)
SEASON3_CARDS: List[Dict[str, str]] = [
    {
        "name": "S3 – Orchestrator Pro & Message Bus",
        "desc": (
            "Mettre en place un Orchestrator Pro avec message bus / architecture "
            "event-driven pour orchestrer les engines (risk, portfolio, execution, "
            "governance, daily loop)."
        ),
    },
    {
        "name": "S3 – Risk Engine Pro (Version finale S3)",
        "desc": (
            "Étendre le Risk Engine Pro avec intégration complète des nouveaux "
            "régimes (volatilité, market pressure, stability, coherence, etc.) et "
            "logique de vetos institutionnels."
        ),
    },
    {
        "name": "S3 – Execution Engine Pro (Version institutionnelle)",
        "desc": (
            "Renforcer l’Execution Engine Pro avec gestion de la latence, "
            "backpressure, contrôle qualité des signaux et intégration étroite "
            "avec le Governor et le Kill Switch global."
        ),
    },
    {
        "name": "S3 – Portfolio Engine Pro (Multi-poches)",
        "desc": (
            "Étendre Portfolio Engine Pro à plusieurs poches (Scalp / Swing / Long "
            "Term) avec budgets séparés, contraintes institutionnelles et suivi "
            "agrégé."
        ),
    },
    {
        "name": "S3 – Backpressure Engine",
        "desc": (
            "Mettre en place un Backpressure Engine pour détecter la saturation "
            "du système (latence, files d’attente, volume de signaux) et adapter "
            "le rythme d’exécution."
        ),
    },
    {
        "name": "S3 – Governance Engine Pro",
        "desc": (
            "Finaliser Governance Engine Pro : agrégation des signaux de risk, "
            "weak signals, discipline, kill-switch et exécution en un score de "
            "gouvernance et un flag global (soft/hard block)."
        ),
    },
    {
        "name": "S3 – Daily Loop Engine",
        "desc": (
            "Formaliser un Daily Loop Engine institutionnel : ordre de lancement "
            "des engines, checks pré/post, métriques et journaux quotidiens."
        ),
    },
    {
        "name": "S3 – System Metrics & Telemetry Pro",
        "desc": (
            "Mettre en place un module de métriques système et de télémétrie "
            "avancée (temps de réponse, erreurs, saturation, santé des services)."
        ),
    },
    {
        "name": "S3 – Architecture Multi-Services & Auto-Recovery",
        "desc": (
            "Préparer une architecture multi-services avec scénarios d’auto-recovery, "
            "restart ciblé des briques, et isolation des pannes."
        ),
    },
    {
        "name": "S3 – Stress Test Engine (50 scenarios extremes)",
        "desc": (
            "Consolider un Stress Test Engine avec environ 50 scénarios extrêmes "
            "(flash crash, illiquidité, explosion des spreads, corrélation forte, "
            "choc macro) exécutables sur demande ou de façon planifiée."
        ),
    },
    {
        "name": "S3 – Production Protocol & Real Production Protocol",
        "desc": (
            "Formaliser un Production Protocol complet : pre-flight checks, "
            "runtime monitoring, post-flight review, canary deployment, "
            "drift monitoring, sécurité long terme et gouvernance "
            "institutionnelle. Définir également un Real Production Protocol "
            "avec règles pratiques de mise en production quotidienne."
        ),
    },
]


# ---------------------------------------------------------------------------
# Fonctions Trello
# ---------------------------------------------------------------------------

def create_card(name: str, desc: str) -> str | None:
    """Crée une carte Trello dans la liste TRELLO_LIST_ID."""
    url = "https://api.trello.com/1/cards"
    params = {
        "key": TRELLO_KEY,
        "token": TRELLO_TOKEN,
        "idList": TRELLO_LIST_ID,
        "name": name,
        "desc": desc,
        "pos": "bottom",
    }

    logger.info("Création de la carte Trello: %s", name)

    try:
        resp = requests.post(url, params=params, timeout=20)
    except Exception as e:
        logger.error("Erreur réseau lors de l'appel Trello pour '%s': %s", name, e)
        return None

    # Gestion explicite des erreurs Trello
    if resp.status_code >= 400:
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text

        logger.error(
            "Erreur Trello (%s) pour la carte '%s' – réponse: %s",
            resp.status_code,
            name,
            body,
        )
        return None

    try:
        data = resp.json()
    except Exception as e:
        logger.error("Réponse Trello non-JSON pour '%s': %s", name, e)
        return None

    card_id = data.get("id")
    short_url = data.get("shortUrl")
    logger.info("Carte créée: %s (%s)", name, short_url or card_id)
    return card_id


def push_cards(cards: List[Dict[str, str]], label: str) -> None:
    """Envoie une liste de cartes, en loggant les succès/échecs."""
    logger.info("=== Création des cartes Trello pour %s (%d cartes) ===", label, len(cards))
    success = 0
    fail = 0

    for card in cards:
        name = card["name"]
        desc = card.get("desc", "")
        card_id = create_card(name, desc)
        if card_id:
            success += 1
        else:
            fail += 1

    logger.info(
        "Résultat %s : %d cartes créées, %d échecs.",
        label,
        success,
        fail,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print(
            "Usage: python -m src.v2.tools.trello_sync "
            "[season2|season25-engines|season25-product|season25-all|season3|all]"
        )
        raise SystemExit(1)

    mode = argv[0].strip().lower()

    if mode == "season2":
        push_cards(SEASON2_CARDS, "Season 2")
    elif mode == "season25-engines":
        push_cards(SEASON25_ENGINES_CARDS, "Season 2.5 – Engines")
    elif mode == "season25-product":
        push_cards(SEASON25_PRODUCT_CARDS, "Season 2.5 – Produit")
    elif mode == "season25-all":
        push_cards(SEASON25_ENGINES_CARDS, "Season 2.5 – Engines")
        push_cards(SEASON25_PRODUCT_CARDS, "Season 2.5 – Produit")
    elif mode == "season3":
        push_cards(SEASON3_CARDS, "Season 3")
    elif mode == "all":
        push_cards(SEASON2_CARDS, "Season 2")
        push_cards(SEASON25_ENGINES_CARDS, "Season 2.5 – Engines")
        push_cards(SEASON25_PRODUCT_CARDS, "Season 2.5 – Produit")
        push_cards(SEASON3_CARDS, "Season 3")
    else:
        print(
            "Mode inconnu. Utilise: season2 | season25-engines | "
            "season25-product | season25-all | season3 | all"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
