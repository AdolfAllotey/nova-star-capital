from pathlib import Path
import subprocess

BASE = Path("data/equities_offensive")

REQUIRED = [
    BASE / "execution" / "simulated_fills.jsonl",
    BASE / "state" / "positions.json",
    BASE / "state" / "exposure_snapshot.json",
]

def ensure_files():
    for p in REQUIRED:
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("", encoding="utf-8")

def run(cmd):
    subprocess.run(cmd, check=False)

def main():
    ensure_files()
    run(["python", "src/v2/equities_offensive/execution/position_tracker.py"])
    run(["python", "src/v2/equities_offensive/ui/ui_bundle_builder.py"])

if __name__ == "__main__":
    main()
