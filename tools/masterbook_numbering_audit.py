from pathlib import Path
import re
from collections import defaultdict

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")

numbered = []
for p in ROOT.glob("*.md"):
    m = re.match(r"^(\d+)_", p.name)
    if m:
        numbered.append((int(m.group(1)), p.name))

by_num = defaultdict(list)
for n, name in numbered:
    by_num[n].append(name)

nums = sorted(by_num)
missing = [n for n in range(min(nums), max(nums) + 1) if n not in by_num]
duplicates = {n: names for n, names in by_num.items() if len(names) > 1}

print("===== MASTER BOOK NUMBERING AUDIT =====")
print("Numbered docs:", len(numbered))
print("Min:", min(nums))
print("Max:", max(nums))
print("Missing numbers:", missing if missing else "none")
print()
print("Duplicates:")
if duplicates:
    for n, names in duplicates.items():
        print(n, names)
else:
    print("none")

print()
print("Potential semantic duplicates:")
keywords = defaultdict(list)
for n, name in numbered:
    stem = re.sub(r"^\d+_", "", name).replace(".md", "")
    key = stem.replace("_STANDARD", "").replace("_PLAYBOOK", "").replace("_MANUAL", "")
    keywords[key].append(name)

for key, names in sorted(keywords.items()):
    if len(names) > 1:
        print(key, "=>", names)
