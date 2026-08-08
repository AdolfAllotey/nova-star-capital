from pathlib import Path
import re
from collections import defaultdict

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

legacy = []
for p in sorted(ROOT.glob("*.md")):
    m = re.match(r"^(\d+)_", p.name)
    if m and int(m.group(1)) <= 16:
        legacy.append((int(m.group(1)), p))

groups = defaultdict(list)
for n, p in legacy:
    groups[n].append(p)

out = [
    "# Nova Star Capital",
    "# Master Book Legacy 00-16 Audit",
    "",
    "---",
    "",
    "This report maps historical duplicate documents in the 00–16 range.",
    "",
]

for n in sorted(groups):
    files = groups[n]
    out.append(f"# {n:02d}")
    out.append("")
    for p in files:
        title = ""
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break
        except Exception:
            pass
        out.append(f"- {p.name} — {title}")
    out.append("")

(ROOT / "MASTER_BOOK_LEGACY_00_16_AUDIT.md").write_text("\n".join(out), encoding="utf-8")

print("Legacy audit created:")
print(ROOT / "MASTER_BOOK_LEGACY_00_16_AUDIT.md")
print("Legacy docs:", len(legacy))
print("Duplicate numbers:", {k: len(v) for k, v in groups.items() if len(v) > 1})
