#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_STATE_PATH = Path("data/equities_offensive/state/state.json")
DEFAULT_LOCK_PATH  = Path("data/equities_offensive/state/state.lock")

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _load_json(path: Path, default: Any = None) -> Any:
    # Prefer NSC utilities if present
    try:
        from src.v2.utils.file_utils import load_json_file  # type: ignore
        return load_json_file(str(path), default=default)
    except Exception:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from src.v2.utils.file_utils import save_json_file  # type: ignore
        save_json_file(str(path), data)
    except Exception:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

@dataclass
class StateStore:
    state_path: Path = DEFAULT_STATE_PATH
    lock_path: Path = DEFAULT_LOCK_PATH
    lock_ttl_sec: int = 120

    def _acquire_lock(self) -> None:
        """
        Lock ultra simple via fichier. Suffisant en single-node systemd.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        if self.lock_path.exists():
            age = time.time() - self.lock_path.stat().st_mtime
            if age < self.lock_ttl_sec:
                raise RuntimeError(f"State lock present (age={age:.1f}s) at {self.lock_path}")
            # stale lock -> overwrite
        self.lock_path.write_text(str(time.time()), encoding="utf-8")

    def _release_lock(self) -> None:
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception:
            pass

    def default_state(self) -> Dict[str, Any]:
        return {
            "ts": utc_now_iso(),
            "engine": "equities_state_store_v1",
            "positions": {},  # symbol -> {qty, avg_price, notional_usd, side}
            "orders_seen": [],  # list of plan_id processed
            "last_run": {  # pointers + hashes
                "ts": None,
                "plan_id": None,
                "inputs_hash": None,
            },
            "meta": {
                "schema": 1,
            },
        }

    def load(self) -> Dict[str, Any]:
        st = _load_json(self.state_path, default=None)
        if not isinstance(st, dict):
            st = self.default_state()
        # ensure keys
        st.setdefault("positions", {})
        st.setdefault("orders_seen", [])
        st.setdefault("last_run", {"ts": None, "plan_id": None, "inputs_hash": None})
        st.setdefault("meta", {"schema": 1})
        return st

    def save(self, state: Dict[str, Any]) -> None:
        state["ts"] = utc_now_iso()
        _save_json(self.state_path, state)

    def with_lock(self):
        """
        Context manager style (manual) : acquire/release.
        """
        self._acquire_lock()
        return self

    def close(self) -> None:
        self._release_lock()

    # Helpers idempotence
    def has_seen_plan(self, state: Dict[str, Any], plan_id: Optional[str]) -> bool:
        if not plan_id:
            return False
        return plan_id in (state.get("orders_seen") or [])

    def mark_plan_seen(self, state: Dict[str, Any], plan_id: Optional[str]) -> None:
        if not plan_id:
            return
        seen = state.setdefault("orders_seen", [])
        if plan_id not in seen:
            seen.append(plan_id)

    def set_last_run(self, state: Dict[str, Any], plan_id: Optional[str], inputs_obj: Any) -> None:
        payload = json.dumps(inputs_obj, sort_keys=True, ensure_ascii=False)
        state["last_run"] = {
            "ts": utc_now_iso(),
            "plan_id": plan_id,
            "inputs_hash": sha256(payload)[:16],
        }

def main():
    store = StateStore()
    store.with_lock()
    try:
        st = store.load()
        store.save(st)
        print(json.dumps({"ok": True, "state_path": str(store.state_path)}, ensure_ascii=False, indent=2))
    finally:
        store.close()

if __name__ == "__main__":
    main()
