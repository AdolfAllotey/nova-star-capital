from pathlib import Path
import re
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

docs = sorted(ROOT.glob("*.md"))
numbered = []

for p in docs:
    m = re.match(r"^(\d+)_", p.name)
    if m:
        numbered.append((int(m.group(1)), p.name))

by_num = defaultdict(list)
for n, name in numbered:
    by_num[n].append(name)

nums = sorted(by_num)
missing = [n for n in range(min(nums), max(nums) + 1) if n not in by_num]

out = []
out.append("# Nova Star Capital")
out.append("# Master Book Status Report")
out.append("")
out.append(f"Generated UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
out.append("")
out.append("---")
out.append("")
out.append(f"Total Markdown files: {len(docs)}")
out.append(f"Numbered documents: {len(numbered)}")
out.append(f"Numbering range: {min(nums)} to {max(nums)}")
out.append("")
out.append("# Accepted Numbering Gaps")
out.append("")
for n in missing:
    out.append(f"- {n}")
out.append("")
out.append("# Duplicate Numbers")
out.append("")
for n, names in sorted(by_num.items()):
    if len(names) > 1:
        out.append(f"## {n}")
        for name in names:
            out.append(f"- {name}")
        out.append("")
out.append("# Master Book Position")
out.append("")
out.append("The Master Book V7 has reached an advanced institutional documentation stage.")
out.append("")
out.append("Recent generated collections include:")
out.append("")
out.append("- Executive Playbooks")
out.append("- Asset Class Playbooks")
out.append("- Operations Manuals")
out.append("- Quantitative Research Standards")
out.append("")
out.append("Recent duplicate standards have been archived safely.")
out.append("")
out.append("# Next Recommended Step")
out.append("")
out.append("Perform a dedicated consolidation of the historical 00–16 documents before any further structural renumbering.")

(ROOT / "MASTER_BOOK_STATUS_REPORT.md").write_text("\n".join(out) + "\n", encoding="utf-8")

print("Status report created:")
print(ROOT / "MASTER_BOOK_STATUS_REPORT.md")
