from pathlib import Path
import re

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

docs = sorted(ROOT.glob("*.md"))

groups = {}
for p in docs:
    m = re.match(r"^(\d+)_", p.name)
    if not m:
        continue
    n = int(m.group(1))
    bucket = f"{(n//20)*20:03d}-{(n//20)*20+19:03d}"
    groups.setdefault(bucket, []).append(p.name)

out = [
    "# Nova Star Capital",
    "# Master Book Coverage Report",
    "",
    "---",
    "",
    f"Total markdown documents: {len(docs)}",
    "",
]

for bucket, names in sorted(groups.items()):
    out.append(f"## {bucket}")
    out.append("")
    for name in names:
        out.append(f"- {name}")
    out.append("")

(ROOT / "MASTER_BOOK_COVERAGE_REPORT.md").write_text("\n".join(out), encoding="utf-8")

print("Coverage report created:")
print(ROOT / "MASTER_BOOK_COVERAGE_REPORT.md")
print("Total docs:", len(docs))
