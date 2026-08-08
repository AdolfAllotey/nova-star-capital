import re

BUSINESS_PATTERNS = {
    "mock_placeholder": r'\b(mock|Mock|MOCK|placeholder|Placeholder|TODO|FIXME|dummy|fake|sample)\b',
    "static_business_pct_array": r'\[\s*["\'][^"\']+["\']\s*,\s*["\']\d{1,3}(?:\.\d+)?%["\']',
    "static_confidence_78": r'\bconfidence[^\\n]{0,80}78\b|\b78[^\\n]{0,80}confidence\b',
    "static_score_pct": r'\b(score|confidence|allocation|exposure|risk|governance|execution|api)[^\\n]{0,80}["\']\d{1,3}%["\']',
    "static_money_value": r'\b(pnl|cash|capital|notional|exposure|value)[^\\n]{0,80}["\'](?:€|\$)?\d+[.,]?\d*\s*(?:€|USD|EUR)?["\']',
}

def scan(text: str):
    findings = {}
    lines = text.splitlines()
    detail = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if any(x in stripped for x in ["strokeWidth", "left-[", "top-[", "w-[", "cx=", "cy=", " d=", "path d=", "opacity=", "x:", "y:"]):
            continue
        # Ignore visual topology/layout arrays: [label, subtitle, tone, x%, y%]
        if stripped.startswith("[") and stripped.endswith("],") and stripped.count("%") >= 2:
            continue
        for name, pat in BUSINESS_PATTERNS.items():
            if re.search(pat, stripped, re.IGNORECASE):
                findings[name] = findings.get(name, 0) + 1
                detail.append({"line": i, "type": name, "code": stripped[:240]})
    return findings, detail
