from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import get_data_dir, load_json_file

try:
    from openai import OpenAI
except Exception:  # noqa: BLE001
    OpenAI = None

logger = get_logger("assistant_router")
router = APIRouter(prefix="/assistant")

DATA_DIR = Path(get_data_dir())
ENV = os.getenv("NSC_ENV", "PREPROD")

# Fichiers d'état principaux
PATH_MARKET_CONDITIONS = DATA_DIR / "analysis" / "market_conditions_engine_pro.json"
PATH_MARKET_COHERENCE = DATA_DIR / "analysis" / "market_coherence_engine_pro.json"
PATH_SIGNAL_QUALITY = DATA_DIR / "analysis" / "signal_quality_engine_pro.json"
PATH_REAL_PROTOCOL = DATA_DIR / "operations" / "real_production_protocol_state.json"
PATH_KNOWLEDGE_DAILY = DATA_DIR / "knowledge" / "knowledge_daily_report.json"
PATH_EVENT_BUS = DATA_DIR / "telemetry" / "event_bus.jsonl"


class AssistantRequest(BaseModel):
    message: str


class AssistantResponse(BaseModel):
    reply: str
    timestamp: str
    env: str
    context_used: Dict[str, bool]


def _now_utc_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_load_json(path: Path, default: Any) -> Any:
    try:
        return load_json_file(path, default=default)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[assistant_router] JSON load error: {path}: {e}")
        return default


def _load_recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    if not PATH_EVENT_BUS.exists():
        return []
    events: List[Dict[str, Any]] = []
    try:
        with PATH_EVENT_BUS.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        return events[-limit:]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[assistant_router] event bus read error: {e}")
        return []


def _build_context() -> Tuple[str, Dict[str, bool]]:
    used = {
        "market_conditions": False,
        "market_coherence": False,
        "signal_quality": False,
        "real_production_protocol": False,
        "knowledge_daily": False,
        "events": False,
    }

    parts: List[str] = []
    parts.append(f"NSC Context – env={ENV}")
    parts.append("")

    mc = _safe_load_json(PATH_MARKET_CONDITIONS, default={})
    if isinstance(mc, dict) and mc:
        used["market_conditions"] = True
        parts.append("=== Market Conditions Engine Pro ===")
        parts.append(f"regime={mc.get('regime','unknown')}, flag={mc.get('global_flag','unknown')}, score={mc.get('score','N/A')}")
        for r in mc.get("reasons", [])[:30]:
            parts.append(f"- {r}")
        parts.append("")

    coh = _safe_load_json(PATH_MARKET_COHERENCE, default={})
    if isinstance(coh, dict) and coh:
        used["market_coherence"] = True
        parts.append("=== Market Coherence Engine Pro ===")
        parts.append(f"flag={coh.get('coherence_flag', coh.get('flag','unknown'))}, score={coh.get('coherence_score', coh.get('score','N/A'))}")
        for r in coh.get("reasons", [])[:30]:
            parts.append(f"- {r}")
        parts.append("")

    sq = _safe_load_json(PATH_SIGNAL_QUALITY, default={})
    if isinstance(sq, dict) and sq:
        used["signal_quality"] = True
        parts.append("=== Signal Quality Engine Pro ===")
        parts.append(f"regime={sq.get('regime','unknown')}, flag={sq.get('quality_flag', sq.get('flag','unknown'))}, score={sq.get('score','N/A')}")
        for r in sq.get("reasons", [])[:30]:
            parts.append(f"- {r}")
        parts.append("")

    rp = _safe_load_json(PATH_REAL_PROTOCOL, default={})
    if isinstance(rp, dict) and rp:
        used["real_production_protocol"] = True
        parts.append("=== Real Production Protocol ===")
        parts.append(f"current_phase={rp.get('current_phase','unknown')}")
        ps = rp.get("phase_status", {}) if isinstance(rp.get("phase_status", {}), dict) else {}
        parts.append(f"status={ps.get('status','unknown')}, checks_ok={ps.get('nb_checks_ok',0)}/{ps.get('nb_checks_total',0)}")
        for r in rp.get("reasons", [])[:30]:
            parts.append(f"- {r}")
        parts.append("")

    kd = _safe_load_json(PATH_KNOWLEDGE_DAILY, default={})
    if isinstance(kd, dict) and kd:
        used["knowledge_daily"] = True
        parts.append("=== Knowledge Daily ===")
        parts.append(f"date={kd.get('date','unknown')}, score={kd.get('knowledge_score','N/A')}, flag={kd.get('knowledge_flag','unknown')}")
        sections = kd.get("sections", {}) if isinstance(kd.get("sections", {}), dict) else {}
        ms = sections.get("market_summary", {}) if isinstance(sections.get("market_summary", {}), dict) else {}
        nb = sections.get("nsc_behavior", {}) if isinstance(sections.get("nsc_behavior", {}), dict) else {}
        tl = sections.get("to_learn_today", {}) if isinstance(sections.get("to_learn_today", {}), dict) else {}
        if ms.get("bullets"):
            parts.append("Market summary:")
            for b in ms.get("bullets", [])[:40]:
                parts.append(f"- {b}")
        if nb.get("bullets"):
            parts.append("NSC behavior:")
            for b in nb.get("bullets", [])[:40]:
                parts.append(f"- {b}")
        if tl.get("bullets"):
            parts.append("To learn today:")
            for b in tl.get("bullets", [])[:40]:
                parts.append(f"- {b}")
        parts.append("")

    evts = _load_recent_events(limit=20)
    if evts:
        used["events"] = True
        parts.append("=== Recent Events (Event Bus) ===")
        for evt in evts:
            ts = evt.get("timestamp", "?")
            sev = evt.get("severity", "?")
            etype = evt.get("type", "?")
            src = evt.get("source", "?")
            msg = evt.get("message", "")
            parts.append(f"{ts} [{sev}] {etype} (src={src}) {msg}")
        parts.append("")

    return "\n".join(parts), used


