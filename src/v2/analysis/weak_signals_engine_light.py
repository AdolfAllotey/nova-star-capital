# src/v2/analysis/weak_signals_engine_light.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
ANALYSIS_DIR = DATA_DIR / "analysis"


@dataclass
class WeakSignalRow:
    symbol: str
    momentum_score: Optional[float] = None
    hype_score: Optional[float] = None
    liquidity_risk_score: Optional[float] = None
    liquidity_flag: Optional[str] = None
    meta_score: Optional[float] = None
    weak_flag: str = "ok"
    reason: str = ""


def _load_json_assets(relative_path: str) -> List[Dict[str, Any]]:
    """
    Charge un fichier JSON dans data/analysis et renvoie une liste d'assets.
    Supporte les formats :
      - {"assets": [...]}
      - [...]
    """
    path = ANALYSIS_DIR / relative_path
    data = load_json_file(path, default=[])

    if isinstance(data, dict):
        assets = data.get("assets", [])
        if isinstance(assets, list):
            return assets
        return []
    elif isinstance(data, list):
        return data
    else:
        return []


def _index_by_symbol(
    assets: List[Dict[str, Any]], symbol_keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Indexe une liste d'assets par symbole, en utilisant plusieurs clés possibles :
    ex: ["symbol", "symbol_raw"].
    """
    if symbol_keys is None:
        symbol_keys = ["symbol", "symbol_raw"]

    index: Dict[str, Any] = {}
    for row in assets:
        if not isinstance(row, dict):
            continue
        sym = None
        for key in symbol_keys:
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                sym = val.strip().lower()
                break
        if sym:
            index.setdefault(sym, row)
    return index


def _normalize_liquidity_row(symbol: str, value: Any) -> Dict[str, Any]:
    """
    Normalise une ligne de liquidité potentiellement sous forme de liste ou dict.

    - dict → retourné tel quel
    - list → on tente de trouver un dict dont le symbol correspond, sinon premier dict
    - autre → {}
    """
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        chosen = None
        for elt in value:
            if not isinstance(elt, dict):
                continue
            sym = (elt.get("symbol") or "").strip().lower()
            if sym == symbol:
                chosen = elt
                break
            if chosen is None:
                chosen = elt
        return chosen or {}

    return {}


def _load_momentum_index() -> Dict[str, Any]:
    assets = _load_json_assets("momentum_scores.json")
    idx = _index_by_symbol(assets, ["symbol", "symbol_raw"])
    logger.info(
        "[weak_signals_engine_light] Momentum chargé: %d assets indexés.", len(idx)
    )
    return idx


def _load_hype_index() -> Dict[str, Any]:
    assets = _load_json_assets("hype_cycle_overview.json")
    idx = _index_by_symbol(assets, ["symbol"])
    logger.info(
        "[weak_signals_engine_light] Hype cycle chargé: %d assets indexés.", len(idx)
    )
    return idx


def _load_liquidity_index() -> Dict[str, Any]:
    assets = _load_json_assets("liquidity_risk_overview.json")
    # Ici, on accepte que _index_by_symbol puisse donner une list ou un dict,
    # compute_weak_signals normalisera avec _normalize_liquidity_row.
    idx: Dict[str, Any] = {}
    for row in assets:
        if not isinstance(row, dict):
            continue
        sym = (row.get("symbol") or "").strip().lower()
        if not sym:
            continue
        # si plusieurs lignes pour le même symbol, on les accumule en liste
        if sym not in idx:
            idx[sym] = row
        else:
            existing = idx[sym]
            if isinstance(existing, list):
                existing.append(row)
            else:
                idx[sym] = [existing, row]
    logger.info(
        "[weak_signals_engine_light] Liquidité chargée: %d assets indexés.", len(idx)
    )
    return idx


def _load_meta_index() -> Dict[str, Any]:
    """
    Optionnel : meta-score par asset depuis signal_votes.json (ou autre).
    On reste très robuste sur la structure.
    """
    path = ANALYSIS_DIR / "signal_votes.json"
    data = load_json_file(path, default={})

    assets: List[Dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("assets"), list):
        assets = data["assets"]
    elif isinstance(data, list):
        assets = data

    idx = _index_by_symbol(assets, ["symbol"])
    logger.info(
        "[weak_signals_engine_light] Meta-score chargé: %d assets indexés.", len(idx)
    )
    return idx


def _score_weak_signal(row: WeakSignalRow) -> WeakSignalRow:
    """
    Très simple moteur de scoring pour signaux faibles.

    Idée :
      - liquidité faible → gros warning
      - hype très élevée avec momentum moyen/faible → risque de blow-off
      - meta_score très bas → méfiance
    """
    score = 0
    reasons = []

    # Liquidité
    if row.liquidity_risk_score is not None:
        if row.liquidity_risk_score < 40:
            score += 3
            reasons.append("liquidity_risk_score<40")
        elif row.liquidity_risk_score < 60:
            score += 1
            reasons.append("liquidity_risk_score<60")
    if row.liquidity_flag in ("watch", "risk"):
        score += 1
        reasons.append(f"liquidity_flag={row.liquidity_flag}")

    # Hype vs momentum
    if row.hype_score is not None and row.momentum_score is not None:
        if row.hype_score >= 75 and row.momentum_score < 55:
            score += 2
            reasons.append("hype>>momentum")
        elif row.hype_score >= 65 and row.momentum_score < 50:
            score += 1
            reasons.append("hype>momentum")

    # Meta-score bas
    if row.meta_score is not None and row.meta_score < 45:
        score += 2
        reasons.append("meta_score<45")

    # Décision
    if score >= 4:
        row.weak_flag = "avoid"
    elif score >= 2:
        row.weak_flag = "watch"
    else:
        row.weak_flag = "ok"

    row.reason = ", ".join(reasons) if reasons else "rien de particulier"
    return row


def compute_weak_signals() -> Dict[str, Any]:
    momentum_idx = _load_momentum_index()
    hype_idx = _load_hype_index()
    liquidity_idx = _load_liquidity_index()
    meta_idx = _load_meta_index()

    all_symbols = sorted(
        set(momentum_idx.keys()) | set(hype_idx.keys()) | set(liquidity_idx.keys())
    )

    items: List[Dict[str, Any]] = []
    nb_watch = 0
    nb_avoid = 0

    for sym in all_symbols:
        m_row = momentum_idx.get(sym) or {}
        h_row = hype_idx.get(sym) or {}
        l_raw = liquidity_idx.get(sym)
        l_row = _normalize_liquidity_row(sym, l_raw)
        meta_row = meta_idx.get(sym) or {}

        ws = WeakSignalRow(symbol=sym)

        # momentum
        if isinstance(m_row, dict):
            ws.momentum_score = m_row.get("momentum_score")

        # hype
        if isinstance(h_row, dict):
            ws.hype_score = (
                h_row.get("hype_score")
                or h_row.get("hype_cycle_score")
                or h_row.get("hype")
            )

        # liquidité
        if isinstance(l_row, dict):
            ws.liquidity_risk_score = l_row.get("liquidity_risk_score")
            ws.liquidity_flag = l_row.get("liquidity_flag")

        # meta-score global de l’asset (optionnel)
        if isinstance(meta_row, dict):
            ws.meta_score = (
                meta_row.get("meta_score_nsc")
                or meta_row.get("meta_score")
                or meta_row.get("score")
            )

        ws = _score_weak_signal(ws)

        if ws.weak_flag == "watch":
            nb_watch += 1
        elif ws.weak_flag == "avoid":
            nb_avoid += 1

        items.append(
            {
                "symbol": ws.symbol,
                "momentum_score": ws.momentum_score,
                "hype_score": ws.hype_score,
                "liquidity_risk_score": ws.liquidity_risk_score,
                "liquidity_flag": ws.liquidity_flag,
                "meta_score": ws.meta_score,
                "weak_flag": ws.weak_flag,
                "reason": ws.reason,
            }
        )

    # flag global pour discipline / risk_console
    if nb_avoid > 0:
        flag = "risk"
    elif nb_watch > 0:
        flag = "watch"
    else:
        flag = "ok"

    overview: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nb_assets": len(items),
        "nb_weak_watch": nb_watch,
        "nb_weak_avoid": nb_avoid,
        "flag": flag,
        "reason": f"weak_watch={nb_watch}, weak_avoid={nb_avoid}",
        "items": items,
    }

    return overview


def main() -> None:
    logger.info(
        "[weak_signals_engine_light] ROOT_DIR=%s, DATA_DIR=%s",
        str(ROOT_DIR),
        str(DATA_DIR),
    )
    overview = compute_weak_signals()
    out_path = ANALYSIS_DIR / "weak_signals_overview.json"
    save_json_file(out_path, overview)
    logger.info(
        "[weak_signals_engine_light] weak_signals_overview.json sauvegardé (%s, nb_assets=%d, nb_weak_watch=%d, nb_weak_avoid=%d)",
        str(out_path),
        overview.get("nb_assets", 0),
        overview.get("nb_weak_watch", 0),
        overview.get("nb_weak_avoid", 0),
    )


if __name__ == "__main__":
    main()
