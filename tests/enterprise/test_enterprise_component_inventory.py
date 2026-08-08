from pathlib import Path

from src.v2.enterprise.inventory.enterprise_component_inventory import (
    detect_maturity,
    should_ignore_path,
)


def test_stub_engine_is_prototype() -> None:
    path = Path("/opt/nsc/app/src/v2/portfolio/portfolio_engine_stub.py")
    assert detect_maturity(path, "engine", "def run(): pass") == "prototype"


def test_regular_engine_is_implemented() -> None:
    path = Path("/opt/nsc/app/src/v2/risk/risk_engine.py")
    assert detect_maturity(path, "engine", "def calculate_risk(): pass") == "implemented"


def test_explicit_placeholder_backend_is_prototype() -> None:
    path = Path("/opt/nsc/app/src/v2/reporting/daily_report.py")
    content = '"""Daily report placeholder / base."""'
    assert detect_maturity(path, "report", content) == "prototype"


def test_html_placeholder_does_not_degrade_react_component() -> None:
    path = Path("/opt/nsc/app/src/v2/interface/react/src/pages/Search.jsx")
    content = '<input placeholder="Search..." />'
    assert detect_maturity(path, "react_page", content) == "detected"


def test_shadow_mode_is_shadow() -> None:
    path = Path("/opt/nsc/app/src/v2/options/options_engine.py")
    content = 'MODE = "shadow mode"'
    assert detect_maturity(path, "engine", content) == "shadow"


def test_deprecated_source_is_deprecated() -> None:
    path = Path("/opt/nsc/app/src/v2/api/old_router.py")
    content = '"""Deprecated endpoint retained for compatibility."""'
    assert detect_maturity(path, "router", content) == "deprecated"


def test_node_modules_is_ignored() -> None:
    path = Path(
        "/opt/nsc/app/src/v2/interface/react/node_modules/react/index.js"
    )
    assert should_ignore_path(path)


def test_backup_file_is_ignored() -> None:
    path = Path(
        "/opt/nsc/app/src/v2/portfolio/"
        "portfolio_engine.py.bak_20260722"
    )
    assert should_ignore_path(path)


def test_catalog_status_vocabulary_does_not_mark_module_deprecated() -> None:
    path = Path(
        "/opt/nsc/app/src/v2/enterprise/capability/"
        "capability_catalog.py"
    )
    content = '''
VALID_STATUSES = {
    "implemented",
    "deprecated",
    "archived",
}
'''
    assert detect_maturity(path, "registry", content) == "detected"


def test_explicit_deprecated_module_is_deprecated() -> None:
    path = Path("/opt/nsc/app/src/v2/api/old_router.py")
    content = '"""This module is deprecated. Use new_router."""'
    assert detect_maturity(path, "router", content) == "deprecated"


def test_root_enterprise_test_is_detected() -> None:
    from src.v2.enterprise.inventory.enterprise_component_inventory import (
        nearby_tests_exist,
    )

    path = Path(
        "/opt/nsc/app/src/v2/enterprise/inventory/"
        "enterprise_component_inventory.py"
    )
    assert nearby_tests_exist(path)


def test_nsc_deprecated_legacy_wrapper_is_deprecated() -> None:
    path = Path(
        "/opt/nsc/app/src/v2/trading/capital_allocator.py"
    )
    content = '''
"""
DEPRECATED / LEGACY.
Ce module est conservé pour compat et redirige vers
l'implémentation officielle.
"""
'''
    assert detect_maturity(
        path,
        "runner",
        content,
    ) == "deprecated"
