import json
from pathlib import Path

from src.v2.enterprise.capability.capability_catalog import (
    build_catalog,
)
from src.v2.enterprise.capability.capability_registry import (
    flatten_capabilities,
    match_component,
    normalize_text,
    observed_status,
)


def sample_capability(**overrides):
    payload = {
        "capability_id": "CAP-TEST-001",
        "domain_id": "investment_intelligence",
        "name": "Market Discovery",
        "description": "Test capability",
        "owner": "Market Intelligence",
        "criticality": "critical",
        "roadmap_phase": "RC1",
        "lifecycle_phase": "certification",
        "target_status": "production_ready",
        "target_maturity": 5,
        "dependencies": [],
        "component_keywords": [
            "market_discovery",
            "discovery_engine",
        ],
        "path_keywords": ["discovery"],
        "api_keywords": ["discovery"],
        "dashboard_keywords": ["TopMovers"],
        "report_keywords": ["discovery"],
        "documentation_keywords": [],
    }
    payload.update(overrides)
    return payload


def sample_component(**overrides):
    payload = {
        "component_id": "TEST-ENG-001",
        "stable_key": (
            "discovery:engine:"
            "src/v2/discovery/market_discovery_engine.py"
        ),
        "name": "market_discovery_engine",
        "display_name": "Market Discovery Engine",
        "domain": "discovery",
        "component_type": "engine",
        "subtype": "python_engine",
        "path": (
            "src/v2/discovery/"
            "market_discovery_engine.py"
        ),
        "language": "python",
        "extension": ".py",
        "owner": "Market Intelligence",
        "status": "detected",
        "maturity": "detected",
        "criticality": "standard",
        "route_count": 0,
        "is_package_initializer": False,
    }
    payload.update(overrides)
    return payload


def test_normalize_text_handles_camel_case():
    assert normalize_text("TopMovers") == "top_movers"


def test_catalog_flattens_to_65_capabilities():
    domains = build_catalog()
    payload = {
        "domains": [
            domain.to_dict()
            for domain in domains
        ]
    }

    capabilities = flatten_capabilities(payload)

    assert len(capabilities) == 65


def test_exact_component_match():
    match = match_component(
        sample_capability(),
        sample_component(),
    )

    assert match is not None
    assert match["strength"] == "EXACT"
    assert match["score"] >= 0.60
    assert match["evidence_role"] == "CORE"
    assert match["active_component"] is True
    assert (
        match["primary_implementation_evidence"]
        is True
    )


def test_generic_path_signal_does_not_become_strong():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=["discovery"],
        api_keywords=[],
        dashboard_keywords=[],
        report_keywords=[],
    )
    component = sample_component(
        name="unrelated_runner",
        display_name="Unrelated Runner",
        path="src/v2/discovery/unrelated_runner.py",
        component_type="runner",
    )

    match = match_component(
        capability,
        component,
    )

    assert match is not None
    assert match["strength"] == "WEAK"


def test_package_initializer_is_ignored():
    match = match_component(
        sample_capability(),
        sample_component(
            name="__init__",
            path="src/v2/discovery/__init__.py",
            is_package_initializer=True,
        ),
    )

    assert match is None


def test_dashboard_keyword_requires_dashboard_component():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=[],
        api_keywords=[],
        dashboard_keywords=["TopMovers"],
        report_keywords=[],
    )

    non_dashboard = sample_component(
        name="TopMovers",
        path="src/v2/tools/TopMovers.py",
        component_type="utility",
    )

    dashboard = sample_component(
        name="TopMovers",
        path=(
            "src/v2/interface/react/src/pages/"
            "TopMovers.jsx"
        ),
        domain="interface",
        language="javascript",
        extension=".jsx",
        component_type="react_page",
        subtype="react_page",
    )

    assert match_component(
        capability,
        non_dashboard,
    ) is None

    match = match_component(
        capability,
        dashboard,
    )

    assert match is not None
    assert match["strength"] == "EXACT"
    assert match["evidence_role"] == "PRESENTATION"
    assert (
        match["primary_implementation_evidence"]
        is False
    )


def test_no_match_produces_no_evidence():
    assert observed_status([]) == "no_evidence"


def test_weak_match_produces_weak_status():
    assert observed_status(
        [{"strength": "WEAK"}]
    ) == "weak_evidence_only"


