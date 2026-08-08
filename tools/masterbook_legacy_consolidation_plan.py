from pathlib import Path

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

plan = """# Nova Star Capital
# Master Book Legacy 00-16 Consolidation Plan

Status: Proposed
Scope: MASTER_BOOK_V7

---

# Purpose

This document defines the proposed consolidation plan for historical duplicate documents in the 00–16 range.

No files are deleted by this plan.

---

# Proposed Canonical Structure

| Canonical Number | Proposed Canonical Document |
|---:|---|
| 00 | 00_EXECUTIVE_SUMMARY.md |
| 01 | 01_VISION_AND_PHILOSOPHY.md |
| 02 | 02_GLOBAL_ARCHITECTURE.md |
| 03 | 03_INVESTMENT_ENGINES.md |
| 04 | 04_DISCOVERY_FRAMEWORK.md |
| 05 | 05_PORTFOLIO_BRAIN.md |
| 06 | 06_EXECUTION_ARCHITECTURE.md |
| 07 | 07_GOVERNANCE.md |
| 08 | 08_FAMILY_OFFICE_ARCHITECTURE.md |
| 09 | 09_CRYPTO_DECISION_ENGINE.md |
| 10 | 10_SECURITY_INFRASTRUCTURE_ARCHITECTURE.md |
| 11 | 11_INFRASTRUCTURE.md |
| 12 | 12_ALGORITHM_REGISTRY.md |
| 13 | 13_ALGORITHM_CATALOG.md |
| 14 | 14_ALGORITHM_DEPENDENCIES.md |
| 15 | 15_ENGINE_RESPONSIBILITY_MATRIX.md |
| 16 | 16_DECISION_FLOW.md |

---

# Consolidation Rule

Historical alternatives should be archived only after confirming that their content has been merged or superseded.

---

# Do Not Delete

All legacy documents must be preserved until final manual validation.

---

# Next Step

Create a legacy archive folder and move non-canonical 00–16 documents after review.

"""

(ROOT / "MASTER_BOOK_LEGACY_00_16_CONSOLIDATION_PLAN.md").write_text(plan, encoding="utf-8")
print("Consolidation plan created:")
print(ROOT / "MASTER_BOOK_LEGACY_00_16_CONSOLIDATION_PLAN.md")
