from __future__ import annotations

"""
Nova Star Capital
Enterprise Component Inventory

Purpose
-------
Build the official technical component inventory of Nova Star Capital.

The inventory scans selected source directories and detects:

- Python engines
- builders
- audits
- reports
- registries
- schedulers
- runners
- services
- adapters
- validators
- FastAPI routers
- React pages
- React components
- JavaScript services
- orchestration modules
- documentation modules

Generated artefacts
-------------------
/opt/nsc/data/preprod/enterprise/component_registry.json
/opt/nsc/data/preprod/enterprise/component_statistics.json
/opt/nsc/data/preprod/enterprise/component_domains.json

Principles
----------
- deterministic output;
- read-only repository scan;
- no code execution from scanned modules;
- stable component identifiers;
- explicit exclusion of vendor, archive and backup directories;
- compatible with future dependency and traceability registries.
"""

import argparse
import ast
import hashlib
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


APP_ROOT = Path("/opt/nsc/app")
DEFAULT_SOURCE_ROOTS = (
    APP_ROOT / "src" / "v2",
    APP_ROOT / "scripts",
    APP_ROOT / "tools",
)

DEFAULT_OUTPUT_ROOT = Path("/opt/nsc/data/preprod/enterprise")

SCHEMA_VERSION = "1.0"
GENERATOR_VERSION = "1.1.0"

SUPPORTED_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".github",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "archive",
    "archives",
    "vendor",
    "vendors",
    "tmp",
    "temp",
    "logs",
}

IGNORED_FILE_PATTERNS = (
    re.compile(r".*\.pyc$", re.IGNORECASE),
    re.compile(r".*\.pyo$", re.IGNORECASE),
    re.compile(r".*\.min\.js$", re.IGNORECASE),
    re.compile(r".*\.map$", re.IGNORECASE),
    re.compile(r".*\.bak(?:_|\.|$).*", re.IGNORECASE),
    re.compile(r".*backup.*", re.IGNORECASE),
    re.compile(r".*copy.*", re.IGNORECASE),
    re.compile(r".*~$", re.IGNORECASE),
)

DOMAIN_ALIASES = {
    "crypto": "crypto",
    "discovery": "discovery",
    "offensive": "offensive_equities",
    "offensive_equities": "offensive_equities",
    "defensive": "defensive_equities",
    "defensive_equities": "defensive_equities",
    "equities": "equities",
    "equity": "equities",
    "bonds": "bonds",
    "bond": "bonds",
    "fixed_income": "bonds",
    "precious_metals": "precious_metals",
    "metals": "precious_metals",
    "options": "options",
    "option": "options",
    "forex": "forex",
    "long_term": "long_term",
    "longterm": "long_term",
    "portfolio": "portfolio",
    "portfolio_brain": "portfolio",
    "capital": "capital",
    "funding": "capital",
    "treasury": "treasury",
    "risk": "risk",
    "governance": "governance",
    "execution": "execution",
    "broker": "execution",
    "brokers": "execution",
    "orders": "execution",
    "reporting": "reporting",
    "reports": "reporting",
    "monitoring": "monitoring",
    "observability": "monitoring",
    "scheduler": "scheduler",
    "scheduling": "scheduler",
    "orchestration": "orchestration",
    "runtime": "runtime",
    "preprod": "preprod",
    "audits": "audit",
    "audit": "audit",
    "documentation": "documentation",
    "knowledge": "knowledge",
    "api": "api",
    "routes": "api",
    "interface": "interface",
    "react": "interface",
    "dashboard": "interface",
    "dashboards": "interface",
    "security": "security",
    "sentiment": "sentiment",
    "whales": "whales",
    "airdrop": "airdrop",
    "airdrops": "airdrop",
    "enterprise": "enterprise",
}

TYPE_ABBREVIATIONS = {
    "engine": "ENG",
    "builder": "BLD",
    "audit": "AUD",
    "report": "RPT",
    "registry": "REG",
    "scheduler": "SCH",
    "runner": "RUN",
    "router": "API",
    "api": "API",
    "dashboard": "UI",
    "react_page": "UI",
    "react_component": "UIC",
    "service": "SRV",
    "adapter": "ADP",
    "validator": "VAL",
    "analyzer": "ANL",
    "model": "MOD",
    "repository": "REP",
    "controller": "CTL",
    "manager": "MGR",
    "orchestrator": "ORC",
    "generator": "GEN",
    "indexer": "IDX",
    "monitor": "MON",
    "loader": "LOD",
    "processor": "PRC",
    "client": "CLI",
    "configuration": "CFG",
    "utility": "UTL",
    "module": "MOD",
}

