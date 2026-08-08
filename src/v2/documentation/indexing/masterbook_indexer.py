from pathlib import Path
import json
from src.v2.documentation.models.document import parse_document

ROOT = Path("/opt/nsc/app/documentation/master/MASTER_BOOK_V7")
OUT = Path("/opt/nsc/data/preprod/documentation")
OUT.mkdir(parents=True, exist_ok=True)


def build_index():
    docs = []
    for path in sorted(ROOT.glob("*.md")):
        if path.name.startswith("MASTER_BOOK_INDEX_AUTO"):
            continue
        if path.name.startswith("MASTER_BOOK_COVERAGE_REPORT"):
            continue
        docs.append(parse_document(path).to_dict())

    payload = {
        "documents_count": len(docs),
        "documents": docs,
    }

    (OUT / "masterbook_index.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload


if __name__ == "__main__":
    payload = build_index()
    print("Master Book index generated:", payload["documents_count"])
    print(OUT / "masterbook_index.json")
