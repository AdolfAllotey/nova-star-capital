#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, hashlib, time, tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any

BASE = Path(__file__).resolve().parents[1]  # /root/src/v2
STATE_PATH = BASE / "data" / "runtime" / "alerts_state.json"
LOG_PATH   = BASE / "data" / "reports" / "alerts.log"
POLICY_PATH= BASE / "config" / "alerts.policy.json"   # <-- optionnel

# --- Defaults globaux (fallback) ---
DEFAULT_TTL_SECONDS = 6 * 3600     # 6h anti-duplicate
DEFAULT_COOLDOWN_S  = 30 * 60      # 30 min par clé
MAX_LOG_LINES       = 5000

# --- Policy par type (fallback code) ---
# Peut être surchargée par /config/alerts.policy.json
DEFAULT_POLICY = {
    # kind: { "ttl": seconds, "cooldown": seconds }
    "worst_trade":     {"ttl": 6*3600, "cooldown": 30*60},
    "breakout":        {"ttl": 2*3600, "cooldown": 15*60},
    "rsi_overbought":  {"ttl": 6*3600, "cooldown": 30*60},
    "rsi_oversold":    {"ttl": 6*3600, "cooldown": 30*60},
    "news_spike":      {"ttl": 1*3600, "cooldown": 10*60},
    # autres types au besoin…
}

def _atomic_write(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent))
    try:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush(); os.fsync(tmp.fileno())
        name = tmp.name
    finally:
        tmp.close()
    os.replace(name, path)

def _load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text() or "null") or default
    except Exception:
        pass
    return default

def _load_policy() -> Dict[str, Dict[str, int]]:
    # Charge un JSON optionnel {"kind": {"ttl": int, "cooldown": int}, ...}
    raw = _load_json(POLICY_PATH, default=None)
    if not raw:
        return DEFAULT_POLICY
    # sanitation légère
    out = dict(DEFAULT_POLICY)
    for k, v in raw.items():
        ttl = int(v.get("ttl", DEFAULT_TTL_SECONDS))
        cd  = int(v.get("cooldown", DEFAULT_COOLDOWN_S))
        out[k] = {"ttl": ttl, "cooldown": cd}
    return out

@dataclass
class Alert:
    kind: str            # ex: "breakout", "rsi_overbought", "news_spike"
    symbol: str          # ex: "BTCUSDT"
    message: str         # texte court
    severity: str = "info"      # info/warn/crit
    source: str = "v2"          # module émetteur
    meta: Optional[Dict[str, Any]] = None  # ex: {"tf":"1h","value":70}

    def key(self) -> str:
        # clé logique pour cooldown (type+symbole+tf)
        return f"{self.kind}:{self.symbol}:{(self.meta or {}).get('tf','')}".lower()

    def hash(self) -> str:
        # hash fort pour déduplication stricte
        h = hashlib.sha256()
        h.update(self.kind.encode())
        h.update(self.symbol.encode())
        h.update((self.message or "").encode())
        h.update(json.dumps(self.meta or {}, sort_keys=True).encode())
        return h.hexdigest()

class AlertManager:
    """
    State schema v2:
      {
        "seen_hashes": { "<hash>": {"ts": <epoch>, "ttl": <seconds>} },
        "last_emitted": { "<key>": {"ts": <epoch>, "cooldown": <seconds>} }
      }
    Ancien schéma (v1) pris en charge automatiquement (migration à la volée).
    """
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS, cooldown_seconds: int = DEFAULT_COOLDOWN_S):
        # valeurs par défaut globales (fallback si aucun policy pour le kind)
        self.default_ttl = int(ttl_seconds)
        self.default_cooldown = int(cooldown_seconds)
        self.policy = _load_policy()
        self.state = _load_json(STATE_PATH, default={"seen_hashes":{}, "last_emitted":{}})
        self._migrate_state_if_needed()

    def _migrate_state_if_needed(self):
        # Convertit vieux schéma (int) -> nouveau schéma (obj ts/ttl ou ts/cooldown)
        sh = self.state.get("seen_hashes", {})
        for k, v in list(sh.items()):
            if isinstance(v, int):
                sh[k] = {"ts": v, "ttl": self.default_ttl}
        le = self.state.get("last_emitted", {})
        for k, v in list(le.items()):
            if isinstance(v, int):
                le[k] = {"ts": v, "cooldown": self.default_cooldown}
        self.state["seen_hashes"] = sh
        self.state["last_emitted"] = le

    def _now(self) -> int:
        return int(time.time())

    def _effective_ttl(self, kind: str) -> int:
        return int(self.policy.get(kind, {}).get("ttl", self.default_ttl))

    def _effective_cooldown(self, kind: str) -> int:
        return int(self.policy.get(kind, {}).get("cooldown", self.default_cooldown))

    def _gc(self):
        # nettoyage des hashes expirés selon leur TTL propre
        now = self._now()
        sh = self.state.get("seen_hashes", {})
        expired = [h for h, obj in sh.items() if now - int(obj.get("ts",0)) > int(obj.get("ttl", self.default_ttl))]
        for h in expired:
            sh.pop(h, None)

    def should_emit(self, alert: Alert) -> bool:
        now = self._now()
        self._gc()

        h = alert.hash()
        sh = self.state["seen_hashes"]
        if h in sh:
            # déjà vu dans la fenêtre TTL propre à cet hash
            if now - int(sh[h].get("ts",0)) <= int(sh[h].get("ttl", self._effective_ttl(alert.kind))):
                return False

        k = alert.key()
        le = self.state["last_emitted"]
        if k in le:
            cd = int(le[k].get("cooldown", self._effective_cooldown(alert.kind)))
            if now - int(le[k].get("ts",0)) < cd:
                return False

        return True

    def record(self, alert: Alert):
        now = self._now()
        ttl = self._effective_ttl(alert.kind)
        cd  = self._effective_cooldown(alert.kind)

        # MàJ state
        h = alert.hash()
        k = alert.key()
        self.state["seen_hashes"][h] = {"ts": now, "ttl": ttl}
        self.state["last_emitted"][k] = {"ts": now, "cooldown": cd}
        _atomic_write(STATE_PATH, self.state)

        # log append (rotation simple)
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": now, "alert": asdict(alert)}, ensure_ascii=False)
        try:
            if LOG_PATH.exists():
                lines = LOG_PATH.read_text().splitlines()
                lines.append(line)
                if len(lines) > MAX_LOG_LINES:
                    lines = lines[-MAX_LOG_LINES:]
                LOG_PATH.write_text("\n".join(lines) + "\n")
            else:
                LOG_PATH.write_text(line + "\n")
        except Exception:
            # on ne propage pas un échec de log
            pass
