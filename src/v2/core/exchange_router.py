# src/v2/core/exchange_router.py

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import logging
logger = logging.getLogger(__name__)

_EXCHANGE_MAP_CACHE: Optional[Dict[str, Any]] = None


def _resolve_token_exchange_map_path() -> Path:
    """
    Priority:
      1) NSC_TOKEN_EXCHANGE_MAP env var
      2) repo canonical candidates (config, data, dist)
    """
    envp = (os.getenv("NSC_TOKEN_EXCHANGE_MAP") or "").strip()
    if envp:
        return Path(envp).expanduser().resolve()

    root = Path(__file__).resolve().parents[3]  # /opt/nsc/app
    candidates = [
        root / "src" / "v2" / "data" / "token_exchange_map.json",
        root / "src" / "v2" / "config" / "token_exchange_map.json",
        root / "dist" / "data" / "token_exchange_map.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


EXCHANGE_MAP_PATH: Path = _resolve_token_exchange_map_path()


def load_exchange_map(force_reload: bool = False) -> Dict[str, Any]:
    """Load mapping token -> exchange (values can be str or dict). Cached in memory."""
    global _EXCHANGE_MAP_CACHE

    if _EXCHANGE_MAP_CACHE is not None and not force_reload:
        return _EXCHANGE_MAP_CACHE

    p = EXCHANGE_MAP_PATH
    if not p.exists():
        logger.warning("[exchange_router] token_exchange_map.json not found: %s", p)
        _EXCHANGE_MAP_CACHE = {}
        return _EXCHANGE_MAP_CACHE

    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            logger.warning("[exchange_router] token_exchange_map.json not a dict: %s", p)
            _EXCHANGE_MAP_CACHE = {}
            return _EXCHANGE_MAP_CACHE
        _EXCHANGE_MAP_CACHE = obj
        return _EXCHANGE_MAP_CACHE
    except Exception as e:
        logger.warning("[exchange_router] failed to load %s: %s", p, e)
        _EXCHANGE_MAP_CACHE = {}
        return _EXCHANGE_MAP_CACHE


def _extract_exchange(v: Any) -> Optional[str]:
    """Accept str or dict; return normalized lowercase exchange or None."""
    if isinstance(v, str):
        vv = v.strip()
        return vv.lower() if vv else None

    if isinstance(v, dict):
        for key in ("exchange", "platform", "venue", "router", "name"):
            val = v.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip().lower()

        ex = v.get("exchange")
        if isinstance(ex, dict):
            val = ex.get("name")
            if isinstance(val, str) and val.strip():
                return val.strip().lower()

    return None


def get_exchange_for_token(token_symbol: str) -> Optional[str]:
    """
    Return exchange for a token symbol.

    Supports:
      - 'MATIC', 'BNB'
      - 'maticusdt', 'MATICUSDT'
      - will also try base token if endswith 'USDT'
    """
    if not token_symbol:
        return None

    exmap = load_exchange_map()
    if not isinstance(exmap, dict) or not exmap:
        return None

    sym = str(token_symbol).strip()
    if not sym:
        return None

    sym_u = sym.upper()
    sym_l = sym.lower()

    base_u = sym_u[:-4] if sym_u.endswith("USDT") else sym_u
    base_l = sym_l[:-4] if sym_l.endswith("usdt") else sym_l

    candidates = [
        sym, sym_u, sym_l,
        base_u, base_l,
        f"{base_u}USDT", f"{base_l}usdt",
    ]

    for k in candidates:
        if k in exmap:
            return _extract_exchange(exmap.get(k))

    return None
