from dataclasses import dataclass, asdict
from pathlib import Path
import re


@dataclass
class MasterBookDocument:
    number: int | None
    filename: str
    title: str
    classification: str
    status: str
    path: str
    word_count: int

    def to_dict(self):
        return asdict(self)


def parse_document(path: Path) -> MasterBookDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    number = None
    m = re.match(r"^(\d+)_", path.name)
    if m:
        number = int(m.group(1))

    title = path.stem
    classification = "unknown"
    status = "unknown"

    for line in lines[:30]:
        if line.startswith("# ") and title == path.stem:
            title = line.replace("# ", "").strip()
        if line.lower().startswith("classification:"):
            classification = line.split(":", 1)[1].strip()
        if line.lower().startswith("status:"):
            status = line.split(":", 1)[1].strip()

    words = len(re.findall(r"\w+", text))

    return MasterBookDocument(
        number=number,
        filename=path.name,
        title=title,
        classification=classification,
        status=status,
        path=str(path),
        word_count=words,
    )
