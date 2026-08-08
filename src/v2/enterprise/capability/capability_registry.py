from __future__ import annotations

"""
Nova Star Capital
Capability Registry & Component-to-Capability Mapper V1

This module maps the official Enterprise Capability Catalog to the
Enterprise Component Inventory.

Design principles
-----------------
- A keyword match is evidence, not proof of implementation.
- Generic substring matches must never produce strong evidence alone.
- Target status and observed repository evidence remain separate.
- Mapping is deterministic and explainable.
- Weak evidence is retained for investigation but excluded from primary
  implementation evidence.
"""

import argparse
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


APP_ROOT = Path("/opt/nsc/app")
DEFAULT_INPUT_ROOT = Path("/opt/nsc/data/preprod/enterprise")
DEFAULT_OUTPUT_ROOT = Path("/opt/nsc/data/preprod/enterprise")

SCHEMA_VERSION = "1.0"
MAPPER_VERSION = "1.1.1"

LOGGER = logging.getLogger("nsc.enterprise.capability.registry")


GENERIC_KEYWORDS = {
    "api",
    "audit",
    "capital",
    "cash",
    "control",
    "crypto",
    "dashboard",
    "data",
    "decision",
    "discovery",
    "engine",
    "execution",
    "fill",
    "gold",
    "governance",
    "ibkr",
    "market",
    "mexc",
    "monitoring",
    "options",
    "order",
    "pnl",
    "portfolio",
    "report",
    "reporting",
    "risk",
    "security",
    "signal",
    "strategy",
    "system",
    "validation",
    "veto",
}


EVIDENCE_WEIGHTS = {
    "exact_component_name": 0.72,
    "exact_component_display_name": 0.68,
    "exact_component_keyword_token": 0.48,
    "exact_path_segment": 0.42,
    "exact_path_phrase": 0.36,
    "exact_api_component": 0.55,
    "exact_dashboard_component": 0.60,
    "exact_report_component": 0.50,
    "exact_documentation_component": 0.50,
    "domain_coherence": 0.10,
    "owner_coherence": 0.05,
    "generic_component_token": 0.10,
    "generic_path_token": 0.06,
}


PRIMARY_STRENGTHS = {"EXACT", "STRONG"}

EVIDENCE_ROLES = {
    "CORE",
    "SUPPORTING",
    "API_EXPOSURE",
    "PRESENTATION",
    "AUDIT",
    "DOCUMENTATION",
    "TEST",
    "INACTIVE",
}

CORE_COMPONENT_TYPES = {
    "engine",
    "controller",
    "manager",
    "orchestrator",
    "processor",
    "kernel",
    "service",
    "strategy",
    "adapter",
    "allocator",
    "validator",
}

SUPPORTING_COMPONENT_TYPES = {
    "builder",
    "generator",
    "registry",
    "module",
    "runner",
    "utility",
    "config",
    "model",
    "repository",
    "client",
}

NON_IMPLEMENTATION_COMPONENT_TYPES = {
    "report",
    "audit",
    "documentation",
    "react_page",
    "react_component",
    "test",
}


NON_PRODUCTION_IMPLEMENTATION_MARKERS = {
    "simulated",
    "simulation",
    "shadow",
    "mock",
    "stub",
    "fake",
    "dry_run",
    "dryrun",
    "sandbox",
}


SUPPORTING_PRIMARY_IDENTITY_TYPES = {
    "exact_component_name",
    "exact_component_display_name",
    "exact_component_keyword_token",
}


INACTIVE_PATH_MARKERS = {
    "_old",
    "old",
    "disabled",
    "_disabled",
    "deprecated",
    "archive",
    "archived",
    "backup",
    "backups",
    "bak",
}

TEST_PATH_MARKERS = {
    "test",
    "tests",
    "testing",
}

EXAMPLE_PATH_MARKERS = {
    "example",
    "examples",
    "sample",
    "samples",
    "demo",
    "demos",
}


def component_path_tokens(
    component: dict[str, Any],
) -> set[str]:
    path = str(component.get("path", ""))
    normalized = normalize_text(path)
    tokens = set(tokenize(path))

    if ".disabled" in path.lower():
        tokens.add("disabled")

    if ".bak_" in path.lower():
        tokens.add("bak")

    if "_bak_" in path.lower():
        tokens.add("bak")

    if "._old" in path.lower():
        tokens.add("_old")

    if "_old/" in path.lower():
        tokens.add("_old")

    if normalized:
        tokens.add(normalized)

    return tokens


