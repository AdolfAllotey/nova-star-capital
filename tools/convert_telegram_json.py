# tools/convert_telegram_json.py
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

def load_groups_list():
    path = os.getenv("TELEGRAM_GROUPS_FILE")
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            groups = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        if groups:
            return groups
    raw = os.getenv("TELEGRAM_GROUPS", "")
    return [g.strip() for g in raw.split(",") if g.strip()]

def main():
    # charge env (local v2 + racine si présent)
    here = os.path.dirname(__file__)
    load_dotenv(os.path.join(here, "..", "src", "v2", ".env"), override=False)
    load_dotenv(os.path.join(here, "..", ".env"), override=False)

    in_path = os.path.join(here, "..", "src", "v2", "data", "social", "telegram_data.json")
    in_path = os.path.realpath(in_path)
    if not os.path.isfile(in_path):
        print(f"Fichier introuvable: {in_path}")
        return 1

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # si c'est déjà un dict par nom, on ne fait rien
    if isinstance(data.get("groups"), dict):
        print("Déjà au format dict par nom — rien à faire.")
        return 0

    if not isinstance(data.get("groups"), list):
        print("Format inattendu: 'groups' n'est ni list ni dict.")
        return 1

    groups_list = load_groups_list()
    if not groups_list:
        print("Impossible de retrouver la liste des groupes (TELEGRAM_GROUPS[_FILE]).")
        return 1

    old = data["groups"]
    new_groups = {}
    for idx, messages in enumerate(old):
        name = groups_list[idx] if idx < len(groups_list) else f"Group_{idx}"
        new_groups[name] = messages

    data["groups"] = new_groups
    # met à jour le timestamp
    data["scraped_at"] = datetime.now(timezone.utc).isoformat()

    tmp = in_path + ".converted.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, in_path)
    print(f"✅ Conversion OK → {in_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