def test_generated_registry_sources_exist():
    root = Path(
        "/opt/nsc/data/preprod/enterprise"
    )

    assert (
        root / "capability_catalog.json"
    ).exists()
    assert (
        root / "component_registry.json"
    ).exists()

    catalog = json.loads(
        (
            root / "capability_catalog.json"
        ).read_text(encoding="utf-8")
    )
    registry = json.loads(
        (
            root / "component_registry.json"
        ).read_text(encoding="utf-8")
    )

    assert catalog["capabilities_count"] == 65
    assert registry["components_count"] > 0



def test_exact_core_match_produces_implementation_status():
    match = match_component(
        sample_capability(),
        sample_component(),
    )

    assert match is not None

    assert observed_status(
        [match]
    ) == "exact_implementation_evidence"


def test_dashboard_is_not_primary_implementation_evidence():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=[],
        api_keywords=[],
        dashboard_keywords=["TopMovers"],
        report_keywords=[],
    )

    dashboard = sample_component(
        name="TopMovers",
        display_name="Top Movers",
        path=(
            "src/v2/interface/react/src/pages/"
            "TopMovers.jsx"
        ),
        domain="interface",
        language="javascript",
        extension=".jsx",
        component_type="react_page",
        subtype="dashboard",
    )

    match = match_component(
        capability,
        dashboard,
    )

    assert match is not None
    assert match["evidence_role"] == "PRESENTATION"
    assert match["primary_implementation_evidence"] is False
    assert observed_status(
        [match]
    ) == "presentation_evidence_only"


def test_api_router_is_not_primary_implementation_evidence():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=[],
        api_keywords=["discovery"],
        dashboard_keywords=[],
        report_keywords=[],
    )

    router = sample_component(
        name="discovery",
        display_name="Discovery",
        path="src/v2/api/routes/discovery.py",
        domain="api",
        component_type="router",
        subtype="fastapi",
        route_count=1,
    )

    match = match_component(
        capability,
        router,
    )

    assert match is not None
    assert match["evidence_role"] == "API_EXPOSURE"
    assert match["primary_implementation_evidence"] is False
    assert observed_status(
        [match]
    ) == "api_exposure_evidence_only"


def test_audit_component_is_not_primary_implementation_evidence():
    capability = sample_capability(
        component_keywords=["end_to_end_audit"],
        path_keywords=[],
        api_keywords=[],
        dashboard_keywords=[],
        report_keywords=[],
    )

    audit = sample_component(
        name="end_to_end_audit",
        display_name="End To End Audit",
        path="src/v2/audits/end_to_end_audit.py",
        domain="audit",
        component_type="audit",
        subtype="audit",
    )

    match = match_component(
        capability,
        audit,
    )

    assert match is not None
    assert match["evidence_role"] == "AUDIT"
    assert match["primary_implementation_evidence"] is False
    assert observed_status(
        [match]
    ) == "audit_evidence_only"


def test_disabled_component_is_never_primary():
    component = sample_component(
        path=(
            "src/v2/options.disabled/"
            "market_discovery_engine.py"
        ),
    )

    match = match_component(
        sample_capability(),
        component,
    )

    assert match is not None
    assert match["evidence_role"] == "INACTIVE"
    assert match["active_component"] is False
    assert match["primary_implementation_evidence"] is False


def test_backup_component_is_never_primary():
    component = sample_component(
        path=(
            "src/v2/discovery/"
            "market_discovery_engine.py"
            ".bak_exact_token_20260723"
        ),
    )

    match = match_component(
        sample_capability(),
        component,
    )

    assert match is not None
    assert match["evidence_role"] == "INACTIVE"
    assert match["primary_implementation_evidence"] is False


def test_builder_is_not_automatically_a_report():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=[],
        api_keywords=[],
        dashboard_keywords=[],
        report_keywords=["discovery"],
    )

    builder = sample_component(
        name="discovery_plan_builder",
        display_name="Discovery Plan Builder",
        path=(
            "src/v2/discovery/"
            "discovery_plan_builder.py"
        ),
        component_type="builder",
        subtype="builder",
    )

    assert match_component(
        capability,
        builder,
    ) is None


def test_single_non_generic_path_phrase_is_not_strong():
    capability = sample_capability(
        component_keywords=[],
        path_keywords=["market_discovery"],
        api_keywords=[],
        dashboard_keywords=[],
        report_keywords=[],
    )

    component = sample_component(
        name="unrelated_runner",
        display_name="Unrelated Runner",
        path=(
            "src/v2/market_discovery/"
            "unrelated_runner.py"
        ),
        component_type="runner",
    )

    match = match_component(
        capability,
        component,
    )

    assert match is not None
    assert match["strength"] == "WEAK"
    assert match["primary_implementation_evidence"] is False
