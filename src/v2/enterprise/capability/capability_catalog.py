from __future__ import annotations

"""
Nova Star Capital
Enterprise Capability Catalog V1

This module defines the official business capability model of NSC.

The catalog is intentionally independent from the current source-code layout.
Technical components may change without changing the underlying business
capabilities.

Generated artefacts
-------------------
/opt/nsc/data/preprod/enterprise/capability_catalog.json
/opt/nsc/data/preprod/enterprise/capability_catalog_statistics.json
/opt/nsc/data/preprod/enterprise/CAPABILITY_CATALOG_REPORT.md
"""

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


APP_ROOT = Path("/opt/nsc/app")
DEFAULT_OUTPUT_ROOT = Path("/opt/nsc/data/preprod/enterprise")

SCHEMA_VERSION = "1.0"
CATALOG_VERSION = "1.0.0"

LOGGER = logging.getLogger("nsc.enterprise.capability.catalog")


VALID_STATUSES = {
    "concept",
    "planned",
    "prototype",
    "implemented",
    "integrated",
    "validated",
    "certified",
    "production_ready",
    "production",
    "shadow",
    "deprecated",
    "archived",
}

VALID_LIFECYCLE_PHASES = {
    "ideation",
    "architecture",
    "implementation",
    "integration",
    "explainability",
    "documentation",
    "certification",
    "observation",
    "production",
    "evolution",
}

VALID_ROADMAP_PHASES = {
    "RC1",
    "RC2",
    "POST_PRODUCTION",
    "CONTINUOUS",
}

VALID_CRITICALITIES = {
    "critical",
    "high",
    "important",
    "standard",
}

VALID_MATURITY_LEVELS = set(range(0, 7))


@dataclass(frozen=True)
class CertificationRequirements:
    implementation: bool = True
    integration: bool = True
    documentation: bool = True
    explainability: bool = True
    audit: bool = True
    reporting: bool = False
    api: bool = False
    dashboard: bool = False
    tests: bool = True
    runtime_observation: bool = True

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    domain_id: str
    name: str
    description: str
    owner: str
    criticality: str
    roadmap_phase: str
    lifecycle_phase: str
    target_status: str
    target_maturity: int
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    component_keywords: tuple[str, ...] = field(default_factory=tuple)
    path_keywords: tuple[str, ...] = field(default_factory=tuple)
    api_keywords: tuple[str, ...] = field(default_factory=tuple)
    dashboard_keywords: tuple[str, ...] = field(default_factory=tuple)
    report_keywords: tuple[str, ...] = field(default_factory=tuple)
    documentation_keywords: tuple[str, ...] = field(default_factory=tuple)
    kpis: tuple[str, ...] = field(default_factory=tuple)
    certification: CertificationRequirements = field(
        default_factory=CertificationRequirements
    )
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dependencies"] = list(self.dependencies)
        payload["component_keywords"] = list(self.component_keywords)
        payload["path_keywords"] = list(self.path_keywords)
        payload["api_keywords"] = list(self.api_keywords)
        payload["dashboard_keywords"] = list(self.dashboard_keywords)
        payload["report_keywords"] = list(self.report_keywords)
        payload["documentation_keywords"] = list(
            self.documentation_keywords
        )
        payload["kpis"] = list(self.kpis)
        return payload


@dataclass(frozen=True)
class CapabilityDomain:
    domain_id: str
    name: str
    description: str
    owner: str
    capabilities: tuple[Capability, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "capabilities_count": len(self.capabilities),
            "capabilities": [
                capability.to_dict()
                for capability in self.capabilities
            ],
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        + "\n",
    )


def certification(
    *,
    reporting: bool = False,
    api: bool = False,
    dashboard: bool = False,
    explainability: bool = True,
    tests: bool = True,
    runtime_observation: bool = True,
) -> CertificationRequirements:
    return CertificationRequirements(
        implementation=True,
        integration=True,
        documentation=True,
        explainability=explainability,
        audit=True,
        reporting=reporting,
        api=api,
        dashboard=dashboard,
        tests=tests,
        runtime_observation=runtime_observation,
    )


def capability(
    capability_id: str,
    domain_id: str,
    name: str,
    description: str,
    owner: str,
    *,
    criticality: str = "important",
    roadmap_phase: str = "RC1",
    lifecycle_phase: str = "certification",
    target_status: str = "production_ready",
    target_maturity: int = 5,
    dependencies: Iterable[str] = (),
    component_keywords: Iterable[str] = (),
    path_keywords: Iterable[str] = (),
    api_keywords: Iterable[str] = (),
    dashboard_keywords: Iterable[str] = (),
    report_keywords: Iterable[str] = (),
    documentation_keywords: Iterable[str] = (),
    kpis: Iterable[str] = (),
    requirements: CertificationRequirements | None = None,
    notes: str | None = None,
) -> Capability:
    return Capability(
        capability_id=capability_id,
        domain_id=domain_id,
        name=name,
        description=description,
        owner=owner,
        criticality=criticality,
        roadmap_phase=roadmap_phase,
        lifecycle_phase=lifecycle_phase,
        target_status=target_status,
        target_maturity=target_maturity,
        dependencies=tuple(dependencies),
        component_keywords=tuple(component_keywords),
        path_keywords=tuple(path_keywords),
        api_keywords=tuple(api_keywords),
        dashboard_keywords=tuple(dashboard_keywords),
        report_keywords=tuple(report_keywords),
        documentation_keywords=tuple(documentation_keywords),
        kpis=tuple(kpis),
        certification=requirements or certification(),
        notes=notes,
    )


