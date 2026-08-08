#!/usr/bin/env python3
from pathlib import Path
import json
from datetime import datetime, timezone

from inventory_scanner import is_active_file, is_inactive_file, scan_file
from business_integrity import scan as scan_business
from visual_integrity import scan as scan_visual
from react_logic_analyzer import scan as scan_logic
from data_lineage import build as build_lineage
from certification_engine import score_page
from report_writer import write_json

ROOT = Path("/opt/nsc/app")
REACT_SRC = ROOT / "src/v2/interface/react/src"
PAGES_DIR = REACT_SRC / "pages"
COMPONENTS_DIR = REACT_SRC / "components"
OUT_DIR = ROOT / "data/preprod/governance/dashboard_audit"
SCOPE_REGISTRY = ROOT / "src/v2/governance/dashboard_audit/dashboard_scope_registry.json"

def load_scope():
    if not SCOPE_REGISTRY.exists():
        return None
    payload = json.loads(SCOPE_REGISTRY.read_text(encoding="utf-8"))
    return set(payload.get("dashboard_scope", []))

def enrich(item):
    text = item.pop("text")
    bh, bh_detail = scan_business(text)
    br, vr = scan_logic(text)
    vh = scan_visual(text)

    item["business_hardcode_findings"] = bh
    item["business_hardcode_details"] = bh_detail
    item["business_react_logic_findings"] = br
    item["visual_constant_findings"] = vh
    item["visual_react_logic_findings"] = vr

    score, level, status = score_page(item)
    item["dashboard_quality_score"] = score
    item["certification_level"] = level
    item["certification_status"] = status
    return item

def main():
    now = datetime.now(timezone.utc).isoformat()

    active_pages = sorted([p for p in PAGES_DIR.rglob("*") if p.is_file() and is_active_file(p)])
    inactive_pages = sorted([p for p in PAGES_DIR.rglob("*") if p.is_file() and is_inactive_file(p)])
    active_components = sorted([p for p in COMPONENTS_DIR.rglob("*") if p.is_file() and is_active_file(p)])
    inactive_components = sorted([p for p in COMPONENTS_DIR.rglob("*") if p.is_file() and is_inactive_file(p)])

    all_pages = [enrich(scan_file(p, ROOT)) for p in active_pages]
    components = [enrich(scan_file(p, ROOT)) for p in active_components]

    scope = load_scope()
    if scope:
        pages = [p for p in all_pages if p["name"] in scope]
        legacy_pages = [p for p in all_pages if p["name"] not in scope]
        missing_scope_pages = sorted([name for name in scope if name not in {p["name"] for p in all_pages}])
    else:
        pages = all_pages
        legacy_pages = []
        missing_scope_pages = []

    inventory = {
        "generated_at": now,
        "scope": "NSC Dashboard React",
        "active_pages_count": len(active_pages),
        "certified_scope_pages_count": len(pages),
        "legacy_active_pages_count": len(legacy_pages),
        "missing_scope_pages_count": len(missing_scope_pages),
        "inactive_pages_count": len(inactive_pages),
        "active_components_count": len(active_components),
        "inactive_components_count": len(inactive_components),
        "certified_scope_pages": [{k:v for k,v in x.items() if not k.endswith("_details")} for x in pages],
        "legacy_active_pages": [{k:v for k,v in x.items() if not k.endswith("_details")} for x in legacy_pages],
        "missing_scope_pages": missing_scope_pages,
        "inactive_pages": [str(p.relative_to(ROOT)) for p in inactive_pages],
        "inactive_components": [str(p.relative_to(ROOT)) for p in inactive_components],
    }

    lineage = {
        "generated_at": now,
        "pages": [build_lineage(x) for x in pages],
        "components": [build_lineage(x) for x in components],
    }

    business_integrity = {
        "generated_at": now,
        "pages": [
            {
                "page": x["name"],
                "file": x["file"],
                "criticality": x["criticality"],
                "business_hardcode_findings": x["business_hardcode_findings"],
                "business_hardcode_details": x["business_hardcode_details"],
                "business_react_logic_findings": x["business_react_logic_findings"],
            }
            for x in pages
            if x["business_hardcode_findings"] or x["business_react_logic_findings"]
        ],
    }

    visual_integrity = {
        "generated_at": now,
        "pages": [
            {
                "page": x["name"],
                "file": x["file"],
                "visual_constant_findings": x["visual_constant_findings"],
                "visual_react_logic_findings": x["visual_react_logic_findings"],
            }
            for x in pages
            if x["visual_constant_findings"] or x["visual_react_logic_findings"]
        ],
    }

    certification = {
        "generated_at": now,
        "method": "Dashboard Audit Engine V2 - business/visual separation",
        "pages": [
            {
                "page": x["name"],
                "file": x["file"],
                "department": x["department"],
                "criticality": x["criticality"],
                "api_count": len(x["api_calls"]),
                "json_ref_count": len(x["json_refs"]),
                "business_hardcode_count": sum(x["business_hardcode_findings"].values()),
                "business_react_logic_count": sum(x["business_react_logic_findings"].values()),
                "visual_constant_count": sum(x["visual_constant_findings"].values()),
                "visual_react_logic_count": sum(x["visual_react_logic_findings"].values()),
                "dashboard_quality_score": x["dashboard_quality_score"],
                "certification_level": x["certification_level"],
                "certification_status": x["certification_status"],
            }
            for x in pages
        ],
    }

    legacy = {
        "generated_at": now,
        "count": len(legacy_pages),
        "missing_scope_pages": missing_scope_pages,
        "pages": [
            {
                "page": x["name"],
                "file": x["file"],
                "department": x["department"],
                "criticality": x["criticality"],
                "dashboard_quality_score": x["dashboard_quality_score"],
                "certification_level": x["certification_level"],
                "reason": "active_file_not_in_dashboard_scope_registry",
            }
            for x in legacy_pages
        ],
    }

    gold = {
        "generated_at": now,
        "gold_pages": [x for x in certification["pages"] if x["certification_level"] == "GOLD"],
        "silver_pages": [x for x in certification["pages"] if x["certification_level"] == "SILVER"],
        "bronze_pages": [x for x in certification["pages"] if x["certification_level"] == "BRONZE"],
        "red_pages": [x for x in certification["pages"] if x["certification_level"] == "RED"],
        "critical_A_summary": [x for x in certification["pages"] if x["criticality"] == "A"],
    }

    write_json(OUT_DIR, "dashboard_inventory_register.json", inventory)
    write_json(OUT_DIR, "dashboard_data_lineage_report.json", lineage)
    write_json(OUT_DIR, "dashboard_business_integrity.json", business_integrity)
    write_json(OUT_DIR, "dashboard_visual_integrity.json", visual_integrity)
    write_json(OUT_DIR, "dashboard_certification_matrix.json", certification)
    write_json(OUT_DIR, "dashboard_gold_certification.json", gold)
    write_json(OUT_DIR, "dashboard_legacy_pages.json", legacy)

    print("===== NSC DASHBOARD AUDIT ENGINE V2 DONE =====")
    print(f"Active pages discovered: {len(active_pages)}")
    print(f"Certified scope pages: {len(pages)}")
    print(f"Legacy active pages: {len(legacy_pages)}")
    print(f"Missing scope pages: {len(missing_scope_pages)}")
    print(f"Inactive/backup pages: {len(inactive_pages)}")
    print(f"Active components: {len(active_components)}")
    print(f"Inactive/backup components: {len(inactive_components)}")
    print(f"Reports written to: {OUT_DIR}")

if __name__ == "__main__":
    main()