CRITICAL_DOMAINS = {
    "portfolio",
    "risk",
    "governance",
    "execution",
    "runtime",
    "orchestration",
    "capital",
}

HIGH_CRITICALITY_TYPES = {
    "engine",
    "controller",
    "orchestrator",
    "scheduler",
    "router",
    "api",
    "validator",
}


LOGGER = logging.getLogger("nsc.enterprise.component_inventory")


@dataclass(frozen=True)
class EnterpriseComponent:
    component_id: str
    stable_key: str
    name: str
    display_name: str
    domain: str
    component_type: str
    subtype: str | None
    path: str
    absolute_path: str
    source_root: str
    language: str
    extension: str
    owner: str
    status: str
    maturity: str
    criticality: str
    size_bytes: int
    line_count: int
    class_count: int
    function_count: int
    import_count: int
    route_count: int
    exported_symbol_count: int
    has_main_entrypoint: bool
    has_tests_nearby: bool
    is_package_initializer: bool
    detected_signals: list[str]
    parse_status: str
    parse_error: str | None
    content_sha256: str
    modified_utc: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PythonInspection:
    class_count: int
    function_count: int
    import_count: int
    route_count: int
    exported_symbol_count: int
    has_main_entrypoint: bool
    detected_signals: list[str]
    parse_status: str
    parse_error: str | None


