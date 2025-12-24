"""
trello_sync_v2.py

Script one-shot pour créer les 34 cartes Season 3 dans une liste Trello.

Utilise les variables d'environnement :
- TRELLO_KEY
- TRELLO_TOKEN
- TRELLO_LIST_ID   (ID de la *liste* cible, pas du board)

Usage :
    cd /opt/nsc/app
    export TRELLO_KEY="..."
    export TRELLO_TOKEN="..."
    export TRELLO_LIST_ID="..."
    python -m src.v2.tools.trello_sync_v2
"""

import os
import logging
from typing import List, Dict, Tuple

import requests


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# Config & constantes
# ---------------------------------------------------------------------------

TRELLO_API_BASE = "https://api.trello.com/1"


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variable d'environnement manquante : {name}")
    return value


# ---------------------------------------------------------------------------
# Définition des 34 cartes Season 3
# ---------------------------------------------------------------------------

def get_season3_cards() -> List[Dict[str, str]]:
    """
    Retourne la liste complète des 34 cartes Season 3 (nom + description).
    """
    cards: List[Dict[str, str]] = []

    # 🟦 Bloc 1 – Orchestration & Architecture (6 cartes)
    cards.append({
        "name": "S3 – Message Bus Pro",
        "desc": (
            "Mettre en place un Message Bus Pro (event-driven) pour NSC : "
            "distribution des événements (signals, fills, risques, logs) entre services, "
            "gestion des topics, formats de messages, retries et observabilité."
        ),
    })
    cards.append({
        "name": "S3 – Orchestrator Pro",
        "desc": (
            "Construire l’Orchestrator Pro responsable de la coordination des engines NSC : "
            "ordonnancement des étapes, dépendances, timeouts, retries, et gestion centralisée "
            "des échecs (grâce/killswitch)."
        ),
    })
    cards.append({
        "name": "S3 – Daily Loop Engine Pro (v3)",
        "desc": (
            "Refactor du Daily Trading Loop en version Pro : découplé, paramétrable par scénario "
            "(backtest, sim, prod), piloté via Orchestrator/Message Bus, avec logs et métriques "
            "consistent sur tout le cycle journalier."
        ),
    })
    cards.append({
        "name": "S3 – System Metrics & Telemetry Pro",
        "desc": (
            "Mettre en place un module System Metrics & Telemetry Pro : agrégation des KPIs système "
            "(latence, erreurs, temps d’exécution, volumétrie, drawdown technique), export vers Prometheus "
            "ou équivalent, dashboards d’observabilité."
        ),
    })
    cards.append({
        "name": "S3 – Architecture Multi-Services & Auto-Recovery",
        "desc": (
            "Formaliser l’architecture multi-services NSC (API, workers, engines) avec stratégies "
            "d’auto-recovery : redémarrages ciblés, isolation des pannes, healthchecks, et "
            "détection d’états dégradés (degraded/safe/emergency mode)."
        ),
    })
    cards.append({
        "name": "S3 – Backpressure Engine",
        "desc": (
            "Créer un Backpressure Engine pour ralentir ou bloquer certaines parties du système "
            "lorsque la charge devient trop élevée : contrôle du flux de signaux, limitation du nombre "
            "de positions ou d’appels API, modes de throttling adaptatifs."
        ),
    })

    # 🟧 Bloc 2 – Microstructure & Flow (9 cartes)
    cards.append({
        "name": "S3 – Microstructure Ultra Engine",
        "desc": (
            "Développer le Microstructure Ultra Engine : analyse fine du carnet d’ordres, "
            "des spreads, de la liquidité locale, des spoofings potentiels, et des conditions "
            "microstructurelles par actif (régimes micro)."
        ),
    })
    cards.append({
        "name": "S3 – Footprint Engine Pro",
        "desc": (
            "Implémenter un Footprint Engine Pro : intégration de données de volume par prix, "
            "imbalance bid/ask, footprint simplifié pour crypto, et signaux de pression d’achat/vente."
        ),
    })
    cards.append({
        "name": "S3 – Composite Cycle Engine",
        "desc": (
            "Construire un Composite Cycle Engine : combiner plusieurs horizons de cycle "
            "(court, moyen, long terme) pour évaluer le contexte cyclique d’un actif ou du marché."
        ),
    })
    cards.append({
        "name": "S3 – Cross-Asset Liquidity Engine",
        "desc": (
            "Créer un Cross-Asset Liquidity Engine : suivre la liquidité globale entre différentes "
            "classes d’actifs (crypto majeures, stablecoins, indices…) et en déduire des régimes "
            "de liquidité (ample, normale, stress)."
        ),
    })
    cards.append({
        "name": "S3 – Flow of Funds Engine",
        "desc": (
            "Mettre en place un Flow of Funds Engine : détecter les flux de capitaux (entrées/sorties) "
            "entre assets, secteurs ou thèmes, et associer un score de flux aux signaux de trading."
        ),
    })
    cards.append({
        "name": "S3 – Correlation Regime Engine",
        "desc": (
            "Développer un Correlation Regime Engine : identification des régimes de corrélation "
            "(faible, normale, forte) entre actifs/indices, impacts sur la diversification effective "
            "et taille des positions."
        ),
    })
    cards.append({
        "name": "S3 – Dispersion Engine",
        "desc": (
            "Créer un Dispersion Engine : mesurer la dispersion des performances au sein d’un univers "
            "d’actifs (top/bottom, sectors) et utiliser cette information pour filtrer ou booster "
            "certaines stratégies (momentum, mean-reversion)."
        ),
    })
    cards.append({
        "name": "S3 – Multi-Asset Friction Engine",
        "desc": (
            "Implémenter un Multi-Asset Friction Engine : modéliser les frictions (frais, slippage, "
            "latence, contraintes d’exchanges) par type d’actif, et les intégrer dans le meta-score "
            "et le sizing."
        ),
    })
    cards.append({
        "name": "S3 – Liquidity Migration Engine",
        "desc": (
            "Construire un Liquidity Migration Engine : suivre les migrations de liquidité "
            "(d’un token à l’autre, d’un secteur à l’autre ou d’un exchange à l’autre) et "
            "adapter les signaux/allocations en conséquence."
        ),
    })

    # 🟩 Bloc 3 – Structure du marché & Régimes (11 cartes)
    cards.append({
        "name": "S3 – Volatility State Machine",
        "desc": (
            "Mettre en place une Volatility State Machine : classification des régimes de volatilité "
            "(low/normal/high/extreme), transitions de régime, et impact direct sur tailles de position, "
            "stops et filtrage des signaux."
        ),
    })
    cards.append({
        "name": "S3 – Market Memory Engine",
        "desc": (
            "Développer un Market Memory Engine : prise en compte de l’historique récent "
            "(drawdowns, séries de gains/pertes, chocs de marché) pour ajuster le risque et "
            "les signaux (mémoire de marché)."
        ),
    })
    cards.append({
        "name": "S3 – Structural Break Engine",
        "desc": (
            "Créer un Structural Break Engine : détecter les ruptures structurelles "
            "(changements de régime brutaux, cassures de corrélations, chocs macro) et "
            "appliquer des vetos / reconfigurations temporaires du système."
        ),
    })
    cards.append({
        "name": "S3 – Fractal Energy Engine",
        "desc": (
            "Implémenter un Fractal Energy Engine : mesurer la 'tension' ou énergie fractale des "
            "mouvements de prix (consolidation vs expansion) pour moduler l’agressivité du "
            "momentum / breakout."
        ),
    })
    cards.append({
        "name": "S3 – Regime Transition Engine",
        "desc": (
            "Construire un Regime Transition Engine : identifier les phases de transition entre "
            "régimes (bull→bear, low vol→high vol, etc.) et ajuster progressivement les tailles, "
            "les signaux et les vetos."
        ),
    })
    cards.append({
        "name": "S3 – Information Imbalance Engine",
        "desc": (
            "Mettre en place un Information Imbalance Engine : croiser prix, volumes, sentiment, "
            "news et flux pour détecter les situations d’information déséquilibrée (marché mal pricé, "
            "asymétrie d’info)."
        ),
    })
    cards.append({
        "name": "S3 – Market Pressure Engine",
        "desc": (
            "Développer un Market Pressure Engine : score global de pression acheteuse/vendeuse "
            "basé sur orderflow, footprint, sentiment et flux de capitaux."
        ),
    })
    cards.append({
        "name": "S3 – Market Strength Engine",
        "desc": (
            "Créer un Market Strength Engine : mesurer la force globale du marché (breadth, % d’actifs "
            "au-dessus de leurs moyennes, nouveaux plus hauts/bas) et l’intégrer au meta-score."
        ),
    })
    cards.append({
        "name": "S3 – Market Stability Engine",
        "desc": (
            "Implémenter un Market Stability Engine : indicateur de stabilité/fragilité du marché "
            "(flash crashes récents, gaps, anomalies de spread/liquidité) influençant le risk engine."
        ),
    })
    cards.append({
        "name": "S3 – Market Coherence Engine",
        "desc": (
            "Développer un Market Coherence Engine : mesure de cohérence entre signaux "
            "(technique, macro, sentiment, flow) ; si incohérence élevée → réduction du risque "
            "ou blocage de certaines stratégies."
        ),
    })
    cards.append({
        "name": "S3 – Signal Quality Engine",
        "desc": (
            "Mettre en place un Signal Quality Engine : notation de la qualité de chaque signal "
            "(data quality, bruit, cohérence multi-engines, contexte de marché), intégré dans "
            "le Meta-Score Pro V3."
        ),
    })

    # 🟥 Bloc 4 – Gouvernance & Production (8 cartes)
    cards.append({
        "name": "S3 – Market Conditions Engine",
        "desc": (
            "Créer un Market Conditions Engine : synthèse de l’état global du marché "
            "(regime, volatilité, liquidité, sentiment, dispersion) en un score unique, "
            "utilisé par le Risk Engine et l’Execution Engine."
        ),
    })
    cards.append({
        "name": "S3 – Governance Engine Pro (V3)",
        "desc": (
            "Étendre le Governance Engine Pro pour la V3 : règles institutionnelles, "
            "soft/hard vetos globaux, intégration des journaux de discipline et de l’"
            "emotional regime, pilotage des modes Normal/Degraded/Safe/Emergency."
        ),
    })
    cards.append({
        "name": "S3 – Daily Loop Engine – Institutional Runtime",
        "desc": (
            "Finaliser le Daily Loop Engine en runtime institutionnel : gestion des fenêtres "
            "de trading, validations pré/post-trade, contraintes de gouvernance, et compatibilité "
            "avec le Production Protocol."
        ),
    })
    cards.append({
        "name": "S3 – System Metrics & Telemetry Pro – Extended",
        "desc": (
            "Étendre System Metrics & Telemetry Pro avec des métriques institutionnelles : "
            "SLA, SLO internes, budgets d’erreurs, temps de récupération, et intégration "
            "dans des dashboards de production."
        ),
    })
    cards.append({
        "name": "S3 – Auto-Recovery Scenarios & Playbooks",
        "desc": (
            "Définir et implémenter les scénarios d’auto-recovery et playbooks : "
            "que faire en cas de crash de service, latence excessive, dérive de modèles, "
            "ou erreurs récurrentes (runbooks codés)."
        ),
    })
    cards.append({
        "name": "S3 – Stress Test Engine (50 scénarios extrêmes)",
        "desc": (
            "Consolider un Stress Test Engine avec ~50 scénarios extrêmes (flash crash, "
            "illiquidité, explosion de spreads, corrélation→1, choc macro) exécutables "
            "sur demande ou planifiés."
        ),
    })
    cards.append({
        "name": "S3 – Production Protocol",
        "desc": (
            "Formaliser un Production Protocol complet : pre-flight checks, run-time monitoring, "
            "post-flight review, checklists pour chaque déploiement ou changement majeur de "
            "configuration NSC."
        ),
    })
    cards.append({
        "name": "S3 – Real Production Protocol",
        "desc": (
            "Étendre le Production Protocol en Real Production Protocol : canary deployment, "
            "drift monitoring, mécanismes de rollback, gouvernance long terme, et intégration "
            "avec le pont assistant/Trello/GitHub."
        ),
    })

    return cards


