from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_PATH = "/opt/nsc/app/data/trading/kill_switch.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_upper() -> str:
    return (os.environ.get("NSC_ENV") or os.environ.get("ENV") or "UNKNOWN").strip().upper()


def _safe_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return default


def _safe_list(v: Any) -> List[str]:
    if isinstance(v, list):
        out: List[str] = []
        for x in v:
            try:
                out.append(str(x))
            except Exception:
                pass
        return out
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


@dataclass(frozen=True)
class KillSwitchState:
    enabled: bool = False
    hard_block: bool = False
    soft_block: bool = False
    soft_veto: bool = False
    mode: str = "normal"
    reasons: List[str] = field(default_factory=list)
    source: str = "unknown"
    updated_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def blocks_trading(self) -> bool:
        return bool(self.hard_block)

    def explain(self) -> str:
        rs = ", ".join(self.reasons) if self.reasons else "none"
        return (
            f"enabled={self.enabled}, hard_block={self.hard_block}, soft_block={self.soft_block}, "
            f"soft_veto={self.soft_veto}, mode={self.mode}, reasons={rs}, source={self.source}"
        )


def load_kill_switch(path: Optional[str] = None) -> KillSwitchState:
    """
    Source unique de vérité du kill-switch.
    Règles:
      - Si fichier manquant en PREPROD/PROD -> HARD BLOCK (fail-closed)
      - Normalisation: enabled=False => aucun blocage (hard/soft/soft_veto à False)
    """
    env = _env_upper()
    p = path or DEFAULT_PATH

    if not os.path.isfile(p):
        # Fail-closed en PREPROD/PROD
        if env in ("PREPROD", "PROD"):
            return KillSwitchState(
                enabled=True,
                hard_block=True,
                soft_block=True,
                soft_veto=True,
                mode="hard_block",
                reasons=["kill_switch_missing"],
                source="governance",
                updated_at=_utc_now_iso(),
                raw={"path": p, "env": env},
            )
        # DEV/UNKNOWN: fail-open
        return KillSwitchState(
            enabled=False,
            hard_block=False,
            soft_block=False,
            soft_veto=False,
            mode="normal",
            reasons=["kill_switch_missing_dev_fail_open"],
            source="governance",
            updated_at=_utc_now_iso(),
            raw={"path": p, "env": env},
        )

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # JSON corrompu => fail-closed en PREPROD/PROD
        if env in ("PREPROD", "PROD"):
            return KillSwitchState(
                enabled=True,
                hard_block=True,
                soft_block=True,
                soft_veto=True,
                mode="hard_block",
                reasons=["kill_switch_invalid_json"],
                source="governance",
                updated_at=_utc_now_iso(),
                raw={"path": p, "env": env},
            )
        return KillSwitchState(
            enabled=False,
            hard_block=False,
            soft_block=False,
            soft_veto=False,
            mode="normal",
            reasons=["kill_switch_invalid_json_dev_fail_open"],
            source="governance",
            updated_at=_utc_now_iso(),
            raw={"path": p, "env": env},
        )

    if not isinstance(data, dict):
        data = {}

    enabled = _safe_bool(data.get("enabled", False), False)
    hard_block = _safe_bool(data.get("hard_block", False), False)
    soft_block = _safe_bool(data.get("soft_block", False), False)

    # Compat: certains fichiers ont "soft_veto" ou "soft_veto" implicite via mode
    soft_veto = _safe_bool(data.get("soft_veto", False), False)

    mode = str(data.get("mode") or "normal")
    source = str(data.get("source") or "manual")
    updated_at = data.get("updated_at")
    reasons = _safe_list(data.get("reasons"))

    # Compat legacy: parfois "reason" (string)
    if not reasons:
        reasons = _safe_list(data.get("reason"))

    # Normalisation critique
    if not enabled:
        hard_block = False
        soft_block = False
        soft_veto = False
        # si mode “hard_block” traîne alors que enabled=False
        if mode in ("hard", "hard_block"):
            mode = "normal"

    return KillSwitchState(
        enabled=enabled,
        hard_block=hard_block,
        soft_block=soft_block,
        soft_veto=soft_veto,
        mode=mode,
        reasons=reasons,
        source=source,
        updated_at=str(updated_at) if updated_at is not None else None,
        raw=data,
    )


def enforce_hard_block_on_orders(
    orders: List[Dict[str, Any]], ks: KillSwitchState
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Si HARD BLOCK => supprime tous les ordres."""
    if ks and ks.hard_block:
        return [], ["kill_switch:hard_block"]
    return orders, []