@dataclass(frozen=True)
class FrontendInspection:
    route_count: int
    exported_symbol_count: int
    detected_signals: list[str]
    parse_status: str
    parse_error: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_modified_utc(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat(timespec="seconds")
    except OSError:
        return None


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def normalize_token(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_").lower()


def humanize(value: str) -> str:
    normalized = normalize_token(value)
    return " ".join(part.capitalize() for part in normalized.split("_") if part)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def should_ignore_path(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}

    if lower_parts.intersection(IGNORED_DIRECTORY_NAMES):
        return True

    for part in path.parts:
        normalized = part.lower()
        if normalized.startswith("dist.bak"):
            return True
        if normalized.startswith("react_prod_"):
            return True
        if normalized.startswith("react_legacy"):
            return True
        if normalized.startswith("_archive"):
            return True
        if ".bak_" in normalized:
            return True

    name = path.name
    return any(pattern.fullmatch(name) for pattern in IGNORED_FILE_PATTERNS)


def iter_source_files(source_roots: Iterable[Path]) -> Iterable[tuple[Path, Path]]:
    seen: set[Path] = set()

    for source_root in source_roots:
        if not source_root.exists():
            LOGGER.warning("Source root not found: %s", source_root)
            continue

        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if should_ignore_path(path):
                continue

            resolved = path.resolve()
            if resolved in seen:
                continue

            seen.add(resolved)
            yield source_root, path


def read_text(path: Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore"), None
    except OSError as exc:
        return "", str(exc)


def calculate_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


def inspect_python(content: str) -> PythonInspection:
    detected_signals: set[str] = set()

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return PythonInspection(
            class_count=0,
            function_count=0,
            import_count=0,
            route_count=0,
            exported_symbol_count=0,
            has_main_entrypoint=False,
            detected_signals=[],
            parse_status="syntax_error",
            parse_error=f"{exc.msg} at line {exc.lineno}",
        )
    except Exception as exc:
        return PythonInspection(
            class_count=0,
            function_count=0,
            import_count=0,
            route_count=0,
            exported_symbol_count=0,
            has_main_entrypoint=False,
            detected_signals=[],
            parse_status="error",
            parse_error=str(exc),
        )

    class_count = 0
    function_count = 0
    import_count = 0
    route_count = 0
    exported_symbol_count = 0
    has_main_entrypoint = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_count += 1
            exported_symbol_count += int(not node.name.startswith("_"))

            bases = {
                getattr(base, "id", None)
                or getattr(base, "attr", None)
                or ""
                for base in node.bases
            }

            if "BaseModel" in bases:
                detected_signals.add("pydantic_model")
            if "Enum" in bases:
                detected_signals.add("enum")
            if any("Repository" in base for base in bases):
                detected_signals.add("repository_class")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_count += 1
            exported_symbol_count += int(not node.name.startswith("_"))

            for decorator in node.decorator_list:
                decorator_name = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                if re.search(
                    r"\.(get|post|put|patch|delete|options|head)\s*\(",
                    decorator_name,
                    re.IGNORECASE,
                ):
                    route_count += 1
                    detected_signals.add("fastapi_route")

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1

            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            else:
                module = " ".join(alias.name for alias in node.names)

            module_lower = module.lower()

            if "fastapi" in module_lower:
                detected_signals.add("fastapi")
            if "pydantic" in module_lower:
                detected_signals.add("pydantic")
            if "sqlalchemy" in module_lower:
                detected_signals.add("sqlalchemy")
            if "pandas" in module_lower:
                detected_signals.add("pandas")
            if "numpy" in module_lower:
                detected_signals.add("numpy")
            if "logging" in module_lower:
                detected_signals.add("logging")
            if "asyncio" in module_lower:
                detected_signals.add("asyncio")

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "router":
                    detected_signals.add("fastapi_router")
                if isinstance(target, ast.Name) and target.id == "app":
                    detected_signals.add("application_entrypoint")

        elif isinstance(node, ast.If):
            test_dump = ast.dump(node.test)
            if "__name__" in test_dump and "__main__" in test_dump:
                has_main_entrypoint = True
                detected_signals.add("main_entrypoint")

    if "APIRouter(" in content:
        detected_signals.add("fastapi_router")

    if "@dataclass" in content:
        detected_signals.add("dataclass")

    if "argparse.ArgumentParser" in content:
        detected_signals.add("cli")

    return PythonInspection(
        class_count=class_count,
        function_count=function_count,
        import_count=import_count,
        route_count=route_count,
        exported_symbol_count=exported_symbol_count,
        has_main_entrypoint=has_main_entrypoint,
        detected_signals=sorted(detected_signals),
        parse_status="ok",
        parse_error=None,
    )


def inspect_frontend(content: str, suffix: str) -> FrontendInspection:
    signals: set[str] = set()
    route_count = 0
    exported_symbol_count = 0

    try:
        if re.search(r"\bimport\s+React\b|\bfrom\s+[\"']react[\"']", content):
            signals.add("react")

        if re.search(r"\buseEffect\s*\(", content):
            signals.add("react_use_effect")

        if re.search(r"\buseState\s*\(", content):
            signals.add("react_use_state")

        if re.search(r"\bfetch\s*\(", content):
            signals.add("http_fetch")

        if re.search(r"\baxios\b", content, re.IGNORECASE):
            signals.add("axios")

        if re.search(r"\bexport\s+default\b", content):
            signals.add("default_export")
            exported_symbol_count += 1

        named_exports = re.findall(
            r"\bexport\s+(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)",
            content,
        )
        exported_symbol_count += len(named_exports)

        route_count += len(
            re.findall(
                r"<Route\b|createBrowserRouter\s*\(|path\s*:\s*[\"']",
                content,
            )
        )

        if re.search(r"\bRecharts\b|from\s+[\"']recharts[\"']", content):
            signals.add("charting")

        if re.search(r"\bWebSocket\b|EventSource\s*\(", content):
            signals.add("realtime")

        return FrontendInspection(
            route_count=route_count,
            exported_symbol_count=exported_symbol_count,
            detected_signals=sorted(signals),
            parse_status="ok",
            parse_error=None,
        )
    except Exception as exc:
        return FrontendInspection(
            route_count=0,
            exported_symbol_count=0,
            detected_signals=[],
            parse_status="error",
            parse_error=str(exc),
        )


def detect_domain(path: Path, source_root: Path) -> str:
    try:
        relative_parts = list(path.relative_to(source_root).parts)
    except ValueError:
        relative_parts = list(path.parts)

    candidates: list[str] = []

    for part in relative_parts[:-1]:
        normalized = normalize_token(part)
        if normalized:
            candidates.append(normalized)

    stem_tokens = normalize_token(path.stem).split("_")
    candidates.extend(stem_tokens)

    for candidate in candidates:
        if candidate in DOMAIN_ALIASES:
            return DOMAIN_ALIASES[candidate]

    joined = "_".join(candidates)

    ordered_patterns = (
        ("offensive_equities", "offensive_equities"),
        ("defensive_equities", "defensive_equities"),
        ("precious_metals", "precious_metals"),
        ("portfolio_brain", "portfolio"),
        ("long_term", "long_term"),
        ("documentation_center", "documentation"),
        ("enterprise_architecture", "enterprise"),
    )

    for pattern, domain in ordered_patterns:
        if pattern in joined:
            return domain

    if "src/v2/api" in str(path).replace("\\", "/"):
        return "api"

    if "interface/react" in str(path).replace("\\", "/"):
        return "interface"

    if source_root.name == "scripts":
        return "orchestration"

    if source_root.name == "tools":
        return "tooling"

    return "platform"


def detect_component_type(
    path: Path,
    content: str,
    signals: Iterable[str],
) -> tuple[str, str | None]:
    stem = normalize_token(path.stem)
    path_text = str(path).replace("\\", "/").lower()
    signal_set = set(signals)

    if path.name == "__init__.py":
        return "module", "package_initializer"

    if "fastapi_router" in signal_set or "fastapi_route" in signal_set:
        return "router", "fastapi"

    if "/api/routes/" in path_text:
        return "router", "fastapi"

    if "/interface/react/" in path_text:
        if "/pages/" in path_text:
            return "react_page", "dashboard"
        if "/components/" in path_text:
            return "react_component", "frontend_component"
        if "/services/" in path_text or "/api/" in path_text:
            return "service", "frontend_service"
        return "react_component", "frontend_module"

    ordered_suffixes = (
        ("_engine", "engine"),
        ("_builder", "builder"),
        ("_audit", "audit"),
        ("_auditor", "audit"),
        ("_report", "report"),
        ("_reporter", "report"),
        ("_registry", "registry"),
        ("_scheduler", "scheduler"),
        ("_runner", "runner"),
        ("_service", "service"),
        ("_adapter", "adapter"),
        ("_validator", "validator"),
        ("_validation", "validator"),
        ("_analyzer", "analyzer"),
        ("_analysis", "analyzer"),
        ("_model", "model"),
        ("_repository", "repository"),
        ("_controller", "controller"),
        ("_manager", "manager"),
        ("_orchestrator", "orchestrator"),
        ("_generator", "generator"),
        ("_indexer", "indexer"),
        ("_monitor", "monitor"),
        ("_loader", "loader"),
        ("_processor", "processor"),
        ("_client", "client"),
        ("_config", "configuration"),
        ("_configuration", "configuration"),
        ("_utils", "utility"),
        ("_util", "utility"),
    )

    for suffix, component_type in ordered_suffixes:
        if stem.endswith(suffix):
            return component_type, suffix.lstrip("_")

    keyword_patterns = (
        ("engine", "engine"),
        ("audit", "audit"),
        ("report", "report"),
        ("registry", "registry"),
        ("scheduler", "scheduler"),
        ("orchestrat", "orchestrator"),
        ("validator", "validator"),
        ("builder", "builder"),
        ("monitor", "monitor"),
    )

    for keyword, component_type in keyword_patterns:
        if keyword in stem:
            return component_type, "keyword_detection"

    if "cli" in signal_set or "main_entrypoint" in signal_set:
        return "runner", "cli"

    if path.suffix.lower() == ".py":
        return "module", "python_module"

    return "module", "frontend_module"


def detect_owner(domain: str) -> str:
    owner_map = {
        "crypto": "Crypto Platform",
        "discovery": "Market Intelligence",
        "offensive_equities": "Offensive Equities",
        "defensive_equities": "Defensive Equities",
        "equities": "Equities Platform",
        "bonds": "Fixed Income",
        "precious_metals": "Precious Metals",
        "options": "Options Platform",
        "forex": "Forex Platform",
        "long_term": "Long-Term Portfolio",
        "portfolio": "Portfolio Brain",
        "capital": "Capital Management",
        "treasury": "Treasury",
        "risk": "Risk Management",
        "governance": "Governance",
        "execution": "Execution Platform",
        "reporting": "Reporting",
        "monitoring": "Platform Operations",
        "scheduler": "Platform Operations",
        "orchestration": "Platform Operations",
        "runtime": "Platform Operations",
        "preprod": "Preproduction",
        "documentation": "Enterprise Knowledge",
        "knowledge": "Enterprise Knowledge",
        "api": "Platform API",
        "interface": "Platform Interface",
        "security": "Security",
        "enterprise": "Enterprise Architecture",
        "audit": "Audit and Certification",
        "tooling": "Engineering Tooling",
        "platform": "Platform Engineering",
    }
    return owner_map.get(domain, humanize(domain))


def detect_criticality(domain: str, component_type: str) -> str:
    if domain in CRITICAL_DOMAINS and component_type in HIGH_CRITICALITY_TYPES:
        return "critical"

    if domain in CRITICAL_DOMAINS:
        return "high"

    if component_type in HIGH_CRITICALITY_TYPES:
        return "high"

    if component_type in {
        "audit",
        "report",
        "registry",
        "scheduler",
        "service",
        "react_page",
    }:
        return "important"

    return "standard"


def detect_maturity(path: Path, component_type: str, content: str) -> str:
    """
    Infer a conservative static maturity classification.

    This classification only describes evidence visible in source code.
    It must not be interpreted as proof of integration, runtime health,
    certification or production readiness.
    """
    lower_path = str(path).lower()
    lower_name = path.name.lower()
    lower_stem = path.stem.lower()
    content_head = content[:2500].lower()

    deprecated_path_signals = (
        "deprecated",
        "/archive/",
        "/archives/",
    )
    explicit_deprecated_content_signals = (
        "@deprecated",
        "this module is deprecated",
        "this component is deprecated",
        "deprecated module",
        "deprecated component",
        "deprecated endpoint retained",
        "deprecated: use ",
        "deprecated - use ",
        "deprecated / legacy",
    )
    if (
        any(signal in lower_path for signal in deprecated_path_signals)
        or any(
            signal in content_head
            for signal in explicit_deprecated_content_signals
        )
    ):
        return "deprecated"

    stub_name_signals = (
        "_stub",
        "stub_",
        ".stub",
    )
    if (
        any(signal in lower_name for signal in stub_name_signals)
        or lower_stem == "stub"
    ):
        return "prototype"

    placeholder_name_signals = (
        "_placeholder",
        "placeholder_",
    )
    if any(signal in lower_name for signal in placeholder_name_signals):
        return "prototype"

    prototype_path_signals = (
        "experimental",
        "prototype",
        "/poc/",
        "/proof_of_concept/",
    )
    if any(signal in lower_path for signal in prototype_path_signals):
        return "prototype"

    explicit_prototype_content_signals = (
        "not implemented",
        "not yet implemented",
        "placeholder / base",
        "placeholder v2",
        "placeholder for now",
        "temporary stub",
    )
    if any(
        signal in content_head
        for signal in explicit_prototype_content_signals
    ):
        return "prototype"

    if "shadow" in lower_path or "shadow mode" in content_head:
        return "shadow"

    if component_type in {
        "engine",
        "router",
        "scheduler",
        "orchestrator",
        "controller",
        "validator",
    }:
        return "implemented"

    return "detected"


def nearby_tests_exist(path: Path) -> bool:
    stem = path.stem

    candidates = {
        path.with_name(f"test_{stem}.py"),
        path.with_name(f"{stem}_test.py"),
        path.parent / "tests" / f"test_{stem}.py",
        path.parent.parent / "tests" / f"test_{stem}.py",
        APP_ROOT / "tests" / f"test_{stem}.py",
    }

    try:
        relative = path.resolve().relative_to(
            (APP_ROOT / "src" / "v2").resolve()
        )
        if len(relative.parts) > 1:
            domain = relative.parts[0]
            candidates.add(
                APP_ROOT
                / "tests"
                / domain
                / f"test_{stem}.py"
            )
    except ValueError:
        pass

    return any(candidate.exists() for candidate in candidates)


def stable_component_key(
    relative_path: str,
    domain: str,
    component_type: str,
) -> str:
    return f"{domain}:{component_type}:{relative_path}"


def component_id_from_key(
    stable_key: str,
    domain: str,
    component_type: str,
) -> str:
    domain_prefix = normalize_token(domain).replace("_", "-").upper()
    type_prefix = TYPE_ABBREVIATIONS.get(component_type, "MOD")
    digest = hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:10].upper()
    return f"{domain_prefix}-{type_prefix}-{digest}"


def build_component(
    path: Path,
    source_root: Path,
) -> EnterpriseComponent:
    content, read_error = read_text(path)
    suffix = path.suffix.lower()

    if suffix == ".py":
        inspection = inspect_python(content)
        class_count = inspection.class_count
        function_count = inspection.function_count
        import_count = inspection.import_count
        route_count = inspection.route_count
        exported_symbol_count = inspection.exported_symbol_count
        has_main_entrypoint = inspection.has_main_entrypoint
        signals = inspection.detected_signals
        parse_status = inspection.parse_status
        parse_error = inspection.parse_error or read_error
        language = "python"
    else:
        inspection = inspect_frontend(content, suffix)
        class_count = 0
        function_count = len(
            re.findall(
                r"\b(?:function\s+[A-Za-z_$][\w$]*|"
                r"(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*"
                r"(?:async\s*)?\([^)]*\)\s*=>)",
                content,
            )
        )
        import_count = len(re.findall(r"^\s*import\b", content, flags=re.MULTILINE))
        route_count = inspection.route_count
        exported_symbol_count = inspection.exported_symbol_count
        has_main_entrypoint = False
        signals = inspection.detected_signals
        parse_status = inspection.parse_status
        parse_error = inspection.parse_error or read_error
        language = {
            ".js": "javascript",
            ".jsx": "javascript-react",
            ".ts": "typescript",
            ".tsx": "typescript-react",
        }.get(suffix, "unknown")

    domain = detect_domain(path, source_root)
    component_type, subtype = detect_component_type(path, content, signals)

    relative_path = safe_relative(path, APP_ROOT)

    explicit_type_overrides = {
        "src/v2/enterprise/inventory/"
        "enterprise_component_inventory.py": (
            "generator",
            "enterprise_inventory_generator",
        ),
        "src/v2/enterprise/capability/"
        "capability_catalog.py": (
            "registry",
            "enterprise_capability_catalog",
        ),
    }
    if relative_path in explicit_type_overrides:
        component_type, subtype = explicit_type_overrides[relative_path]
    stable_key = stable_component_key(relative_path, domain, component_type)
    component_id = component_id_from_key(
        stable_key=stable_key,
        domain=domain,
        component_type=component_type,
    )

    try:
        stat = path.stat()
        size_bytes = stat.st_size
    except OSError:
        size_bytes = len(content.encode("utf-8", errors="ignore"))

    line_count = len(content.splitlines())
    display_name = humanize(path.stem)

    return EnterpriseComponent(
        component_id=component_id,
        stable_key=stable_key,
        name=path.stem,
        display_name=display_name,
        domain=domain,
        component_type=component_type,
        subtype=subtype,
        path=relative_path,
        absolute_path=str(path.resolve()),
        source_root=safe_relative(source_root, APP_ROOT),
        language=language,
        extension=suffix,
        owner=detect_owner(domain),
        status="detected" if parse_status == "ok" else "detected_with_warning",
        maturity=detect_maturity(path, component_type, content),
        criticality=detect_criticality(domain, component_type),
        size_bytes=size_bytes,
        line_count=line_count,
        class_count=class_count,
        function_count=function_count,
        import_count=import_count,
        route_count=route_count,
        exported_symbol_count=exported_symbol_count,
        has_main_entrypoint=has_main_entrypoint,
        has_tests_nearby=nearby_tests_exist(path),
        is_package_initializer=path.name == "__init__.py",
        detected_signals=sorted(set(signals)),
        parse_status=parse_status,
        parse_error=parse_error,
        content_sha256=calculate_sha256(content),
        modified_utc=safe_modified_utc(path),
    )


def build_statistics(
    components: list[EnterpriseComponent],
) -> dict[str, Any]:
    by_type = Counter(component.component_type for component in components)
    by_domain = Counter(component.domain for component in components)
    by_language = Counter(component.language for component in components)
    by_status = Counter(component.status for component in components)
    by_maturity = Counter(component.maturity for component in components)
    by_criticality = Counter(component.criticality for component in components)
    by_parse_status = Counter(component.parse_status for component in components)

    components_with_routes = sum(component.route_count > 0 for component in components)
    components_with_tests = sum(component.has_tests_nearby for component in components)
    package_initializers = sum(
        component.is_package_initializer for component in components
    )
    total_lines = sum(component.line_count for component in components)
    total_size_bytes = sum(component.size_bytes for component in components)

    parsed_components = sum(
        component.parse_status == "ok" for component in components
    )

    test_proximity_coverage = (
        round((components_with_tests / len(components)) * 100, 2)
        if components
        else 0.0
    )

    parse_success_rate = (
        round((parsed_components / len(components)) * 100, 2)
        if components
        else 0.0
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_utc": utc_now(),
        "components_count": len(components),
        "total_lines": total_lines,
        "total_size_bytes": total_size_bytes,
        "components_with_routes": components_with_routes,
        "components_with_nearby_tests": components_with_tests,
        "package_initializers": package_initializers,
        "test_proximity_coverage": test_proximity_coverage,
        "parse_success_rate": parse_success_rate,
        "by_type": dict(sorted(by_type.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "by_language": dict(sorted(by_language.items())),
        "by_status": dict(sorted(by_status.items())),
        "by_maturity": dict(sorted(by_maturity.items())),
        "by_criticality": dict(sorted(by_criticality.items())),
        "by_parse_status": dict(sorted(by_parse_status.items())),
    }


def build_domain_summary(
    components: list[EnterpriseComponent],
) -> dict[str, Any]:
    grouped: dict[str, list[EnterpriseComponent]] = defaultdict(list)

    for component in components:
        grouped[component.domain].append(component)

    domains: dict[str, Any] = {}

    for domain, domain_components in sorted(grouped.items()):
        type_counts = Counter(
            component.component_type for component in domain_components
        )
        criticality_counts = Counter(
            component.criticality for component in domain_components
        )
        maturity_counts = Counter(
            component.maturity for component in domain_components
        )

        api_present = any(
            component.component_type in {"router", "api"}
            for component in domain_components
        )
        dashboard_present = any(
            component.component_type == "react_page"
            for component in domain_components
        )
        audit_present = any(
            component.component_type == "audit"
            for component in domain_components
        )
        reporting_present = any(
            component.component_type == "report"
            for component in domain_components
        )
        scheduler_present = any(
            component.component_type == "scheduler"
            for component in domain_components
        )

        domains[domain] = {
            "domain": domain,
            "owner": detect_owner(domain),
            "components_count": len(domain_components),
            "line_count": sum(
                component.line_count for component in domain_components
            ),
            "size_bytes": sum(
                component.size_bytes for component in domain_components
            ),
            "component_types": dict(sorted(type_counts.items())),
            "criticality": dict(sorted(criticality_counts.items())),
            "maturity": dict(sorted(maturity_counts.items())),
            "coverage_signals": {
                "api_present": api_present,
                "dashboard_present": dashboard_present,
                "audit_present": audit_present,
                "reporting_present": reporting_present,
                "scheduler_present": scheduler_present,
            },
            "component_ids": [
                component.component_id
                for component in sorted(
                    domain_components,
                    key=lambda item: (
                        item.component_type,
                        item.path,
                    ),
                )
            ],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_utc": utc_now(),
        "domains_count": len(domains),
        "domains": domains,
    }


def validate_components(
    components: list[EnterpriseComponent],
) -> list[str]:
    errors: list[str] = []

    ids = [component.component_id for component in components]
    duplicate_ids = [
        component_id
        for component_id, count in Counter(ids).items()
        if count > 1
    ]

    if duplicate_ids:
        errors.append(
            "Duplicate component IDs detected: "
            + ", ".join(sorted(duplicate_ids))
        )

    keys = [component.stable_key for component in components]
    duplicate_keys = [
        stable_key
        for stable_key, count in Counter(keys).items()
        if count > 1
    ]

    if duplicate_keys:
        errors.append(
            "Duplicate stable keys detected: "
            + ", ".join(sorted(duplicate_keys))
        )

    paths = [component.path for component in components]
    duplicate_paths = [
        path
        for path, count in Counter(paths).items()
        if count > 1
    ]

    if duplicate_paths:
        errors.append(
            "Duplicate paths detected: "
            + ", ".join(sorted(duplicate_paths))
        )

    for component in components:
        if not component.component_id:
            errors.append(f"Missing component ID for {component.path}")

        if not component.domain:
            errors.append(f"Missing domain for {component.path}")

        if not component.component_type:
            errors.append(f"Missing component type for {component.path}")

    return errors


def build_inventory(
    source_roots: Iterable[Path],
    output_root: Path,
) -> dict[str, Any]:
    started_utc = utc_now()
    components: list[EnterpriseComponent] = []

    for source_root, path in iter_source_files(source_roots):
        try:
            component = build_component(path, source_root)
            components.append(component)
        except Exception as exc:
            LOGGER.exception(
                "Unable to inspect component %s: %s",
                path,
                exc,
            )

    components.sort(
        key=lambda component: (
            component.domain,
            component.component_type,
            component.path,
        )
    )

    validation_errors = validate_components(components)
    statistics = build_statistics(components)
    domain_summary = build_domain_summary(components)

    registry_payload = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_utc": utc_now(),
        "started_utc": started_utc,
        "repository_root": str(APP_ROOT),
        "source_roots": [
            safe_relative(source_root, APP_ROOT)
            for source_root in source_roots
        ],
        "status": "healthy" if not validation_errors else "warning",
        "validation_errors": validation_errors,
        "components_count": len(components),
        "components": [
            component.to_dict()
            for component in components
        ],
    }

    output_root.mkdir(parents=True, exist_ok=True)

    registry_path = output_root / "component_registry.json"
    statistics_path = output_root / "component_statistics.json"
    domains_path = output_root / "component_domains.json"

    atomic_write_json(registry_path, registry_payload)
    atomic_write_json(statistics_path, statistics)
    atomic_write_json(domains_path, domain_summary)

    return {
        "status": registry_payload["status"],
        "components_count": len(components),
        "validation_errors": validation_errors,
        "registry_path": str(registry_path),
        "statistics_path": str(statistics_path),
        "domains_path": str(domains_path),
        "statistics": statistics,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Nova Star Capital Enterprise Component Inventory."
        )
    )

    parser.add_argument(
        "--source-root",
        action="append",
        dest="source_roots",
        help=(
            "Source root to scan. Can be supplied more than once. "
            "Defaults to src/v2, scripts and tools."
        ),
    )

    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help=(
            "Directory where registry artefacts are written. "
            f"Default: {DEFAULT_OUTPUT_ROOT}"
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when validation warnings exist.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging.",
    )

    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ),
    )