def _call_llm(user_message: str, context: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return (
            "NSC Assistant est disponible en mode diagnostic local, mais l'appel LLM n'est pas configuré "
            "(OPENAI_API_KEY manquant ou SDK OpenAI indisponible)."
        )

    client = OpenAI(api_key=api_key)
    model = os.getenv("NSC_ASSISTANT_MODEL", "gpt-5.1-mini")

    system_prompt = """
Tu es NSC Assistant, un assistant interne d'analyse pour Nova Star Capital.
Objectif :
- Expliquer factuellement l'état actuel du système (marché, gouvernance, risque, exécution, knowledge daily).
- Identifier les blocages, signaux d'alerte et données manquantes.
- Proposer des pistes de diagnostic et les pages/JSON à vérifier.
Contraintes :
- Ton neutre, institutionnel, structuré.
- Pas d'emojis, pas de marketing, pas de conseils financiers.
- Si une info est manquante, le dire explicitement.
Structure attendue :
1) Etat du système
2) Marché
3) Gouvernance / Production protocol
4) Points de vigilance
5) Actions de diagnostic (concrètes)
"""

    # garde-fou taille
    if len(context) > 12000:
        context = context[-12000:]

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "system", "content": "Contexte NSC:\n" + context},
            {"role": "user", "content": user_message.strip()},
        ],
        temperature=0.1,
        max_tokens=900,
    )
    return resp.choices[0].message.content.strip()


@router.post("/chat", response_model=AssistantResponse)
def chat(payload: AssistantRequest) -> AssistantResponse:
    msg = (payload.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message manquant.")

    context, used = _build_context()
    reply = _call_llm(msg, context)

    return AssistantResponse(
        reply=reply,
        timestamp=_now_utc_iso(),
        env=ENV,
        context_used=used,
    )
