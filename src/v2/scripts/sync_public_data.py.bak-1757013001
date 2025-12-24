import os, shutil, datetime

# Dossiers source (pipeline) -> destination (UI servie par Vite)
SRC = "src/v2/data"
DST = "src/v2/interface/react/public/data"

# Sous-dossiers à synchroniser (si l’un n’existe pas, on saute)
SUBFOLDERS = ["reports", "risk", "simulation", "meta", "airdrops"]

def _copy_tree(src, dst):
    if not os.path.exists(src):
        return 0
    os.makedirs(dst, exist_ok=True)
    copied = 0
    for root, _, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out_dir = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(out_dir, exist_ok=True)
        for f in files:
            if not f.endswith((".json", ".txt", ".html")):
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(out_dir, f))
            copied += 1
    return copied

def sync_public_data():
    total = 0
    os.makedirs(DST, exist_ok=True)
    # on copie aussi les JSON à la racine de SRC (ex: daily_report.json)
    for f in os.listdir(SRC):
        if f.endswith(".json"):
            shutil.copy2(os.path.join(SRC, f), os.path.join(DST, f))
            total += 1
    # puis les sous-dossiers
    for sub in SUBFOLDERS:
        total += _copy_tree(os.path.join(SRC, sub), os.path.join(DST, sub))
    # petit marqueur de santé
    with open(os.path.join(DST, "_last_sync.txt"), "w") as fp:
        fp.write(datetime.datetime.now(timezone.utc).isoformat() + "Z\n")
    return total

if __name__ == "__main__":
    n = sync_public_data()
    print(f"[sync_public_data] {n} fichiers mis à jour.")