def component_is_inactive(
    component: dict[str, Any],
) -> bool:
    path = str(component.get("path", "")).lower()
    name = str(component.get("name", "")).lower()
    status = str(component.get("status", "")).lower()
    maturity = str(component.get("maturity", "")).lower()
    tokens = component_path_tokens(component)

    explicit_markers = (
        ".disabled",
        "_disabled",
        "._old",
        "_old/",
        "/_old/",
        "_bak_",
        ".bak_",
        "/backup/",
        "/backups/",
        "/archive/",
        "/archived/",
    )

    return (
        any(marker in path for marker in explicit_markers)
        or any(marker in name for marker in {
            "_disabled",
            "_deprecated",
            "_old",
            "_backup",
        })
        or bool(tokens & INACTIVE_PATH_MARKERS)
        or status in {
            "disabled",
            "inactive",
            "deprecated",
            "archived",
        }
        or maturity in {
            "disabled",
            "inactive",
            "archived",
        }
    )


def classify_evidence_role(
    component: dict[str, Any],
) -> str:
    if component_is_inactive(component):
        return "INACTIVE"

    component_type = str(
        component.get("component_type", "")
    ).lower()
    subtype = str(component.get("subtype", "")).lower()
    domain = str(component.get("domain", "")).lower()
    extension = str(component.get("extension", "")).lower()
    path = str(component.get("path", "")).lower()
    name = str(component.get("name", "")).lower()
    tokens = component_path_tokens(component)

    if (
        bool(tokens & TEST_PATH_MARKERS)
        or name.startswith("test_")
        or name.endswith("_test")
        or "/tests/" in path
    ):
        return "TEST"

    if (
        bool(tokens & EXAMPLE_PATH_MARKERS)
        or name.endswith("_example")
        or name.startswith("example_")
    ):
        return "INACTIVE"

    if component_type in {
        "react_page",
        "react_component",
    }:
        return "PRESENTATION"

    if (
        component_type == "router"
        or subtype == "fastapi"
        or domain == "api"
        or int(component.get("route_count", 0) or 0) > 0
    ):
        return "API_EXPOSURE"

    if (
        component_type == "audit"
        or subtype == "audit"
        or domain == "audit"
        or "/audits/" in path
    ):
        return "AUDIT"

    if (
        domain == "documentation"
        or extension in {".md", ".rst", ".txt"}
        or component_type == "documentation"
    ):
        return "DOCUMENTATION"

    if component_type in CORE_COMPONENT_TYPES:
        return "CORE"

    if component_type in SUPPORTING_COMPONENT_TYPES:
        return "SUPPORTING"

    return "SUPPORTING"


