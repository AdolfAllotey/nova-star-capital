from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)

DATA_DIR = Path(get_data_dir()).resolve()
ROOT_DIR = DATA_DIR.parent


def _now_iso() -> str:
    """Retourne un timestamp ISO8601 en UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def _load_env() -> Dict[str, Any]:
    return {
        "env": os.getenv("NSC_ENV", "PREPROD"),
        "instance": os.getenv("NSC_INSTANCE", "nsc-crypto"),
    }


def _ticker_from_symbol(symbol: str) -> str:
    """Map très simple symbol -> ticker affiché."""
    mapping = {
        "bitcoin": "BTC",
        "btc": "BTC",
        "ethereum": "ETH",
        "eth": "ETH",
        "solana": "SOL",
        "sol": "SOL",
    }
    return mapping.get(symbol.lower(), symbol.upper())


def _priority_from_meta(meta: Optional[float], risk_flag: str) -> str:
    """Détermine la priorité d’alerte pour Telegram."""
    if meta is None:
        return "low"

    # base sur le meta-score
    if meta >= 80:
        pri = "high"
    elif meta >= 60:
        pri = "medium"
    else:
        pri = "low"

    # si le régime de risque est déjà en caution/danger, on évite de monter trop
    if risk_flag in ("caution", "danger") and pri == "high":
        return "medium"
    return pri


def _channel_from_priority(priority: str) -> str:
    """
    Détermine la "cible" de routing logique.
    - high/medium → premium
    - low → freemium
    (plutôt symbolique pour l’instant, on branchera ça sur les users ensuite)
    """
    if priority in ("high", "medium"):
        return "premium"
    return "freemium"


def build_signal_text(
    symbol: str,
    side: str,
    strategy: str,
    final_weight: float,
    meta_score: Optional[float],
    risk_flag: str,
    weak_kind: Optional[str],
    notes: Optional[List[str]] = None,
) -> str:
    """
    Construit le texte lisible pour Telegram (FR, compact, NSC-style).
    """
    ticker = _ticker_from_symbol(symbol)
    direction = "ACHAT" if side.lower() == "buy" else "VENTE"
    weight_pct = round(final_weight * 100, 2)

    meta_str = f"{meta_score:.1f}" if meta_score is not None else "N/A"
    risk_str = risk_flag or "n/a"
    weak_str = weak_kind or "none"

    lines = [
        f"🔔 NSC • Signal {strategy.capitalize()}",
        f"• {ticker} • {direction}",
        f"• Taille cible: {weight_pct:.2f}% du capital trading",
        f"• Meta-score: {meta_str} • Risk: {risk_str} • Weak: {weak_str}",
    ]

    if notes:
        # on garde seulement 1–2 notes pour ne pas surcharger
        short_notes = notes[:2]
        lines.append("")
        lines.append("📝 Notes: " + " / ".join(short_notes))

    return "\n".join(lines)


def load_kill_switch(data_dir: Path) -> Dict[str, Any]:
    path = data_dir / "trading" / "kill_switch.json"
    return load_json_file(path, default={})


def load_governance(data_dir: Path) -> Dict[str, Any]:
    path = data_dir / "analysis" / "governance_engine_pro.json"
    return load_json_file(path, default={})


def load_sized_signals(data_dir: Path) -> List[Dict[str, Any]]:
    path = data_dir / "trading" / "sized_signals.json"
    data = load_json_file(path, default=[])
    if isinstance(data, list):
        return data
    logger.warning("[signal_dispatcher_telegram] sized_signals.json n'est pas une liste.")
    return []


def compute_block_state(
    kill_switch: Dict[str, Any], governance: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Détermine si on doit bloquer totalement l’envoi (hard/soft block global).
    """
    ks_existing = _safe_get(kill_switch, ["enriched", "existing"], default={})
    ks_mode = ks_existing.get("mode")
    ks_soft = bool(ks_existing.get("soft_block", False))
    ks_hard = bool(ks_existing.get("hard_block", False))

    gov_flag = governance.get("flag")
    risk_console_flag = governance.get("risk_console_flag")

    reasons: List[str] = []

    if ks_hard:
        reasons.append("Kill-switch HARD BLOCK actif.")
    elif ks_soft:
        reasons.append("Kill-switch SOFT BLOCK actif.")

    if gov_flag in ("hard_block", "soft_block"):
        reasons.append(f"Governance flag={gov_flag}.")

    if risk_console_flag and risk_console_flag != "ok":
        reasons.append(f"Risk console flag={risk_console_flag}.")

    blocked = ks_hard or ks_soft or gov_flag in ("hard_block", "soft_block")

    return {
        "blocked": blocked,
        "ks_mode": ks_mode,
        "ks_soft": ks_soft,
        "ks_hard": ks_hard,
        "gov_flag": gov_flag,
        "risk_console_flag": risk_console_flag,
        "reasons": reasons,
    }


