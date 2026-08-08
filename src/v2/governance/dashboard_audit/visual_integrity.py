import re

VISUAL_PATTERNS = {
    "tailwind_visual_percent": r'w-\[\d{1,3}%\]|left-\[\d{1,3}%\]|top-\[\d{1,3}%\]',
    "svg_numeric_attrs": r'strokeWidth=|cx=|cy=|opacity=|<path|<circle',
    "layout_coordinates": r'\b[xy]:\s*["\']\d{1,3}%["\']',
}

def scan(text: str):
    findings = {}
    for name, pat in VISUAL_PATTERNS.items():
        m = re.findall(pat, text)
        if m:
            findings[name] = len(m)
    return findings