def is_primary_implementation_evidence(
    strength: str,
    evidence_role: str,
    active_component: bool,
    component: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> bool:
    """
    Return whether a match represents primary implementation evidence.

    Reports, presentation, audit and documentation remain valid evidence,
    but they cannot certify the underlying implementation.

    Simulated, shadow, mock and sandbox components cannot represent
    production implementation evidence.
    """
    if not active_component:
        return False

    component_type = str(
        component.get("component_type", "")
    ).lower()
    subtype = str(component.get("subtype", "")).lower()
    name = str(component.get("name", "")).lower()
    path = str(component.get("path", "")).lower()

    if (
        component_type in NON_IMPLEMENTATION_COMPONENT_TYPES
        or subtype in NON_IMPLEMENTATION_COMPONENT_TYPES
    ):
        return False

    semantic_identity = f"{name} {path}"

    if any(
        marker in semantic_identity
        for marker in NON_PRODUCTION_IMPLEMENTATION_MARKERS
    ):
        return False

    if evidence_role == "CORE":
        return strength in PRIMARY_STRENGTHS

    if evidence_role != "SUPPORTING":
        return False

    if strength != "EXACT":
        return False

    evidence_types = {
        str(item.get("evidence_type", ""))
        for item in evidence
    }

    return bool(
        evidence_types
        & SUPPORTING_PRIMARY_IDENTITY_TYPES
    )


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


def normalize_text(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(value))
    value = value.replace("-", "_")
    value = value.replace(".", "_")
    value = value.replace("/", "_")
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def tokenize(value: str) -> tuple[str, ...]:
    normalized = normalize_text(value)
    if not normalized:
        return ()
    return tuple(
        token
        for token in normalized.split("_")
        if token
    )


def normalized_phrase(value: str) -> str:
    return "_".join(tokenize(value))


def path_segments(value: str) -> tuple[str, ...]:
    return tuple(
        normalize_text(part)
        for part in Path(value).parts
        if normalize_text(part)
    )


def flatten_capabilities(
    catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        capability
        for domain in catalog.get("domains", [])
        for capability in domain.get("capabilities", [])
    ]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_generic(keyword: str) -> bool:
    normalized = normalized_phrase(keyword)
    tokens = tokenize(keyword)

    return (
        normalized in GENERIC_KEYWORDS
        or len(normalized) <= 4
        or (
            len(tokens) == 1
            and tokens[0] in GENERIC_KEYWORDS
        )
    )


def phrase_in_tokens(
    phrase_tokens: tuple[str, ...],
    target_tokens: tuple[str, ...],
) -> bool:
    if not phrase_tokens or not target_tokens:
        return False

    length = len(phrase_tokens)

    return any(
        target_tokens[index:index + length] == phrase_tokens
        for index in range(len(target_tokens) - length + 1)
    )


def expected_component_context(
    keyword_field: str,
    component: dict[str, Any],
) -> bool:
    component_type = component.get("component_type")
    subtype = component.get("subtype")
    domain = component.get("domain")
    extension = component.get("extension")

    if keyword_field == "api_keywords":
        return (
            domain == "api"
            or component_type == "router"
            or component.get("route_count", 0) > 0
        )

    if keyword_field == "dashboard_keywords":
        return component_type in {
            "react_page",
            "react_component",
        }

    if keyword_field == "report_keywords":
        return (
            component_type == "report"
            or domain == "reporting"
            or subtype in {
                "report",
                "report_builder",
                "report_generator",
            }
        )

    if keyword_field == "documentation_keywords":
        return (
            domain == "documentation"
            or extension in {".md", ".rst", ".txt"}
        )

    return True


def domain_is_coherent(
    capability: dict[str, Any],
    component: dict[str, Any],
) -> bool:
    capability_domain = capability.get("domain_id", "")
    component_domain = component.get("domain", "")

    aliases = {
        "investment_intelligence": {
            "discovery",
            "sentiment",
            "analysis",
            "signals",
            "market",
        },
        "asset_management": {
            "crypto",
            "offensive_equities",
            "defensive_equities",
            "bonds",
            "precious_metals",
            "options",
            "long_term",
        },
        "portfolio_management": {
            "portfolio",
            "capital",
            "funding",
            "treasury",
        },
        "execution": {
            "execution",
            "trading",
            "broker",
        },
        "risk_management": {
            "risk",
            "governance",
        },
        "governance": {
            "governance",
            "risk",
            "audit",
        },
        "operations": {
            "monitoring",
            "platform",
            "preprod",
            "operations",
        },
        "reporting": {
            "reporting",
            "interface",
            "api",
        },
        "enterprise_knowledge": {
            "documentation",
            "enterprise",
        },
        "enterprise_architecture": {
            "enterprise",
            "audit",
            "tooling",
        },
        "audit_certification": {
            "audit",
            "governance",
            "preprod",
        },
        "security": {
            "security",
            "platform",
            "api",
        },
    }

    return component_domain in aliases.get(capability_domain, set())


def owner_is_coherent(
    capability: dict[str, Any],
    component: dict[str, Any],
) -> bool:
    capability_tokens = set(tokenize(capability.get("owner", "")))
    component_tokens = set(tokenize(component.get("owner", "")))

    meaningful = {
        token
        for token in capability_tokens
        if len(token) > 3
    }

    return bool(meaningful & component_tokens)


def add_evidence(
    evidence: list[dict[str, Any]],
    evidence_type: str,
    *,
    keyword_field: str | None = None,
    keyword: str | None = None,
    matched_value: str | None = None,
) -> None:
    item = {
        "evidence_type": evidence_type,
        "weight": EVIDENCE_WEIGHTS[evidence_type],
    }

    if keyword_field is not None:
        item["keyword_field"] = keyword_field
    if keyword is not None:
        item["keyword"] = keyword
    if matched_value is not None:
        item["matched_value"] = matched_value

    signature = (
        item.get("evidence_type"),
        item.get("keyword_field"),
        item.get("keyword"),
        item.get("matched_value"),
    )

    existing = {
        (
            current.get("evidence_type"),
            current.get("keyword_field"),
            current.get("keyword"),
            current.get("matched_value"),
        )
        for current in evidence
    }

    if signature not in existing:
        evidence.append(item)


def match_component(
    capability: dict[str, Any],
    component: dict[str, Any],
) -> dict[str, Any] | None:
    if component.get("is_package_initializer"):
        return None

    name = normalized_phrase(component.get("name", ""))
    display_name = normalized_phrase(
        component.get("display_name", "")
    )
    path = component.get("path", "")
    path_phrase = normalized_phrase(path)
    basename = normalized_phrase(Path(path).stem)
    segments = path_segments(path)

    name_tokens = tokenize(component.get("name", ""))
    display_tokens = tokenize(component.get("display_name", ""))
    path_tokens = tokenize(path)

    evidence: list[dict[str, Any]] = []

    fields = (
        "component_keywords",
        "path_keywords",
        "api_keywords",
        "dashboard_keywords",
        "report_keywords",
        "documentation_keywords",
    )

    for keyword_field in fields:
        if not expected_component_context(keyword_field, component):
            continue

        for raw_keyword in capability.get(keyword_field, []):
            keyword = normalized_phrase(raw_keyword)

            if not keyword:
                continue

            keyword_tokens = tokenize(raw_keyword)
            generic = is_generic(raw_keyword)

            exact_name = keyword in {
                name,
                basename,
            }
            exact_display = keyword == display_name
            in_name_tokens = phrase_in_tokens(
                keyword_tokens,
                name_tokens,
            )
            in_display_tokens = phrase_in_tokens(
                keyword_tokens,
                display_tokens,
            )
            in_path_tokens = phrase_in_tokens(
                keyword_tokens,
                path_tokens,
            )
            exact_segment = keyword in segments

            if keyword_field == "component_keywords":
                if exact_name:
                    add_evidence(
                        evidence,
                        "exact_component_name",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=component.get("name"),
                    )
                elif exact_display:
                    add_evidence(
                        evidence,
                        "exact_component_display_name",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=component.get(
                            "display_name"
                        ),
                    )
                elif in_name_tokens or in_display_tokens:
                    add_evidence(
                        evidence,
                        (
                            "generic_component_token"
                            if generic
                            else "exact_component_keyword_token"
                        ),
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=component.get("name"),
                    )

            elif keyword_field == "path_keywords":
                if exact_segment:
                    add_evidence(
                        evidence,
                        (
                            "generic_path_token"
                            if generic
                            else "exact_path_segment"
                        ),
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )
                elif in_path_tokens and not generic:
                    add_evidence(
                        evidence,
                        "exact_path_phrase",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )

            elif keyword_field == "api_keywords":
                if (
                    keyword in {name, basename}
                    or in_name_tokens
                    or exact_segment
                ):
                    add_evidence(
                        evidence,
                        "exact_api_component",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )

            elif keyword_field == "dashboard_keywords":
                if keyword in {
                    name,
                    basename,
                    display_name,
                }:
                    add_evidence(
                        evidence,
                        "exact_dashboard_component",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )

            elif keyword_field == "report_keywords":
                if (
                    keyword in {name, basename}
                    or in_name_tokens
                    or exact_segment
                ):
                    add_evidence(
                        evidence,
                        "exact_report_component",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )

            elif keyword_field == "documentation_keywords":
                if (
                    keyword in {name, basename}
                    or in_name_tokens
                    or exact_segment
                ):
                    add_evidence(
                        evidence,
                        "exact_documentation_component",
                        keyword_field=keyword_field,
                        keyword=raw_keyword,
                        matched_value=path,
                    )

    substantive_evidence = [
        item
        for item in evidence
        if item["evidence_type"] not in {
            "domain_coherence",
            "owner_coherence",
        }
    ]

    if not substantive_evidence:
        return None

    if domain_is_coherent(capability, component):
        add_evidence(
            evidence,
            "domain_coherence",
            matched_value=component.get("domain"),
        )

    if owner_is_coherent(capability, component):
        add_evidence(
            evidence,
            "owner_coherence",
            matched_value=component.get("owner"),
        )

    score = round(
        min(
            1.0,
            sum(item["weight"] for item in evidence),
        ),
        4,
    )

    evidence_types = {
        item["evidence_type"]
        for item in substantive_evidence
    }
    evidence_fields = {
        item.get("keyword_field")
        for item in substantive_evidence
        if item.get("keyword_field")
    }

    has_exact_identity = bool(
        evidence_types
        & {
            "exact_component_name",
            "exact_component_display_name",
            "exact_component_keyword_token",
            "exact_api_component",
            "exact_dashboard_component",
            "exact_report_component",
            "exact_documentation_component",
        }
    )

    has_only_generic = evidence_types <= {
        "generic_component_token",
        "generic_path_token",
    }

    if has_exact_identity and score >= 0.60:
        strength = "EXACT"
    elif (
        score >= 0.48
        and len(evidence_fields) >= 2
        and not has_only_generic
    ):
        strength = "STRONG"
    else:
        strength = "WEAK"

    evidence_role = classify_evidence_role(component)
    active_component = evidence_role != "INACTIVE"
    primary_implementation_evidence = (
        is_primary_implementation_evidence(
            strength,
            evidence_role,
            active_component,
            component,
            evidence,
        )
    )

    return {
        "capability_id": capability["capability_id"],
        "component_id": component["component_id"],
        "component_path": component["path"],
        "component_name": component["name"],
        "component_type": component["component_type"],
        "component_subtype": component["subtype"],
        "component_domain": component["domain"],
        "component_maturity": component["maturity"],
        "component_status": component["status"],
        "evidence_role": evidence_role,
        "active_component": active_component,
        "primary_implementation_evidence": (
            primary_implementation_evidence
        ),
        "strength": strength,
        "score": score,
        "evidence_count": len(evidence),
        "evidence": sorted(
            evidence,
            key=lambda item: (
                -item["weight"],
                item["evidence_type"],
                str(item.get("keyword", "")),
            ),
        ),
    }


def observed_status(
    matches: list[dict[str, Any]],
) -> str:
    exact_primary = any(
        match.get("primary_implementation_evidence")
        and match["strength"] == "EXACT"
        for match in matches
    )

    strong_primary = any(
        match.get("primary_implementation_evidence")
        and match["strength"] == "STRONG"
        for match in matches
    )

    if exact_primary:
        return "exact_implementation_evidence"

    if strong_primary:
        return "strong_implementation_evidence"

    non_weak_roles = {
        match.get("evidence_role")
        for match in matches
        if match.get("strength") in PRIMARY_STRENGTHS
    }

    if "SUPPORTING" in non_weak_roles:
        return "supporting_evidence_only"

    if "PRESENTATION" in non_weak_roles:
        return "presentation_evidence_only"

    if "API_EXPOSURE" in non_weak_roles:
        return "api_exposure_evidence_only"

    if "AUDIT" in non_weak_roles:
        return "audit_evidence_only"

    if "DOCUMENTATION" in non_weak_roles:
        return "documentation_evidence_only"

    if "TEST" in non_weak_roles:
        return "test_evidence_only"

    if "INACTIVE" in non_weak_roles:
        return "inactive_evidence_only"

    if any(
        match.get("strength") == "WEAK"
        for match in matches
    ):
        return "weak_evidence_only"

    return "no_evidence"

def mapping_confidence(
    matches: list[dict[str, Any]],
) -> float:
    primary = [
        match["score"]
        for match in matches
        if match.get("primary_implementation_evidence")
    ]

    if not primary:
        return 0.0

    primary.sort(reverse=True)

    confidence = primary[0]

    if len(primary) > 1:
        confidence += min(
            0.18,
            sum(primary[1:4]) * 0.08,
        )

    return round(min(1.0, confidence), 4)


def build_mapping(
    catalog: dict[str, Any],
    registry: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    capabilities = flatten_capabilities(catalog)
    components = registry.get("components", [])

    matches_by_capability: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    matches_by_component: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for capability in capabilities:
        for component in components:
            match = match_component(
                capability,
                component,
            )

            if match is None:
                continue

            matches_by_capability[
                capability["capability_id"]
            ].append(match)

            matches_by_component[
                component["component_id"]
            ].append(match)

    capability_records: list[dict[str, Any]] = []

    for capability in capabilities:
        capability_id = capability["capability_id"]

        matches = sorted(
            matches_by_capability.get(capability_id, []),
            key=lambda item: (
                {
                    "EXACT": 0,
                    "STRONG": 1,
                    "WEAK": 2,
                }[item["strength"]],
                -item["score"],
                item["component_path"],
            ),
        )

        exact_count = sum(
            item["strength"] == "EXACT"
            for item in matches
        )
        strong_count = sum(
            item["strength"] == "STRONG"
            for item in matches
        )
        weak_count = sum(
            item["strength"] == "WEAK"
            for item in matches
        )

        primary_matches = [
            item
            for item in matches
            if item.get("primary_implementation_evidence")
        ]

        role_counts = Counter(
            item.get("evidence_role", "SUPPORTING")
            for item in matches
        )

        capability_records.append(
            {
                "capability_id": capability_id,
                "domain_id": capability["domain_id"],
                "name": capability["name"],
                "description": capability["description"],
                "owner": capability["owner"],
                "criticality": capability["criticality"],
                "roadmap_phase": capability[
                    "roadmap_phase"
                ],
                "lifecycle_phase": capability[
                    "lifecycle_phase"
                ],
                "target_status": capability[
                    "target_status"
                ],
                "target_maturity": capability[
                    "target_maturity"
                ],
                "dependencies": capability.get(
                    "dependencies",
                    [],
                ),
                "observed_status": observed_status(matches),
                "mapping_confidence": mapping_confidence(
                    matches
                ),
                "implementation_claim": False,
                "implementation_claim_reason": (
                    "Repository evidence does not constitute "
                    "automatic implementation certification."
                ),
                "mapped_components_count": len(
                    primary_matches
                ),
                "candidate_components_count": len(matches),
                "exact_matches_count": exact_count,
                "strong_matches_count": strong_count,
                "weak_matches_count": weak_count,
                "evidence_role_counts": dict(
                    sorted(role_counts.items())
                ),
                "primary_components": primary_matches,
                "weak_candidates": [
                    item
                    for item in matches
                    if item["strength"] == "WEAK"
                ][:25],
            }
        )

    component_records: list[dict[str, Any]] = []

    components_by_id = {
        component["component_id"]: component
        for component in components
    }

    for component_id, component in sorted(
        components_by_id.items(),
        key=lambda item: item[1]["path"],
    ):
        matches = sorted(
            matches_by_component.get(component_id, []),
            key=lambda item: (
                {
                    "EXACT": 0,
                    "STRONG": 1,
                    "WEAK": 2,
                }[item["strength"]],
                -item["score"],
                item["capability_id"],
            ),
        )

        primary = [
            item
            for item in matches
            if item.get("primary_implementation_evidence")
        ]

        evidence_role = classify_evidence_role(component)
        active_component = evidence_role != "INACTIVE"

        component_records.append(
            {
                "component_id": component_id,
                "stable_key": component["stable_key"],
                "path": component["path"],
                "name": component["name"],
                "domain": component["domain"],
                "component_type": component[
                    "component_type"
                ],
                "subtype": component["subtype"],
                "maturity": component["maturity"],
                "status": component["status"],
                "evidence_role": evidence_role,
                "active_component": active_component,
                "mapped_capabilities_count": len(primary),
                "candidate_capabilities_count": len(matches),
                "mapped_capabilities": primary,
                "weak_candidates": [
                    item
                    for item in matches
                    if item["strength"] == "WEAK"
                ][:25],
            }
        )

    return capability_records, component_records


def build_statistics(
    capability_records: list[dict[str, Any]],
    component_records: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_counter = Counter(
        item["observed_status"]
        for item in capability_records
    )

    capabilities_without_primary = [
        item
        for item in capability_records
        if item["mapped_components_count"] == 0
    ]

    target_without_primary = [
        item
        for item in capabilities_without_primary
        if item["target_status"] in {
            "implemented",
            "integrated",
            "validated",
            "certified",
            "production_ready",
            "production",
        }
    ]

    rc1_without_primary = [
        item
        for item in capabilities_without_primary
        if item["roadmap_phase"] == "RC1"
    ]

    mapped_components = [
        item
        for item in component_records
        if item["mapped_capabilities_count"] > 0
    ]

    multi_mapped_components = [
        item
        for item in component_records
        if item["mapped_capabilities_count"] > 1
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "generated_utc": utc_now(),
        "capabilities_count": len(capability_records),
        "components_count": len(component_records),
        "capabilities_with_exact_evidence": sum(
            item["exact_matches_count"] > 0
            for item in capability_records
        ),
        "capabilities_with_strong_evidence": sum(
            item["strong_matches_count"] > 0
            for item in capability_records
        ),
        "capabilities_with_only_weak_evidence": sum(
            item["observed_status"]
            == "weak_evidence_only"
            for item in capability_records
        ),
        "capabilities_without_evidence": sum(
            item["observed_status"] == "no_evidence"
            for item in capability_records
        ),
        "capabilities_without_primary_evidence": len(
            capabilities_without_primary
        ),
        "target_status_without_primary_evidence": len(
            target_without_primary
        ),
        "rc1_without_primary_evidence": len(
            rc1_without_primary
        ),
        "components_mapped": len(mapped_components),
        "components_unmapped": (
            len(component_records)
            - len(mapped_components)
        ),
        "components_multi_mapped": len(
            multi_mapped_components
        ),
        "components_inactive": sum(
            not item.get("active_component", True)
            for item in component_records
        ),
        "components_by_evidence_role": dict(
            sorted(
                Counter(
                    item.get(
                        "evidence_role",
                        "SUPPORTING",
                    )
                    for item in component_records
                ).items()
            )
        ),
        "by_observed_status": dict(
            sorted(observed_counter.items())
        ),
        "capabilities_without_primary_evidence_ids": [
            item["capability_id"]
            for item in capabilities_without_primary
        ],
        "target_status_without_primary_evidence_ids": [
            item["capability_id"]
            for item in target_without_primary
        ],
        "rc1_without_primary_evidence_ids": [
            item["capability_id"]
            for item in rc1_without_primary
        ],
    }


def validate_outputs(
    catalog: dict[str, Any],
    registry: dict[str, Any],
    capability_records: list[dict[str, Any]],
    component_records: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []

    expected_capabilities = catalog.get(
        "capabilities_count",
        0,
    )
    expected_components = registry.get(
        "components_count",
        0,
    )

    if len(capability_records) != expected_capabilities:
        errors.append(
            "Capability count mismatch: "
            f"{len(capability_records)} != "
            f"{expected_capabilities}"
        )

    if len(component_records) != expected_components:
        errors.append(
            "Component count mismatch: "
            f"{len(component_records)} != "
            f"{expected_components}"
        )

    capability_ids = [
        item["capability_id"]
        for item in capability_records
    ]

    component_ids = [
        item["component_id"]
        for item in component_records
    ]

    if len(capability_ids) != len(set(capability_ids)):
        errors.append("Duplicate capability records detected")

    if len(component_ids) != len(set(component_ids)):
        errors.append("Duplicate component records detected")

    for capability in capability_records:
        if capability["implementation_claim"] is not False:
            errors.append(
                f"{capability['capability_id']}: "
                "automatic implementation claim detected"
            )

        for match in (
            capability["primary_components"]
            + capability["weak_candidates"]
        ):
            if match["strength"] not in {
                "EXACT",
                "STRONG",
                "WEAK",
            }:
                errors.append(
                    f"{capability['capability_id']}: "
                    f"invalid strength {match['strength']}"
                )

            evidence_role = match.get("evidence_role")

            if evidence_role not in EVIDENCE_ROLES:
                errors.append(
                    f"{capability['capability_id']}: "
                    f"invalid evidence role {evidence_role}"
                )

            if not isinstance(
                match.get("active_component"),
                bool,
            ):
                errors.append(
                    f"{capability['capability_id']}: "
                    "invalid active_component value"
                )

            if not isinstance(
                match.get(
                    "primary_implementation_evidence"
                ),
                bool,
            ):
                errors.append(
                    f"{capability['capability_id']}: "
                    "invalid primary evidence value"
                )

            if (
                match.get(
                    "primary_implementation_evidence"
                )
                and evidence_role not in {
                    "CORE",
                    "SUPPORTING",
                }
            ):
                errors.append(
                    f"{capability['capability_id']}: "
                    "non-implementation role marked primary"
                )

            if (
                match.get(
                    "primary_implementation_evidence"
                )
                and not match.get("active_component")
            ):
                errors.append(
                    f"{capability['capability_id']}: "
                    "inactive component marked primary"
                )

    return sorted(set(errors))


def build_report(
    capability_records: list[dict[str, Any]],
    statistics: dict[str, Any],
    validation_errors: list[str],
) -> str:
    lines = [
        "# Nova Star Capital — Capability Registry",
        "",
        f"- Mapper version: `{MAPPER_VERSION}`",
        f"- Generated UTC: `{statistics['generated_utc']}`",
        f"- Capabilities: **{statistics['capabilities_count']}**",
        f"- Components: **{statistics['components_count']}**",
        f"- Validation status: **{'PASS' if not validation_errors else 'WARNING'}**",
        "",
        "## Mapping overview",
        "",
        "| Metric | Value |",
        "|---|---:|",
        (
            "| Capabilities with exact evidence | "
            f"{statistics['capabilities_with_exact_evidence']} |"
        ),
        (
            "| Capabilities with strong evidence | "
            f"{statistics['capabilities_with_strong_evidence']} |"
        ),
        (
            "| Capabilities with only weak evidence | "
            f"{statistics['capabilities_with_only_weak_evidence']} |"
        ),
        (
            "| Capabilities without evidence | "
            f"{statistics['capabilities_without_evidence']} |"
        ),
        (
            "| Components mapped | "
            f"{statistics['components_mapped']} |"
        ),
        (
            "| Components unmapped | "
            f"{statistics['components_unmapped']} |"
        ),
        (
            "| Components mapped to multiple capabilities | "
            f"{statistics['components_multi_mapped']} |"
        ),
        (
            "| Components classified inactive | "
            f"{statistics['components_inactive']} |"
        ),
        "",
        "## Capability evidence",
        "",
        (
            "| Capability | Target | Observed | Confidence | "
            "Exact | Strong | Weak | Primary components |"
        ),
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]

    for capability in capability_records:
        lines.append(
            "| "
            f"{capability['capability_id']} — "
            f"{capability['name']} | "
            f"{capability['target_status']} | "
            f"{capability['observed_status']} | "
            f"{capability['mapping_confidence']:.2f} | "
            f"{capability['exact_matches_count']} | "
            f"{capability['strong_matches_count']} | "
            f"{capability['weak_matches_count']} | "
            f"{capability['mapped_components_count']} |"
        )

    lines.extend(
        [
            "",
            "## Target status without primary evidence",
            "",
        ]
    )

    target_ids = statistics[
        "target_status_without_primary_evidence_ids"
    ]

    if target_ids:
        for capability_id in target_ids:
            capability = next(
                item
                for item in capability_records
                if item["capability_id"] == capability_id
            )
            lines.append(
                f"- `{capability_id}` — {capability['name']} "
                f"(target: {capability['target_status']}, "
                f"roadmap: {capability['roadmap_phase']})"
            )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            (
                "Repository mapping is evidence discovery only. "
                "It does not certify implementation, integration, "
                "validation, production readiness or production status."
            ),
            "",
        ]
    )

    if validation_errors:
        lines.extend(
            [
                "## Validation errors",
                "",
            ]
        )
        lines.extend(
            f"- {error}"
            for error in validation_errors
        )
        lines.append("")

    return "\n".join(lines)


def generate_registry(
    input_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    catalog_path = input_root / "capability_catalog.json"
    component_registry_path = (
        input_root / "component_registry.json"
    )

    catalog = load_json(catalog_path)
    component_registry = load_json(
        component_registry_path
    )

    capability_records, component_records = build_mapping(
        catalog,
        component_registry,
    )

    statistics = build_statistics(
        capability_records,
        component_records,
    )

    validation_errors = validate_outputs(
        catalog,
        component_registry,
        capability_records,
        component_records,
    )

    status = (
        "healthy"
        if not validation_errors
        else "warning"
    )

    capability_payload = {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "generated_utc": utc_now(),
        "status": status,
        "source_catalog": str(catalog_path),
        "source_catalog_version": catalog.get(
            "catalog_version"
        ),
        "source_component_registry": str(
            component_registry_path
        ),
        "source_component_registry_version": (
            component_registry.get("generator_version")
        ),
        "validation_errors": validation_errors,
        "capabilities_count": len(capability_records),
        "capabilities": capability_records,
    }

    component_payload = {
        "schema_version": SCHEMA_VERSION,
        "mapper_version": MAPPER_VERSION,
        "generated_utc": utc_now(),
        "status": status,
        "validation_errors": validation_errors,
        "components_count": len(component_records),
        "components": component_records,
    }

    report = build_report(
        capability_records,
        statistics,
        validation_errors,
    )

    output_root.mkdir(parents=True, exist_ok=True)

    capability_output = (
        output_root / "capability_registry.json"
    )
    component_output = (
        output_root
        / "component_capability_mapping.json"
    )
    statistics_output = (
        output_root
        / "capability_mapping_statistics.json"
    )
    report_output = (
        output_root
        / "CAPABILITY_MAPPING_REPORT.md"
    )

    atomic_write_json(
        capability_output,
        capability_payload,
    )
    atomic_write_json(
        component_output,
        component_payload,
    )
    atomic_write_json(
        statistics_output,
        statistics,
    )
    atomic_write_text(
        report_output,
        report,
    )

    return {
        "status": status,
        "validation_errors": validation_errors,
        "capabilities_count": len(capability_records),
        "components_count": len(component_records),
        "statistics": statistics,
        "capability_registry_path": str(
            capability_output
        ),
        "component_mapping_path": str(
            component_output
        ),
        "statistics_path": str(statistics_output),
        "report_path": str(report_output),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the NSC Capability Registry and "
            "Component-to-Capability Mapping."
        )
    )
    parser.add_argument(
        "--input-root",
        default=str(DEFAULT_INPUT_ROOT),
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
    )
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def main() -> int:
    args = parse_arguments()
    configure_logging(args.verbose)

    input_root = Path(args.input_root).resolve()
    output_root = Path(args.output_root).resolve()

    LOGGER.info(
        "Starting Capability Registry generation"
    )
    LOGGER.info("Input root: %s", input_root)
    LOGGER.info("Output root: %s", output_root)

    result = generate_registry(
        input_root=input_root,
        output_root=output_root,
    )

    statistics = result["statistics"]

    print()
    print("===== NSC CAPABILITY REGISTRY =====")
    print(f"Status: {result['status']}")
    print(
        f"Capabilities: "
        f"{result['capabilities_count']}"
    )
    print(
        f"Components: "
        f"{result['components_count']}"
    )
    print(
        "Capabilities with exact evidence: "
        f"{statistics['capabilities_with_exact_evidence']}"
    )
    print(
        "Capabilities with strong evidence: "
        f"{statistics['capabilities_with_strong_evidence']}"
    )
    print(
        "Capabilities with only weak evidence: "
        f"{statistics['capabilities_with_only_weak_evidence']}"
    )
    print(
        "Capabilities without evidence: "
        f"{statistics['capabilities_without_evidence']}"
    )
    print(
        "Components mapped: "
        f"{statistics['components_mapped']}"
    )
    print(
        "Components unmapped: "
        f"{statistics['components_unmapped']}"
    )
    print(
        "Target status without primary evidence: "
        f"{statistics['target_status_without_primary_evidence']}"
    )
    print()
    print("Artefacts:")
    print(f"- {result['capability_registry_path']}")
    print(f"- {result['component_mapping_path']}")
    print(f"- {result['statistics_path']}")
    print(f"- {result['report_path']}")

    if result["validation_errors"]:
        print()
        print("Validation errors:")
        for error in result["validation_errors"]:
            print(f"- {error}")

    if (
        args.strict
        and result["validation_errors"]
    ):
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