def build_dispatch_queue(
    data_dir: Path,
) -> Dict[str, Any]:
    """
    Construit la queue d’envoi Telegram à partir des sized_signals + état de gouvernance.
    """
    env_info = _load_env()
    sized_signals = load_sized_signals(data_dir)
    kill_switch = load_kill_switch(data_dir)
    governance = load_governance(data_dir)

    block_state = compute_block_state(kill_switch, governance)

    # Si aucun signal → queue vide, mais utile pour la monitoring
    if not sized_signals:
        logger.info(
            "[signal_dispatcher_telegram] Aucun sized_signal trouvé, queue Telegram vide."
        )
        return {
            "generated_at": _now_iso(),
            "env": env_info.get("env"),
            "instance": env_info.get("instance"),
            "blocked": block_state["blocked"],
            "block_reasons": block_state["reasons"],
            "nb_signals_total": 0,
            "nb_signals_dispatchable": 0,
            "signals": [],
        }

    dispatchable: List[Dict[str, Any]] = []

    for sig in sized_signals:
        try:
            symbol = sig.get("symbol")
            side = sig.get("side", "buy")
            strategy = sig.get("strategy", "momentum")
            final_weight = float(sig.get("final_weight", 0.0))

            if not symbol:
                continue

            # Garde-fous : on n’envoie que des signaux avec taille > 0
            if final_weight <= 0:
                continue

            meta_score = sig.get("meta_score_pro")
            risk_flag = sig.get("risk_flag", "ok")
            weak_kind = sig.get("weak_kind")
            notes = sig.get("notes") or []

            priority = _priority_from_meta(meta_score, risk_flag)
            channel = _channel_from_priority(priority)
            text = build_signal_text(
                symbol=symbol,
                side=side,
                strategy=strategy,
                final_weight=final_weight,
                meta_score=meta_score,
                risk_flag=risk_flag,
                weak_kind=weak_kind,
                notes=notes,
            )

            dispatchable.append(
                {
                    "symbol": symbol,
                    "ticker": _ticker_from_symbol(symbol),
                    "side": side,
                    "strategy": strategy,
                    "final_weight": final_weight,
                    "meta_score": meta_score,
                    "risk_flag": risk_flag,
                    "weak_kind": weak_kind,
                    "priority": priority,
                    "channel": channel,
                    "text": text,
                }
            )
        except Exception as e:  # pragma: no cover - robustesse
            logger.exception(
                "[signal_dispatcher_telegram] Erreur lors du traitement du signal %s: %s",
                sig,
                e,
            )

    nb_total = len(sized_signals)
    nb_disp = len(dispatchable)

    # Si tout est bloqué par gouvernance → on garde quand même la liste,
    # mais c’est au layer supérieur (telegram_utils / bot) de décider d’envoyer
    # ou non (par exemple en mode “alertes de diagnostic”).
    queue: Dict[str, Any] = {
        "generated_at": _now_iso(),
        "env": env_info.get("env"),
        "instance": env_info.get("instance"),
        "blocked": block_state["blocked"],
        "block_reasons": block_state["reasons"],
        "kill_switch": {
            "mode": block_state["ks_mode"],
            "soft_block": block_state["ks_soft"],
            "hard_block": block_state["ks_hard"],
        },
        "governance": {
            "flag": block_state["gov_flag"],
            "risk_console_flag": block_state["risk_console_flag"],
        },
        "nb_signals_total": nb_total,
        "nb_signals_dispatchable": nb_disp,
        "signals": dispatchable,
    }

    return queue


def main() -> None:
    logger.info("[signal_dispatcher_telegram] DATA_DIR=%s", DATA_DIR)
    queue = build_dispatch_queue(DATA_DIR)

    out_path = DATA_DIR / "trading" / "telegram_signal_queue.json"
    save_json_file(out_path, queue)

    logger.info(
        "[signal_dispatcher_telegram] Queue Telegram sauvegardée (%s) – blocked=%s, total=%d, dispatchable=%d",
        out_path,
        queue.get("blocked"),
        queue.get("nb_signals_total"),
        queue.get("nb_signals_dispatchable"),
    )


if __name__ == "__main__":
    main()
