from pathlib import Path
import re

ACTIVE_EXT = {".jsx", ".js", ".tsx", ".ts"}
IGNORE_MARKERS = [".bak", ".broken", ".save", ".disabled"]

def is_active_file(path: Path) -> bool:
    return path.suffix in ACTIVE_EXT and not any(m in path.name for m in IGNORE_MARKERS)

def is_inactive_file(path: Path) -> bool:
    return any(m in path.name for m in IGNORE_MARKERS)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def classify_page(path: Path):
    n = path.stem.lower()
    if n in ["dashboard", "dashboardv4", "executive"]:
        return "Executive", "A"
    if any(k in n for k in ["control", "order", "position", "fill", "execution"]):
        return "Trading", "A"
    if any(k in n for k in ["portfolio", "allocation", "longterm"]):
        return "Investment", "A" if "portfolio" in n else "B"
    if "funding" in n:
        return "Treasury", "B"
    if "risk" in n or "protection" in n:
        return "Risk", "A" if "risk" in n else "B"
    if "governance" in n or "anomal" in n:
        return "Governance", "B"
    if "family" in n:
        return "Family Office", "C"
    return "Other", "C"

def imports(text):
    return sorted(set(re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', text)))

def hooks(text):
    return sorted(set(re.findall(r'\buse[A-Z][A-Za-z0-9_]*\b', text)))

def api_calls(text):
    patterns = [
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.(?:get|post|put|delete)\(["\']([^"\']+)["\']',
        r'api\.(?:get|post|put|delete)\(["\']([^"\']+)["\']',
        r'apiUrl\(["\']([^"\']+)["\']',
        r'fetchJson\(["\']([^"\']+)["\']',
        r'fetch\(`\$\{API_BASE\}([^`]+)`',
        r'fetch\(buildUrl\(["\']([^"\']+)["\']\)',
    ]
    out = []
    for pat in patterns:
        out += re.findall(pat, text)
    return sorted(set(out))

def json_refs(text):
    return sorted(set(re.findall(r'["\']([^"\']+\.json)["\']', text)))

def scan_file(path: Path, root: Path):
    text = read_text(path)
    department, criticality = classify_page(path)
    return {
        "file": str(path.relative_to(root)),
        "name": path.stem,
        "department": department,
        "criticality": criticality,
        "lines": text.count("\n") + 1,
        "imports": imports(text),
        "hooks": hooks(text),
        "api_calls": api_calls(text),
        "json_refs": json_refs(text),
        "text": text,
    }
