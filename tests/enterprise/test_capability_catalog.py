from src.v2.enterprise.capability.capability_catalog import (
    build_catalog,
    detect_dependency_cycles,
    flatten_capabilities,
    validate_catalog,
)


def test_catalog_is_valid() -> None:
    domains = build_catalog()
    assert validate_catalog(domains) == []


def test_catalog_has_no_dependency_cycles() -> None:
    domains = build_catalog()
    capabilities = flatten_capabilities(domains)
    assert detect_dependency_cycles(capabilities) == []


def test_capability_ids_are_unique() -> None:
    domains = build_catalog()
    capabilities = flatten_capabilities(domains)
    ids = [capability.capability_id for capability in capabilities]
    assert len(ids) == len(set(ids))


def test_expected_enterprise_capabilities_exist() -> None:
    domains = build_catalog()
    capabilities = flatten_capabilities(domains)
    ids = {capability.capability_id for capability in capabilities}

    assert "CAP-ENT-001" in ids
    assert "CAP-ENT-002" in ids
    assert "CAP-KNW-004" in ids
    assert "CAP-AUD-001" in ids