def build_catalog() -> tuple[CapabilityDomain, ...]:
    investment_intelligence = CapabilityDomain(
        domain_id="investment_intelligence",
        name="Investment Intelligence",
        description=(
            "Discover, qualify, rank and validate market opportunities "
            "before portfolio decision-making."
        ),
        owner="Market Intelligence",
        capabilities=(
            capability(
                "CAP-INT-001",
                "investment_intelligence",
                "Market Discovery",
                "Discovers market opportunities across supported sources.",
                "Market Intelligence",
                criticality="critical",
                component_keywords=(
                    "market_discovery",
                    "discovery_engine",
                    "candidates",
                ),
                path_keywords=("discovery",),
                api_keywords=("discovery", "top-movers", "top-losers"),
                dashboard_keywords=("TopMovers", "Crypto", "Discovery"),
                report_keywords=("discovery", "candidates"),
                kpis=(
                    "sources_available",
                    "candidates_detected",
                    "cross_source_confirmation_rate",
                    "data_freshness",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-INT-002",
                "investment_intelligence",
                "Momentum Analysis",
                "Measures price acceleration, strength and momentum quality.",
                "Market Intelligence",
                criticality="high",
                dependencies=("CAP-INT-001",),
                component_keywords=(
                    "momentum",
                    "momentum_scoring",
                    "acceleration",
                ),
                path_keywords=("momentum",),
                api_keywords=("momentum",),
                dashboard_keywords=("TopMovers", "SignalBoard"),
                kpis=(
                    "momentum_score",
                    "acceleration_score",
                    "signal_stability",
                ),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-INT-003",
                "investment_intelligence",
                "Persistence Analysis",
                "Measures whether opportunities persist over multiple windows.",
                "Market Intelligence",
                criticality="high",
                dependencies=("CAP-INT-001",),
                component_keywords=("persistence", "ranking_history"),
                path_keywords=("persistence",),
                report_keywords=("persistence",),
                kpis=(
                    "persistence_6h",
                    "persistence_12h",
                    "persistence_24h",
                ),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-INT-004",
                "investment_intelligence",
                "Signal Intelligence",
                "Builds and aggregates tradable signals from market evidence.",
                "Market Intelligence",
                criticality="critical",
                dependencies=("CAP-INT-001", "CAP-INT-002"),
                component_keywords=(
                    "signal",
                    "signal_voting",
                    "signal_engine",
                ),
                path_keywords=("signals",),
                api_keywords=("signals",),
                dashboard_keywords=("SignalBoard", "Strategy"),
                kpis=(
                    "signals_generated",
                    "signal_confidence",
                    "signal_agreement",
                ),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-INT-005",
                "investment_intelligence",
                "Meta Ranking",
                "Combines source-level rankings into a consolidated ranking.",
                "Market Intelligence",
                criticality="critical",
                dependencies=(
                    "CAP-INT-002",
                    "CAP-INT-003",
                    "CAP-INT-004",
                ),
                component_keywords=("meta_ranking", "ranking_engine"),
                path_keywords=("ranking",),
                report_keywords=("ranking",),
                kpis=(
                    "ranked_assets",
                    "ranking_confidence",
                    "ranking_stability",
                ),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-INT-006",
                "investment_intelligence",
                "Meta Validation",
                "Validates ranked opportunities through independent evidence.",
                "Market Intelligence",
                criticality="critical",
                dependencies=("CAP-INT-005",),
                component_keywords=(
                    "meta_validation",
                    "validation_engine",
                    "cross_source_validator",
                ),
                path_keywords=("validation",),
                report_keywords=("validation",),
                kpis=(
                    "validated_candidates",
                    "rejected_candidates",
                    "validation_confidence",
                ),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-INT-007",
                "investment_intelligence",
                "Market Regime Detection",
                "Identifies the current market regime used by allocation logic.",
                "Market Intelligence",
                criticality="critical",
                component_keywords=("market_regime", "regime_engine"),
                path_keywords=("regime",),
                api_keywords=("market-regime", "regime"),
                dashboard_keywords=("MarketRegime", "DashboardV4"),
                kpis=("current_regime", "regime_confidence"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-INT-008",
                "investment_intelligence",
                "Sentiment Intelligence",
                "Measures market and asset-level sentiment.",
                "Market Intelligence",
                criticality="important",
                component_keywords=("sentiment",),
                path_keywords=("sentiment",),
                api_keywords=("sentiment",),
                dashboard_keywords=("Sentiment",),
                kpis=("sentiment_score", "sentiment_change"),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
        ),
    )

    asset_management = CapabilityDomain(
        domain_id="asset_management",
        name="Asset Management",
        description=(
            "Asset-class-specific intelligence and portfolio management."
        ),
        owner="Investment Platform",
        capabilities=(
            capability(
                "CAP-AST-001",
                "asset_management",
                "Crypto Asset Management",
                "Manages crypto discovery, selection and simulated execution.",
                "Crypto Platform",
                criticality="critical",
                dependencies=(
                    "CAP-INT-001",
                    "CAP-INT-004",
                    "CAP-INT-006",
                ),
                component_keywords=("crypto", "trading_kernel"),
                path_keywords=("crypto",),
                api_keywords=("crypto",),
                dashboard_keywords=("Crypto",),
                report_keywords=("crypto",),
                kpis=(
                    "crypto_exposure",
                    "open_positions",
                    "realized_pnl",
                    "unrealized_pnl",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-002",
                "asset_management",
                "Offensive Equities Management",
                "Selects and manages growth-oriented equity exposure.",
                "Offensive Equities",
                criticality="critical",
                dependencies=("CAP-INT-007",),
                component_keywords=(
                    "offensive_equities",
                    "offensive_engine",
                ),
                path_keywords=("offensive_equities", "offensive"),
                api_keywords=("offensive",),
                dashboard_keywords=("Offensive",),
                report_keywords=("offensive",),
                kpis=(
                    "universe_coverage",
                    "selected_equities",
                    "offensive_exposure",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-003",
                "asset_management",
                "Defensive Equities Management",
                "Selects defensive equities and equity ETFs.",
                "Defensive Equities",
                criticality="critical",
                dependencies=("CAP-INT-007",),
                component_keywords=(
                    "defensive_equities",
                    "defensive_engine",
                    "dividend_stability",
                ),
                path_keywords=("defensive_equities", "defensive"),
                api_keywords=("defensive",),
                dashboard_keywords=("Defensive",),
                report_keywords=("defensive",),
                kpis=(
                    "defensive_exposure",
                    "dividend_stability",
                    "quality_score",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-004",
                "asset_management",
                "Fixed Income Management",
                "Manages sovereign and corporate fixed-income exposure.",
                "Fixed Income",
                criticality="high",
                dependencies=("CAP-INT-007",),
                component_keywords=("bond", "fixed_income"),
                path_keywords=("bonds", "fixed_income"),
                api_keywords=("bonds",),
                dashboard_keywords=("Bonds",),
                report_keywords=("bonds",),
                kpis=(
                    "bond_exposure",
                    "duration",
                    "credit_quality",
                    "yield",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-005",
                "asset_management",
                "Precious Metals Management",
                "Manages dedicated precious-metals exposure.",
                "Precious Metals",
                criticality="high",
                dependencies=("CAP-INT-007",),
                component_keywords=("precious_metals", "gold", "silver"),
                path_keywords=("precious_metals", "metals"),
                api_keywords=("precious-metals", "metals"),
                dashboard_keywords=("PreciousMetals",),
                report_keywords=("precious_metals", "metals"),
                kpis=("metals_exposure", "gold_weight", "hedge_contribution"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-006",
                "asset_management",
                "Options Management",
                "Manages approved US options strategies.",
                "Options Platform",
                criticality="critical",
                roadmap_phase="RC2",
                lifecycle_phase="integration",
                target_status="production_ready",
                target_maturity=5,
                dependencies=(
                    "CAP-PRT-001",
                    "CAP-RSK-001",
                    "CAP-EXE-001",
                ),
                component_keywords=(
                    "options_signal_engine",
                    "options_context_engine",
                    "options_portfolio_engine",
                    "options_risk_engine",
                    "options_risk_controller",
                    "options_position_manager",
                    "options_strategy_selector",
                    "run_options_pipeline",
                    "cash_secured_put_builder",
                    "covered_call_builder",
                    "vertical_spread_builder",
                    "volatility_engine",
                ),
                path_keywords=(
                    "options/engines",
                    "options/builders",
                    "options_v3",
                ),
                api_keywords=("options",),
                dashboard_keywords=("Options",),
                report_keywords=("options_daily_report",),
                kpis=(
                    "options_exposure",
                    "delta",
                    "theta",
                    "max_loss",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
                notes="Shadow during RC1; integrated and observed during RC2.",
            ),
            capability(
                "CAP-AST-007",
                "asset_management",
                "Long-Term Investment Management",
                "Manages strategic long-term investment allocations.",
                "Long-Term Portfolio",
                criticality="high",
                dependencies=("CAP-PRT-001",),
                component_keywords=("long_term", "longterm"),
                path_keywords=("long_term", "longterm"),
                api_keywords=("long-term",),
                dashboard_keywords=("LongTerm", "Portfolio"),
                report_keywords=("long_term",),
                kpis=("long_term_value", "allocation_drift"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-AST-008",
                "asset_management",
                "Airdrop Management",
                "Tracks and governs approved airdrop opportunities.",
                "Alternative Investments",
                criticality="standard",
                roadmap_phase="POST_PRODUCTION",
                lifecycle_phase="architecture",
                target_status="planned",
                target_maturity=3,
                component_keywords=("airdrop",),
                path_keywords=("airdrop",),
                kpis=("qualified_airdrops", "realized_value"),
                requirements=certification(
                    reporting=True,
                    api=False,
                    dashboard=False,
                ),
            ),
        ),
    )

    portfolio_management = CapabilityDomain(
        domain_id="portfolio_management",
        name="Portfolio Management",
        description=(
            "Central multi-asset decision, allocation and portfolio control."
        ),
        owner="Portfolio Brain",
        capabilities=(
            capability(
                "CAP-PRT-001",
                "portfolio_management",
                "Portfolio Brain",
                "Central multi-asset decision and coordination capability.",
                "Portfolio Brain",
                criticality="critical",
                dependencies=(
                    "CAP-INT-006",
                    "CAP-INT-007",
                    "CAP-RSK-001",
                    "CAP-GOV-001",
                ),
                component_keywords=("portfolio_brain", "portfolio_engine"),
                path_keywords=("portfolio",),
                api_keywords=("portfolio", "executive"),
                dashboard_keywords=(
                    "Portfolio",
                    "Executive",
                    "FamilyOfficeDashboard",
                ),
                report_keywords=("portfolio", "executive"),
                kpis=(
                    "portfolio_value",
                    "capital_engaged",
                    "cash_available",
                    "decision_confidence",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-002",
                "portfolio_management",
                "Capital Allocation",
                "Allocates available capital across assets and strategies.",
                "Portfolio Brain",
                criticality="critical",
                dependencies=("CAP-PRT-001", "CAP-RSK-001"),
                component_keywords=(
                    "capital_allocator",
                    "allocation_engine",
                ),
                path_keywords=("allocation", "capital"),
                api_keywords=("allocation", "capital-allocator"),
                dashboard_keywords=("AllocationRebalance", "FundingPools"),
                report_keywords=("allocation",),
                kpis=(
                    "target_allocation",
                    "actual_allocation",
                    "capital_utilization",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-003",
                "portfolio_management",
                "Portfolio Rebalancing",
                "Detects and resolves allocation drift.",
                "Portfolio Brain",
                criticality="critical",
                dependencies=("CAP-PRT-002",),
                component_keywords=("rebalance", "rebalancing"),
                path_keywords=("rebalance",),
                api_keywords=("rebalance",),
                dashboard_keywords=("AllocationRebalance",),
                report_keywords=("rebalance",),
                kpis=(
                    "allocation_drift",
                    "rebalance_actions",
                    "rebalance_status",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-004",
                "portfolio_management",
                "Exposure Management",
                "Controls portfolio, strategy and asset-level exposure.",
                "Portfolio Brain",
                criticality="critical",
                dependencies=("CAP-PRT-002", "CAP-RSK-002"),
                component_keywords=("exposure",),
                path_keywords=("exposure",),
                api_keywords=("exposure",),
                dashboard_keywords=("RiskOverview", "Portfolio"),
                kpis=(
                    "gross_exposure",
                    "net_exposure",
                    "asset_exposure",
                ),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-005",
                "portfolio_management",
                "Funding Management",
                "Manages capital inflows, funding pools and deployment policy.",
                "Capital Management",
                criticality="critical",
                dependencies=("CAP-PRT-002",),
                component_keywords=("funding", "funding_plan"),
                path_keywords=("funding",),
                api_keywords=("funding",),
                dashboard_keywords=("FundingPools",),
                report_keywords=("funding",),
                kpis=(
                    "available_funding",
                    "deployed_funding",
                    "funding_gap",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-006",
                "portfolio_management",
                "Treasury Management",
                "Manages cash, stable assets and liquidity reserves.",
                "Treasury",
                criticality="critical",
                dependencies=("CAP-PRT-005",),
                component_keywords=("treasury", "cash_management"),
                path_keywords=("treasury",),
                api_keywords=("treasury", "cash"),
                dashboard_keywords=("FundingPools", "Portfolio"),
                kpis=("cash_balance", "liquidity_ratio", "stable_reserves"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-PRT-007",
                "portfolio_management",
                "Performance Attribution",
                "Explains portfolio performance by asset and decision driver.",
                "Portfolio Brain",
                criticality="high",
                dependencies=("CAP-PRT-001",),
                component_keywords=("attribution", "performance"),
                path_keywords=("attribution", "performance"),
                api_keywords=("attribution", "alpha-beta"),
                dashboard_keywords=("Attribution", "AlphaBeta"),
                report_keywords=("attribution", "performance"),
                kpis=("alpha", "beta", "contribution", "attribution_gap"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
        ),
    )

    execution = CapabilityDomain(
        domain_id="execution",
        name="Execution",
        description=(
            "Transforms approved decisions into controlled orders, fills "
            "and positions."
        ),
        owner="Execution Platform",
        capabilities=(
            capability(
                "CAP-EXE-001",
                "execution",
                "Execution Kernel",
                "Applies final execution rules to approved decisions.",
                "Execution Platform",
                criticality="critical",
                dependencies=("CAP-GOV-002", "CAP-RSK-001"),
                component_keywords=("execution_kernel", "trading_kernel"),
                path_keywords=("execution",),
                report_keywords=("execution",),
                kpis=(
                    "approved_orders",
                    "rejected_orders",
                    "execution_mode",
                ),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-EXE-002",
                "execution",
                "Order Management",
                "Creates, tracks and manages order lifecycle.",
                "Execution Platform",
                criticality="critical",
                dependencies=("CAP-EXE-001",),
                component_keywords=("order_manager", "orders"),
                path_keywords=("orders",),
                api_keywords=("orders",),
                dashboard_keywords=("OrderBoard",),
                kpis=("open_orders", "order_status", "rejection_rate"),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-EXE-003",
                "execution",
                "Fill Management",
                "Tracks simulated or real execution fills.",
                "Execution Platform",
                criticality="critical",
                dependencies=("CAP-EXE-002",),
                component_keywords=("fill", "fills"),
                path_keywords=("fills",),
                api_keywords=("fills",),
                dashboard_keywords=("FillsBoard",),
                kpis=("fills_count", "average_slippage", "fill_ratio"),
                requirements=certification(
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-EXE-004",
                "execution",
                "Position Management",
                "Maintains open and closed position state.",
                "Execution Platform",
                criticality="critical",
                dependencies=("CAP-EXE-003",),
                component_keywords=("position_manager", "positions"),
                path_keywords=("positions",),
                api_keywords=("positions",),
                dashboard_keywords=("PositionsBoard", "OpenPositions"),
                kpis=(
                    "open_positions",
                    "closed_positions",
                    "position_consistency",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-EXE-005",
                "execution",
                "Broker Connectivity",
                "Connects the platform to approved execution brokers.",
                "Execution Platform",
                criticality="critical",
                dependencies=("CAP-EXE-001",),
                component_keywords=(
                    "broker_connector",
                    "broker_connection",
                    "broker_client",
                    "broker_adapter",
                    "execution_broker",
                    "live_broker",
                    "binance_broker",
                    "mexc_broker",
                    "bitpanda_broker",
                    "ibkr_broker",
                ),
                path_keywords=(
                    "broker/connectors",
                    "broker/adapters",
                    "broker/clients",
                    "integrations/brokers",
                ),
                api_keywords=(
                    "broker-connectivity",
                    "broker-connections",
                ),
                kpis=(
                    "available_brokers",
                    "broker_health",
                    "connection_failures",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                ),
            ),
            capability(
                "CAP-EXE-006",
                "execution",
                "Multi-Broker Routing",
                "Selects an approved broker based on asset and availability.",
                "Execution Platform",
                criticality="critical",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="production_ready",
                target_maturity=5,
                dependencies=("CAP-EXE-005", "CAP-GOV-001"),
                component_keywords=("multi_broker", "broker_router"),
                path_keywords=("multi_broker",),
                api_keywords=("broker-routing",),
                kpis=(
                    "routing_success_rate",
                    "broker_failover_rate",
                    "routing_latency",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                ),
            ),
        ),
    )

    risk = CapabilityDomain(
        domain_id="risk_management",
        name="Risk Management",
        description="Measures, constrains and reports investment risk.",
        owner="Risk Management",
        capabilities=(
            capability(
                "CAP-RSK-001",
                "risk_management",
                "Risk Engine",
                "Central risk assessment and control capability.",
                "Risk Management",
                criticality="critical",
                component_keywords=("risk_engine",),
                path_keywords=("risk",),
                api_keywords=("risk",),
                dashboard_keywords=("RiskOverview", "ControlRoom"),
                report_keywords=("risk",),
                kpis=("risk_score", "risk_status", "active_breaches"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-RSK-002",
                "risk_management",
                "Exposure Limits",
                "Defines and enforces exposure limits.",
                "Risk Management",
                criticality="critical",
                dependencies=("CAP-RSK-001",),
                component_keywords=("exposure_limit", "limit_engine"),
                path_keywords=("limits", "exposure"),
                kpis=("limit_utilization", "limit_breaches"),
            ),
            capability(
                "CAP-RSK-003",
                "risk_management",
                "Drawdown Control",
                "Measures and governs portfolio drawdown.",
                "Risk Management",
                criticality="critical",
                dependencies=("CAP-RSK-001",),
                component_keywords=("drawdown",),
                path_keywords=("drawdown",),
                dashboard_keywords=("RiskOverview", "WorstTrades"),
                kpis=("current_drawdown", "maximum_drawdown"),
                requirements=certification(dashboard=True),
            ),
            capability(
                "CAP-RSK-004",
                "risk_management",
                "Concentration Risk",
                "Measures concentration by asset, strategy and class.",
                "Risk Management",
                criticality="high",
                dependencies=("CAP-RSK-001",),
                component_keywords=("concentration",),
                path_keywords=("concentration",),
                kpis=("largest_position", "concentration_score"),
            ),
            capability(
                "CAP-RSK-005",
                "risk_management",
                "Stress Testing",
                "Evaluates portfolio response to adverse scenarios.",
                "Risk Management",
                criticality="high",
                dependencies=("CAP-RSK-001",),
                component_keywords=("stress_test", "scenario"),
                path_keywords=("stress", "scenario"),
                kpis=("stress_loss", "scenario_count"),
                requirements=certification(reporting=True),
            ),
        ),
    )

    governance = CapabilityDomain(
        domain_id="governance",
        name="Governance and Explainability",
        description=(
            "Controls decisions, vetoes, traceability and institutional "
            "explainability."
        ),
        owner="Governance",
        capabilities=(
            capability(
                "CAP-GOV-001",
                "governance",
                "Governance Engine",
                "Applies institutional governance rules.",
                "Governance",
                criticality="critical",
                dependencies=("CAP-RSK-001",),
                component_keywords=("governance_engine",),
                path_keywords=("governance",),
                api_keywords=("governance",),
                dashboard_keywords=("Governance",),
                report_keywords=("governance",),
                kpis=("governance_status", "open_violations"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-GOV-002",
                "governance",
                "Decision Veto",
                "Blocks decisions that violate governance or risk rules.",
                "Governance",
                criticality="critical",
                dependencies=("CAP-GOV-001", "CAP-RSK-001"),
                component_keywords=("veto", "soft_veto", "hard_veto"),
                path_keywords=("veto",),
                kpis=("veto_count", "veto_reasons"),
            ),
            capability(
                "CAP-GOV-003",
                "governance",
                "Kill Switch",
                "Stops execution when critical control conditions are met.",
                "Governance",
                criticality="critical",
                dependencies=("CAP-GOV-002",),
                component_keywords=("kill_switch", "emergency_stop"),
                path_keywords=("kill_switch",),
                kpis=("kill_switch_status", "activation_count"),
            ),
            capability(
                "CAP-GOV-004",
                "governance",
                "Decision Explainability",
                "Explains the evidence and rules behind each decision.",
                "Governance",
                criticality="critical",
                dependencies=(
                    "CAP-INT-006",
                    "CAP-PRT-001",
                    "CAP-RSK-001",
                ),
                component_keywords=(
                    "explainability",
                    "decision_driver",
                    "decision_trace",
                ),
                path_keywords=("explainability",),
                api_keywords=("explainability", "decision-drivers"),
                dashboard_keywords=("Executive", "Strategy"),
                report_keywords=("explainability", "decision"),
                kpis=(
                    "explainability_coverage",
                    "unexplained_decisions",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-GOV-005",
                "governance",
                "Decision Audit Trail",
                "Records the complete lifecycle of platform decisions.",
                "Governance",
                criticality="critical",
                dependencies=("CAP-GOV-004",),
                component_keywords=("audit_trail", "decision_log"),
                path_keywords=("audit_trail", "decision_log"),
                report_keywords=("audit_trail",),
                kpis=("traceable_decisions", "audit_gaps"),
                requirements=certification(
                    reporting=True,
                    explainability=True,
                ),
            ),
        ),
    )

    operations = CapabilityDomain(
        domain_id="operations",
        name="Platform Operations",
        description=(
            "Runs, observes and controls the platform in preproduction "
            "and production."
        ),
        owner="Platform Operations",
        capabilities=(
            capability(
                "CAP-OPS-001",
                "operations",
                "Runtime Orchestration",
                "Coordinates execution of platform pipelines.",
                "Platform Operations",
                criticality="critical",
                component_keywords=("orchestrator", "runtime"),
                path_keywords=("orchestration", "runtime"),
                kpis=("pipeline_success_rate", "runtime_failures"),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-OPS-002",
                "operations",
                "Scheduling",
                "Schedules recurring platform jobs.",
                "Platform Operations",
                criticality="critical",
                dependencies=("CAP-OPS-001",),
                component_keywords=("scheduler", "schedule"),
                path_keywords=("scheduler",),
                kpis=("scheduled_jobs", "late_jobs", "failed_jobs"),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-OPS-003",
                "operations",
                "Platform Monitoring",
                "Monitors component and pipeline health.",
                "Platform Operations",
                criticality="critical",
                dependencies=("CAP-OPS-001",),
                component_keywords=("monitor", "health"),
                path_keywords=("monitoring",),
                api_keywords=("system-status", "health"),
                dashboard_keywords=("SystemStatus", "ControlRoom"),
                report_keywords=("monitoring", "health"),
                kpis=("healthy_components", "failed_components", "uptime"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-OPS-004",
                "operations",
                "Alerting",
                "Raises actionable alerts for operational anomalies.",
                "Platform Operations",
                criticality="high",
                dependencies=("CAP-OPS-003",),
                component_keywords=("alert", "notification"),
                path_keywords=("alerts",),
                kpis=("open_alerts", "critical_alerts", "alert_latency"),
            ),
            capability(
                "CAP-OPS-005",
                "operations",
                "Daily Review",
                "Produces the daily operational and investment review.",
                "Platform Operations",
                criticality="critical",
                dependencies=("CAP-RPT-001", "CAP-OPS-003"),
                component_keywords=("daily_review", "daily_check"),
                path_keywords=("daily_review", "daily_check"),
                report_keywords=("daily_review", "daily_check"),
                kpis=("daily_review_status", "review_findings"),
                requirements=certification(reporting=True),
            ),
            capability(
                "CAP-OPS-006",
                "operations",
                "Preproduction Observation",
                "Tracks RC1 and RC2 observation evidence.",
                "Preproduction",
                criticality="critical",
                dependencies=("CAP-OPS-003", "CAP-AUD-001"),
                component_keywords=(
                    "preprod_observation",
                    "preprod_aggregate_kpis",
                    "global_preprod_anomaly_detector",
                    "global_preprod_history_summary",
                    "global_preprod_long_run_daily_check",
                    "global_preprod_trend_monitor",
                    "global_preprod_weekly_review",
                    "global_preprod_committee_review",
                ),
                path_keywords=(
                    "preprod/observation",
                    "preprod/monitoring",
                    "global_preprod_long_run",
                ),
                report_keywords=(
                    "global_preprod_long_run_daily_report",
                    "preprod_observation_report",
                ),
                kpis=("observation_days", "blocking_incidents"),
                requirements=certification(reporting=True),
            ),
        ),
    )

    reporting = CapabilityDomain(
        domain_id="reporting",
        name="Reporting and Executive Control",
        description="Produces operational, investment and executive reporting.",
        owner="Reporting",
        capabilities=(
            capability(
                "CAP-RPT-001",
                "reporting",
                "Operational Reporting",
                "Produces machine-readable and human-readable reports.",
                "Reporting",
                criticality="critical",
                component_keywords=("report", "reporting"),
                path_keywords=("reporting", "reports"),
                api_keywords=("reports",),
                kpis=("reports_generated", "report_failures"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-RPT-002",
                "reporting",
                "Executive Reporting",
                "Provides executive portfolio and platform summaries.",
                "Reporting",
                criticality="critical",
                dependencies=("CAP-RPT-001", "CAP-PRT-001"),
                component_keywords=("executive_report",),
                path_keywords=("executive_report",),
                api_keywords=("executive",),
                dashboard_keywords=(
                    "Executive",
                    "FamilyOfficeDashboard",
                    "DashboardV4",
                ),
                report_keywords=("executive_report",),
                kpis=("executive_report_status", "decision_summary"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-RPT-003",
                "reporting",
                "Profitability Reporting",
                "Reports realized and unrealized profitability.",
                "Reporting",
                criticality="high",
                dependencies=("CAP-EXE-004",),
                component_keywords=("profitability", "pnl"),
                path_keywords=("profitability", "pnl"),
                api_keywords=("profitability", "pnl"),
                dashboard_keywords=("Profitability",),
                kpis=("realized_pnl", "unrealized_pnl", "win_rate"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
            capability(
                "CAP-RPT-004",
                "reporting",
                "Executive Digital Twin",
                "Provides a unified executive view of architecture and readiness.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                dependencies=(
                    "CAP-ENT-001",
                    "CAP-ENT-002",
                    "CAP-AUD-002",
                ),
                component_keywords=("digital_twin", "scorecard"),
                path_keywords=("digital_twin",),
                dashboard_keywords=("ExecutiveDigitalTwin",),
                kpis=("platform_readiness", "certified_capabilities"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                ),
            ),
        ),
    )

    enterprise_knowledge = CapabilityDomain(
        domain_id="enterprise_knowledge",
        name="Enterprise Knowledge",
        description=(
            "Maintains the official documentation, architecture knowledge "
            "and traceability model."
        ),
        owner="Enterprise Knowledge",
        capabilities=(
            capability(
                "CAP-KNW-001",
                "enterprise_knowledge",
                "Master Book",
                "Maintains the official functional and operating reference.",
                "Enterprise Knowledge",
                criticality="critical",
                component_keywords=(
                    "masterbook_generator",
                    "master_book_generator",
                    "masterbook_builder",
                    "master_book_builder",
                    "masterbook_registry",
                    "master_book_registry",
                ),
                path_keywords=(
                    "masterbook_generator",
                    "master_book_generator",
                    "masterbook_builder",
                    "master_book_builder",
                ),
                report_keywords=("masterbook_status_report",),
                kpis=("documents_count", "documentation_coverage"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                    tests=False,
                ),
            ),
            capability(
                "CAP-KNW-002",
                "enterprise_knowledge",
                "Documentation Center",
                "Indexes and reports documentation coverage and quality.",
                "Enterprise Knowledge",
                criticality="critical",
                dependencies=("CAP-KNW-001",),
                component_keywords=("documentation_center",),
                path_keywords=("documentation_center",),
                api_keywords=("documentation-center",),
                dashboard_keywords=("DocumentationCenter",),
                report_keywords=("documentation_center",),
                kpis=(
                    "documentation_health",
                    "coverage",
                    "quality_issues",
                ),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-KNW-003",
                "enterprise_knowledge",
                "Architecture Decision Records",
                "Preserves major architectural decisions and rationale.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                component_keywords=("adr", "architecture_decision"),
                path_keywords=("adr",),
                kpis=("adr_count", "undocumented_decisions"),
                requirements=certification(
                    reporting=False,
                    api=False,
                    dashboard=False,
                    explainability=False,
                    tests=False,
                ),
            ),
            capability(
                "CAP-KNW-004",
                "enterprise_knowledge",
                "Knowledge Graph",
                "Links capabilities, code, APIs, dashboards and evidence.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                dependencies=("CAP-ENT-001", "CAP-ENT-002"),
                component_keywords=("knowledge_graph", "traceability"),
                path_keywords=("knowledge_graph", "traceability"),
                kpis=("traceability_links", "orphan_nodes"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                    explainability=False,
                ),
            ),
        ),
    )

    enterprise_architecture = CapabilityDomain(
        domain_id="enterprise_architecture",
        name="Enterprise Architecture",
        description=(
            "Inventories, maps and certifies the enterprise architecture."
        ),
        owner="Enterprise Architecture",
        capabilities=(
            capability(
                "CAP-ENT-001",
                "enterprise_architecture",
                "Enterprise Component Inventory",
                "Maintains the official inventory of technical components.",
                "Enterprise Architecture",
                criticality="high",
                component_keywords=("enterprise_component_inventory",),
                path_keywords=("enterprise/inventory",),
                report_keywords=("component_registry",),
                kpis=(
                    "components_count",
                    "parse_success_rate",
                    "classification_coverage",
                ),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-ENT-002",
                "enterprise_architecture",
                "Capability Registry",
                "Maps business capabilities to technical implementation.",
                "Enterprise Architecture",
                criticality="high",
                dependencies=("CAP-ENT-001",),
                component_keywords=("capability_registry",),
                path_keywords=("enterprise/capability",),
                report_keywords=("capability_registry",),
                kpis=(
                    "capabilities_count",
                    "mapped_components",
                    "unmapped_components",
                ),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-ENT-003",
                "enterprise_architecture",
                "Dependency Mapping",
                "Builds the dependency graph between platform components.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                dependencies=("CAP-ENT-001",),
                component_keywords=("dependency_graph",),
                path_keywords=("dependency",),
                kpis=("dependency_edges", "cycles", "orphan_components"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-ENT-004",
                "enterprise_architecture",
                "Producer Consumer Mapping",
                "Maps producers and consumers of platform artefacts.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                dependencies=("CAP-ENT-001",),
                component_keywords=("producer_consumer",),
                path_keywords=("traceability",),
                kpis=("mapped_assets", "orphan_assets"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-ENT-005",
                "enterprise_architecture",
                "Architecture Gap Analysis",
                "Detects gaps across code, APIs, dashboards and documentation.",
                "Enterprise Architecture",
                criticality="high",
                roadmap_phase="RC2",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                dependencies=(
                    "CAP-ENT-001",
                    "CAP-ENT-002",
                    "CAP-ENT-003",
                    "CAP-ENT-004",
                ),
                component_keywords=("gap_analyzer", "gap_analysis"),
                path_keywords=("gap_analysis", "gap_analyzer"),
                kpis=("blocking_gaps", "integration_debt"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
        ),
    )

    audit_certification = CapabilityDomain(
        domain_id="audit_certification",
        name="Audit and Certification",
        description="Provides formal certification evidence and Go/No-Go control.",
        owner="Audit and Certification",
        capabilities=(
            capability(
                "CAP-AUD-001",
                "audit_certification",
                "Capability Certification",
                "Certifies capabilities against Enterprise Capability Lifecycle.",
                "Audit and Certification",
                criticality="critical",
                dependencies=("CAP-ENT-002",),
                component_keywords=("capability_certification",),
                path_keywords=("certification",),
                report_keywords=("certification",),
                kpis=(
                    "certified_capabilities",
                    "blocked_capabilities",
                    "certification_coverage",
                ),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-AUD-002",
                "audit_certification",
                "Production Readiness Assessment",
                "Calculates consolidated production readiness.",
                "Audit and Certification",
                criticality="critical",
                dependencies=("CAP-AUD-001", "CAP-ENT-005"),
                component_keywords=(
                    "production_readiness",
                    "production_readiness_assessment",
                    "readiness_scorecard",
                ),
                path_keywords=(
                    "production_readiness",
                    "readiness_assessment",
                    "readiness_scorecard",
                ),
                report_keywords=(
                    "production_readiness_report",
                    "readiness_scorecard",
                ),
                kpis=("overall_readiness", "blocking_findings"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-AUD-003",
                "audit_certification",
                "End-to-End Audit",
                "Validates the complete decision and execution chain.",
                "Audit and Certification",
                criticality="critical",
                dependencies=(
                    "CAP-INT-006",
                    "CAP-PRT-001",
                    "CAP-RSK-001",
                    "CAP-GOV-001",
                    "CAP-EXE-001",
                    "CAP-RPT-001",
                ),
                component_keywords=("end_to_end_audit", "e2e_audit"),
                path_keywords=("end_to_end_audit", "e2e_audit"),
                report_keywords=("end_to_end",),
                kpis=("e2e_status", "blocking_failures"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-AUD-004",
                "audit_certification",
                "Go No-Go Governance",
                "Issues the formal release recommendation.",
                "Audit and Certification",
                criticality="critical",
                dependencies=("CAP-AUD-002", "CAP-AUD-003"),
                component_keywords=("go_no_go", "go_nogo"),
                path_keywords=("go_no_go",),
                report_keywords=("go_no_go",),
                kpis=("go_no_go_status", "open_blockers"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    dashboard=True,
                    explainability=False,
                ),
            ),
        ),
    )

    security = CapabilityDomain(
        domain_id="security",
        name="Security and Resilience",
        description="Protects access, secrets and platform continuity.",
        owner="Security",
        capabilities=(
            capability(
                "CAP-SEC-001",
                "security",
                "Access Security",
                "Controls authenticated and authorized access.",
                "Security",
                criticality="critical",
                component_keywords=("security", "authentication", "authorization"),
                path_keywords=("security",),
                api_keywords=("security",),
                kpis=("authentication_failures", "unauthorized_requests"),
                requirements=certification(
                    reporting=True,
                    api=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-SEC-002",
                "security",
                "Secrets Management",
                "Protects credentials and sensitive configuration.",
                "Security",
                criticality="critical",
                component_keywords=("secrets", "credentials"),
                path_keywords=("secrets",),
                kpis=("exposed_secrets", "secret_rotation_status"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
            capability(
                "CAP-SEC-003",
                "security",
                "Business Continuity",
                "Supports recovery from operational failure.",
                "Platform Operations",
                criticality="critical",
                roadmap_phase="POST_PRODUCTION",
                lifecycle_phase="architecture",
                target_status="implemented",
                target_maturity=4,
                component_keywords=("backup", "recovery", "continuity"),
                path_keywords=("backup", "recovery"),
                kpis=("recovery_time", "backup_status"),
                requirements=certification(
                    reporting=True,
                    explainability=False,
                ),
            ),
        ),
    )

    return (
        investment_intelligence,
        asset_management,
        portfolio_management,
        execution,
        risk,
        governance,
        operations,
        reporting,
        enterprise_knowledge,
        enterprise_architecture,
        audit_certification,
        security,
    )


def flatten_capabilities(
    domains: Iterable[CapabilityDomain],
) -> list[Capability]:
    return [
        capability_item
        for domain in domains
        for capability_item in domain.capabilities
    ]


def validate_catalog(
    domains: tuple[CapabilityDomain, ...],
) -> list[str]:
    errors: list[str] = []

    domain_ids = [domain.domain_id for domain in domains]
    duplicate_domains = [
        domain_id
        for domain_id, count in Counter(domain_ids).items()
        if count > 1
    ]
    for domain_id in duplicate_domains:
        errors.append(f"Duplicate domain ID: {domain_id}")

    capabilities = flatten_capabilities(domains)
    capability_ids = {
        capability_item.capability_id
        for capability_item in capabilities
    }

    duplicate_capability_ids = [
        capability_id
        for capability_id, count in Counter(
            item.capability_id for item in capabilities
        ).items()
        if count > 1
    ]
    for capability_id in duplicate_capability_ids:
        errors.append(f"Duplicate capability ID: {capability_id}")

    for domain in domains:
        if not domain.capabilities:
            errors.append(
                f"Domain has no capabilities: {domain.domain_id}"
            )

        for item in domain.capabilities:
            if item.domain_id != domain.domain_id:
                errors.append(
                    f"{item.capability_id}: domain mismatch "
                    f"{item.domain_id} != {domain.domain_id}"
                )

            if item.criticality not in VALID_CRITICALITIES:
                errors.append(
                    f"{item.capability_id}: invalid criticality "
                    f"{item.criticality}"
                )

            if item.roadmap_phase not in VALID_ROADMAP_PHASES:
                errors.append(
                    f"{item.capability_id}: invalid roadmap phase "
                    f"{item.roadmap_phase}"
                )

            if item.lifecycle_phase not in VALID_LIFECYCLE_PHASES:
                errors.append(
                    f"{item.capability_id}: invalid lifecycle phase "
                    f"{item.lifecycle_phase}"
                )

            if item.target_status not in VALID_STATUSES:
                errors.append(
                    f"{item.capability_id}: invalid target status "
                    f"{item.target_status}"
                )

            if item.target_maturity not in VALID_MATURITY_LEVELS:
                errors.append(
                    f"{item.capability_id}: invalid maturity "
                    f"{item.target_maturity}"
                )

            for dependency in item.dependencies:
                if dependency == item.capability_id:
                    errors.append(
                        f"{item.capability_id}: self dependency"
                    )
                elif dependency not in capability_ids:
                    errors.append(
                        f"{item.capability_id}: unknown dependency "
                        f"{dependency}"
                    )

    return sorted(set(errors))


def detect_dependency_cycles(
    capabilities: list[Capability],
) -> list[list[str]]:
    graph = {
        item.capability_id: list(item.dependencies)
        for item in capabilities
    }

    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        current_state = state.get(node, 0)

        if current_state == 1:
            if node in stack:
                index = stack.index(node)
                cycle = stack[index:] + [node]
                if cycle not in cycles:
                    cycles.append(cycle)
            return

        if current_state == 2:
            return

        state[node] = 1
        stack.append(node)

        for dependency in graph.get(node, []):
            visit(dependency)

        stack.pop()
        state[node] = 2

    for capability_id in sorted(graph):
        visit(capability_id)

    return cycles


def build_statistics(
    domains: tuple[CapabilityDomain, ...],
) -> dict[str, Any]:
    capabilities = flatten_capabilities(domains)

    by_domain = Counter(item.domain_id for item in capabilities)
    by_phase = Counter(item.roadmap_phase for item in capabilities)
    by_status = Counter(item.target_status for item in capabilities)
    by_criticality = Counter(item.criticality for item in capabilities)
    by_maturity = Counter(
        str(item.target_maturity)
        for item in capabilities
    )
    by_lifecycle = Counter(
        item.lifecycle_phase
        for item in capabilities
    )

    dependency_edges = sum(
        len(item.dependencies)
        for item in capabilities
    )

    api_required = sum(
        item.certification.api
        for item in capabilities
    )
    dashboard_required = sum(
        item.certification.dashboard
        for item in capabilities
    )
    reporting_required = sum(
        item.certification.reporting
        for item in capabilities
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "generated_utc": utc_now(),
        "domains_count": len(domains),
        "capabilities_count": len(capabilities),
        "dependency_edges": dependency_edges,
        "api_required_count": api_required,
        "dashboard_required_count": dashboard_required,
        "reporting_required_count": reporting_required,
        "by_domain": dict(sorted(by_domain.items())),
        "by_roadmap_phase": dict(sorted(by_phase.items())),
        "by_target_status": dict(sorted(by_status.items())),
        "by_criticality": dict(sorted(by_criticality.items())),
        "by_target_maturity": dict(
            sorted(by_maturity.items(), key=lambda item: int(item[0]))
        ),
        "by_lifecycle_phase": dict(sorted(by_lifecycle.items())),
    }


def build_report(
    domains: tuple[CapabilityDomain, ...],
    statistics: dict[str, Any],
    validation_errors: list[str],
    dependency_cycles: list[list[str]],
) -> str:
    capabilities = flatten_capabilities(domains)

    lines: list[str] = [
        "# Nova Star Capital — Enterprise Capability Catalog",
        "",
        f"- Catalog version: `{CATALOG_VERSION}`",
        f"- Generated UTC: `{statistics['generated_utc']}`",
        f"- Domains: **{statistics['domains_count']}**",
        f"- Capabilities: **{statistics['capabilities_count']}**",
        f"- Dependency edges: **{statistics['dependency_edges']}**",
        f"- Validation status: **{'HEALTHY' if not validation_errors and not dependency_cycles else 'WARNING'}**",
        "",
        "## Roadmap distribution",
        "",
        "| Phase | Capabilities |",
        "|---|---:|",
    ]

    for phase, count in statistics["by_roadmap_phase"].items():
        lines.append(f"| {phase} | {count} |")

    lines.extend(
        [
            "",
            "## Criticality distribution",
            "",
            "| Criticality | Capabilities |",
            "|---|---:|",
        ]
    )

    for criticality, count in statistics["by_criticality"].items():
        lines.append(f"| {criticality} | {count} |")

    lines.extend(["", "## Capability map", ""])

    for domain in domains:
        lines.extend(
            [
                f"### {domain.name}",
                "",
                domain.description,
                "",
                "| ID | Capability | Criticality | Roadmap | Target | Maturity |",
                "|---|---|---|---|---|---:|",
            ]
        )

        for item in domain.capabilities:
            lines.append(
                f"| `{item.capability_id}` "
                f"| {item.name} "
                f"| {item.criticality} "
                f"| {item.roadmap_phase} "
                f"| {item.target_status} "
                f"| {item.target_maturity} |"
            )

        lines.append("")

    lines.extend(
        [
            "## Certification requirements",
            "",
            "| Capability | API | Dashboard | Reporting | Tests | Observation |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )

    for item in capabilities:
        requirements = item.certification
        lines.append(
            f"| `{item.capability_id}` {item.name} "
            f"| {'Yes' if requirements.api else 'No'} "
            f"| {'Yes' if requirements.dashboard else 'No'} "
            f"| {'Yes' if requirements.reporting else 'No'} "
            f"| {'Yes' if requirements.tests else 'No'} "
            f"| {'Yes' if requirements.runtime_observation else 'No'} |"
        )

    lines.extend(["", "## Validation", ""])

    if not validation_errors and not dependency_cycles:
        lines.append("- Catalog validation: **PASS**")
        lines.append("- Dependency cycle detection: **PASS**")
    else:
        if validation_errors:
            lines.append("### Validation errors")
            lines.append("")
            for error in validation_errors:
                lines.append(f"- {error}")

        if dependency_cycles:
            lines.append("")
            lines.append("### Dependency cycles")
            lines.append("")
            for cycle in dependency_cycles:
                lines.append(f"- {' → '.join(cycle)}")

    lines.append("")
    return "\n".join(lines)


def generate_catalog(output_root: Path) -> dict[str, Any]:
    domains = build_catalog()
    capabilities = flatten_capabilities(domains)

    validation_errors = validate_catalog(domains)
    dependency_cycles = detect_dependency_cycles(capabilities)
    statistics = build_statistics(domains)

    status = (
        "healthy"
        if not validation_errors and not dependency_cycles
        else "warning"
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "generated_utc": utc_now(),
        "status": status,
        "validation_errors": validation_errors,
        "dependency_cycles": dependency_cycles,
        "principles": [
            "Capabilities are business-stable and code-independent.",
            "Technical components implement capabilities.",
            "Production is a consequence of certification.",
            "Explain before execute.",
            "No critical capability is complete without traceability.",
            "Dashboard data must originate from identifiable backend artefacts.",
        ],
        "maturity_model": {
            "0": "Concept",
            "1": "Prototype",
            "2": "Implemented",
            "3": "Integrated",
            "4": "Certified",
            "5": "Production Ready",
            "6": "Institutional",
        },
        "enterprise_capability_lifecycle": [
            "ideation",
            "architecture",
            "implementation",
            "integration",
            "explainability",
            "documentation",
            "certification",
            "observation",
            "production",
            "evolution",
        ],
        "domains_count": len(domains),
        "capabilities_count": len(capabilities),
        "domains": [
            domain.to_dict()
            for domain in domains
        ],
    }

    report = build_report(
        domains=domains,
        statistics=statistics,
        validation_errors=validation_errors,
        dependency_cycles=dependency_cycles,
    )

    output_root.mkdir(parents=True, exist_ok=True)

    catalog_path = output_root / "capability_catalog.json"
    statistics_path = (
        output_root / "capability_catalog_statistics.json"
    )
    report_path = output_root / "CAPABILITY_CATALOG_REPORT.md"

    atomic_write_json(catalog_path, payload)
    atomic_write_json(statistics_path, statistics)
    atomic_write_text(report_path, report)

    return {
        "status": status,
        "domains_count": len(domains),
        "capabilities_count": len(capabilities),
        "validation_errors": validation_errors,
        "dependency_cycles": dependency_cycles,
        "catalog_path": str(catalog_path),
        "statistics_path": str(statistics_path),
        "report_path": str(report_path),
        "statistics": statistics,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the NSC Enterprise Capability Catalog."
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when validation issues are detected.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
    )
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> int:
    args = parse_arguments()
    configure_logging(args.verbose)

    result = generate_catalog(
        Path(args.output_root).resolve()
    )

    print()
    print("===== NSC ENTERPRISE CAPABILITY CATALOG =====")
    print(f"Status: {result['status']}")
    print(f"Domains: {result['domains_count']}")
    print(f"Capabilities: {result['capabilities_count']}")
    print(
        "Dependency edges: "
        f"{result['statistics']['dependency_edges']}"
    )
    print(
        "Validation errors: "
        f"{len(result['validation_errors'])}"
    )
    print(
        "Dependency cycles: "
        f"{len(result['dependency_cycles'])}"
    )
    print()
    print("Artefacts:")
    print(f"- {result['catalog_path']}")
    print(f"- {result['statistics_path']}")
    print(f"- {result['report_path']}")

    if result["validation_errors"]:
        print()
        print("Validation errors:")
        for error in result["validation_errors"]:
            print(f"- {error}")

    if result["dependency_cycles"]:
        print()
        print("Dependency cycles:")
        for cycle in result["dependency_cycles"]:
            print("- " + " -> ".join(cycle))

    if (
        args.strict
        and (
            result["validation_errors"]
            or result["dependency_cycles"]
        )
    ):
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