def main() -> int:
    args = parse_arguments()
    configure_logging(args.verbose)

    source_roots = (
        tuple(Path(value).resolve() for value in args.source_roots)
        if args.source_roots
        else DEFAULT_SOURCE_ROOTS
    )

    output_root = Path(args.output_root).resolve()

    LOGGER.info("Starting Enterprise Component Inventory")
    LOGGER.info(
        "Source roots: %s",
        ", ".join(str(root) for root in source_roots),
    )
    LOGGER.info("Output root: %s", output_root)

    result = build_inventory(
        source_roots=source_roots,
        output_root=output_root,
    )

    statistics = result["statistics"]

    print()
    print("===== NSC ENTERPRISE COMPONENT INVENTORY =====")
    print(f"Status: {result['status']}")
    print(f"Components: {result['components_count']}")
    print(
        "Parse success rate: "
        f"{statistics.get('parse_success_rate', 0)}%"
    )
    print(
        "Nearby test coverage: "
        f"{statistics.get('test_proximity_coverage', 0)}%"
    )
    print(f"Domains: {len(statistics.get('by_domain', {}))}")
    print(f"Types: {len(statistics.get('by_type', {}))}")
    print()
    print("Artefacts:")
    print(f"- {result['registry_path']}")
    print(f"- {result['statistics_path']}")
    print(f"- {result['domains_path']}")

    if result["validation_errors"]:
        print()
        print("Validation warnings:")
        for error in result["validation_errors"]:
            print(f"- {error}")

    print()
    print("Top component types:")
    for component_type, count in sorted(
        statistics.get("by_type", {}).items(),
        key=lambda item: (-item[1], item[0]),
    )[:15]:
        print(f"- {component_type}: {count}")

    print()
    print("Top domains:")
    for domain, count in sorted(
        statistics.get("by_domain", {}).items(),
        key=lambda item: (-item[1], item[0]),
    )[:20]:
        print(f"- {domain}: {count}")

    if args.strict and result["validation_errors"]:
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
