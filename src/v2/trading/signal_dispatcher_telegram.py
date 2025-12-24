# src/v2/trading/signal_dispatcher_telegram.py

import os
import datetime as dt
from typing import Any, Dict, List, Optional

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import (
    get_data_dir,
    load_json_file,
    save_json_file,
)

logger = get_logger(__name__)


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _read_env() -> Dict[str, Any]:
    return {
        "env": os.getenv("NSC_ENV", "PREPROD"),
        "dispatch_mode": os.getenv("NSC_TELEGRAM_DISPATCH_MODE", "queue"),  # queue | send | off
    }


def _load_system_state(data_dir: str) -> Dict[str, Any]:
    metrics_path = os.path.join(data_dir, "telemetry", "system_metrics.json")
    gov_path = os.path.join(data_dir, "analysis", "governance_engine_pro.json")
    kill_path = os.path.join(data_dir, "trading", "kill_switch.json")

    metrics = load_json_file(metrics_path, default={}) or {}
    governance = load_json_file(gov_path, default={}) or {}
    kill_switch = load_json_file(kill_path, default={}) or {}

    return {
        "metrics": metrics,
        "governance": governance,
        "kill_switch": kill_switch,
    }


def _compute_block_state(state: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Détermine si on bloque l'envoi des signaux Telegram.

    Règles actuelles (simples, version PREPROD) :
    - Si NSC_ENV != "PROD" -> on autorise la génération de queue mais on considère
      que l'envoi réel doit être prudente (mode queue par défaut).
    - Si risk_on_off != "on" -> block.
    - Si kill_switch_status in {hard, soft} -> block.
    - Si governance_flag in {hard_block, soft_block} -> block.
    """
    metrics = state.get("metrics") or {}
    governance = state.get("governance") or {}
    kill_switch = state.get("kill_switch") or {}

    reasons: List[str] = []

    risk_on_off = metrics.get("risk_on_off", "on")
    if risk_on_off != "on":
        reasons.append(f"risk_on_off={risk_on_off}")

    kill_status = kill_switch.get("status") or metrics.get("kill_switch_status")
    if kill_status in ("hard", "soft"):
        reasons.append(f"kill_switch_status={kill_status}")

    gov_flag = governance.get("flag") or metrics.get("governance_flag")
    if gov_flag in ("hard_block", "soft_block"):
        reasons.append(f"governance_flag={gov_flag}")

    # En PREPROD on ne bloque pas juste parce qu'on n'est pas en PROD,
    # mais on garde l'info dans les raisons.
    if env.get("env") != "PROD":
        reasons.append(f"env={env.get('env')} (PREPROD)")

    blocked = len(reasons) > 0 and any(
        r.startswith("kill_switch_status=hard") or r.startswith("governance_flag=hard_block")
        for r in reasons
    )

    # NB: on laisse passer les soft_block/caution pour que tu voies les signaux,
    # même si plus tard on pourra durcir la règle.
    return {
        "blocked": blocked,
        "reasons": reasons,
        "risk_on_off": risk_on_off,
        "kill_status": kill_status,
        "governance_flag": gov_flag,
    }


def _load_sized_signals(data_dir: str) -> List[Dict[str, Any]]:
    path = os.path.join(data_dir, "trading", "sized_signals.json")
    data = load_json_file(path, default=[]) or []
    if not isinstance(data, list):
        logger.warning("[signal_dispatcher_telegram] sized_signals.json n'est pas une liste, type=%s", type(data))
        return []
    logger.info("[signal_dispatcher_telegram] %d sized_signals chargés depuis %s", len(data), path)
    return data


def _build_signal_text(sig: Dict[str, Any], env: Dict[str, Any]) -> str:
    """
    Construit un message texte prêt à être envoyé sur Telegram.
    On reste volontairement simple pour la PREPROD.
    """
    symbol = str(sig.get("symbol") or sig.get("asset") or "UNKNOWN").upper()
    side = str(sig.get("side", "buy")).upper()
    strategy = str(sig.get("strategy", "momentum"))
    size_eur = sig.get("size_eur") or sig.get("capital") or 0
    meta_score = sig.get("meta_score") or sig.get("confidence") or sig.get("score") or 0
    risk_flag = sig.get("risk_flag") or sig.get("risk_mode") or "-"

    env_tag = env.get("env", "PREPROD")
    header = f"[NSC {env_tag}] Signal Trading"

    line1 = f"{symbol} – {side}"
    line2 = f"Stratégie : {strategy}"
    line3 = f"Taille ≈ {size_eur:.2f} €"
    line4 = f"Score global : {meta_score:.1f}"
    line5 = f"Contexte risque : {risk_flag}"

    return "\n".join([header, line1, line2, line3, line4, line5])


def _build_queue(
    sized_signals: List[Dict[str, Any]],
    env: Dict[str, Any],
    block_state: Dict[str, Any],
) -> Dict[str, Any]:
    blocked = bool(block_state.get("blocked"))
    reasons = block_state.get("reasons") or []

    signals_with_text: List[Dict[str, Any]] = []
    if not blocked:
        for sig in sized_signals:
            text = _build_signal_text(sig, env)
            payload = dict(sig)
            payload["telegram_text"] = text
            signals_with_text.append(payload)

    queue = {
        "timestamp": _now_iso(),
        "env": env.get("env", "PREPROD"),
        "mode": env.get("dispatch_mode", "queue"),
        "blocked": blocked,
        "block_reasons": reasons,
        "nb_signals_total": len(sized_signals),
        "nb_signals_dispatchable": len(signals_with_text),
        "signals": signals_with_text,
    }
    return queue


def _maybe_send_telegram(queue: Dict[str, Any], data_dir: str, env: Dict[str, Any]) -> Dict[str, Any]:
    """
    En PREPROD, on laisse le mode par défaut à 'queue'.
    Si NSC_TELEGRAM_DISPATCH_MODE=send, on tente d'envoyer les messages.
    """
    mode = env.get("dispatch_mode", "queue")
    if mode != "send":
        logger.info(
            "[signal_dispatcher_telegram] Mode=%s (pas d'envoi Telegram, queue uniquement).",
            mode,
        )
        queue["nb_sent"] = 0
        queue["send_mode"] = mode
        return queue

    if queue.get("blocked"):
        logger.warning(
            "[signal_dispatcher_telegram] Envoi Telegram bloqué (reasons=%s). Aucune notification envoyée.",
            queue.get("block_reasons"),
        )
        queue["nb_sent"] = 0
        queue["send_mode"] = mode
        return queue

    # Ici on est en mode "send" et pas bloqué.
    # On lit la config utilisateurs Telegram.
    users_cfg_path = os.path.join(data_dir, "config", "telegram_users.json")
    users_cfg = load_json_file(users_cfg_path, default={}) or {}
    users = users_cfg.get("users") or []

    if not users:
        logger.warning(
            "[signal_dispatcher_telegram] Aucune config utilisateur Telegram trouvée (%s). "
            "Aucun message ne sera envoyé.",
            users_cfg_path,
        )
        queue["nb_sent"] = 0
        queue["send_mode"] = mode
        return queue

    # Import lazy pour éviter de casser si telegram_utils n'est pas prêt.
    try:
        from src.v2.utils.telegram_utils import send_telegram_message  # type: ignore
    except Exception as e:  # pragma: no cover
        logger.error(
            "[signal_dispatcher_telegram] Impossible d'importer telegram_utils.send_telegram_message: %s",
            e,
        )
        queue["nb_sent"] = 0
        queue["send_mode"] = mode
        return queue

    nb_sent = 0
    signals = queue.get("signals") or []
    for sig in signals:
        text = sig.get("telegram_text")
        if not text:
            continue

        for user in users:
            if not user.get("enabled", True):
                continue
            chat_id = user.get("chat_id")
            if not chat_id:
                continue
            try:
                send_telegram_message(
                    text=text,
                    chat_id=chat_id,
                )
                nb_sent += 1
            except Exception as exc:  # pragma: no cover
                logger.error(
                    "[signal_dispatcher_telegram] Erreur lors de l'envoi Telegram à chat_id=%s: %s",
                    chat_id,
                    exc,
                )

    logger.info(
        "[signal_dispatcher_telegram] Envoi Telegram terminé – messages envoyés=%d (mode=%s).",
        nb_sent,
        mode,
    )
    queue["nb_sent"] = nb_sent
    queue["send_mode"] = mode
    return queue


def main() -> None:
    data_dir = get_data_dir()
    env = _read_env()

    logger.info(
        "[signal_dispatcher_telegram] Démarrage – DATA_DIR=%s, env=%s, mode=%s",
        data_dir,
        env.get("env"),
        env.get("dispatch_mode"),
    )

    sized_signals = _load_sized_signals(data_dir)
    system_state = _load_system_state(data_dir)
    block_state = _compute_block_state(system_state, env)

    queue = _build_queue(sized_signals, env, block_state)
    queue = _maybe_send_telegram(queue, data_dir, env)

    queue_path = os.path.join(data_dir, "trading", "telegram_signal_queue.json")
    save_json_file(queue_path, queue)
    logger.info(
        "[signal_dispatcher_telegram] Queue Telegram sauvegardée (%s) – blocked=%s, total=%d, dispatchable=%d, sent=%s",
        queue_path,
        queue.get("blocked"),
        queue.get("nb_signals_total"),
        queue.get("nb_signals_dispatchable"),
        queue.get("nb_sent", 0),
    )


if __name__ == "__main__":
    main()
