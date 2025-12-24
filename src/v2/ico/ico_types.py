# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import datetime as dt

ISO = "%Y-%m-%d"

def iso_now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

def safe_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        # accepte YYYY-MM-DD
        dt.datetime.strptime(s, ISO)
        return s
    except Exception:
        return None

@dataclass
class ICOCandidate:
    symbol: str
    name: str
    chain: Optional[str] = None
    tge_date: Optional[str] = None  # YYYY-MM-DD
    website: Optional[str] = None
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def normalize(self):
        self.symbol = (self.symbol or "").upper().strip()
        self.name = (self.name or "").strip()
        if self.tags:
            self.tags = sorted(list(dict.fromkeys([t.strip().lower() for t in self.tags if t])))
        self.tge_date = safe_date(self.tge_date)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ScreenedICO(ICOCandidate):
    valid: bool = True
    reasons: Optional[List[str]] = None

@dataclass
class ScoredICO(ScreenedICO):
    risk: float = 0.5          # 0..1 (0 = faible risque)
    hype: float = 0.5          # 0..1 (1 = très hype)
    score: float = 0.5         # 0..1 composite
    features: Optional[Dict[str, Any]] = None

@dataclass
class Allocation:
    symbol: str
    amount_usd: float
    rationale: Optional[str] = None

@dataclass
class AllocationPlan:
    generated_at: str
    regime: str
    budget_usd: float
    items: List[Allocation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "regime": self.regime,
            "budget_usd": round(self.budget_usd, 2),
            "items": [asdict(x) for x in self.items],
        }
