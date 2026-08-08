def build(item):
    return {
        "page": item["name"],
        "file": item["file"],
        "department": item["department"],
        "criticality": item["criticality"],
        "api_calls": item["api_calls"],
        "json_refs": item["json_refs"],
        "hooks": item["hooks"],
        "imports": item["imports"],
        "lineage_status": "SOURCE_DETECTED" if item["api_calls"] or item["json_refs"] else "NO_SOURCE_DETECTED",
    }