# ---------------------------------------------------------------------------
# Fonctions Trello
# ---------------------------------------------------------------------------

def get_existing_cards(
    key: str, token: str, list_id: str
) -> Dict[str, str]:
    """
    Retourne un dict {nom_carte: id_carte} pour toutes les cartes de la liste.
    """
    url = f"{TRELLO_API_BASE}/lists/{list_id}/cards"
    params = {"key": key, "token": token, "fields": "name"}
    logger.info("Récupération des cartes existantes pour la liste %s", list_id)

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    cards = resp.json()
    existing = {card["name"]: card["id"] for card in cards}
    logger.info("Cartes existantes trouvées: %d", len(existing))
    return existing


def create_card(
    key: str, token: str, list_id: str, name: str, desc: str
) -> Tuple[bool, str]:
    """
    Crée une carte Trello dans la liste, renvoie (success, message).
    """
    url = f"{TRELLO_API_BASE}/cards"
    params = {
        "key": key,
        "token": token,
        "idList": list_id,
        "name": name,
        "desc": desc,
        "pos": "bottom",
    }

    logger.info("Création de la carte Trello: %s", name)

    resp = requests.post(url, params=params, timeout=10)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        msg = f"Erreur Trello ({resp.status_code}) pour la carte '{name}' – réponse: {data}"
        logger.error(msg)
        return False, msg

    card = resp.json()
    logger.info("Carte créée: %s (id=%s)", card.get("name"), card.get("id"))
    return True, f"OK: {card.get('id')}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    key = _get_env("TRELLO_KEY")
    token = _get_env("TRELLO_TOKEN")
    list_id = _get_env("TRELLO_LIST_ID")

    season3_cards = get_season3_cards()
    logger.info("=== Création des cartes Trello pour Season 3 (total=%d) ===", len(season3_cards))

    try:
        existing = get_existing_cards(key, token, list_id)
    except Exception as e:
        logger.error("Impossible de récupérer les cartes existantes : %s", e)
        raise

    created = 0
    skipped = 0
    errors = 0

    for card in season3_cards:
        name = card["name"]
        desc = card["desc"]

        if name in existing:
            logger.info("Carte déjà existante, skip: %s (id=%s)", name, existing[name])
            skipped += 1
            continue

        success, _ = create_card(key, token, list_id, name, desc)
        if success:
            created += 1
        else:
            errors += 1

    logger.info(
        "=== Résultat Season 3 : %d créées, %d déjà présentes, %d erreurs ===",
        created,
        skipped,
        errors,
    )


if __name__ == "__main__":
    main()
