from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.v2.equities_offensive.finalize_equities_state import main as finalize_equities_state
from src.v2.equities_offensive.runner import ensure_preprod_artifacts, run
from src.v2.utils.file_utils import save_json
from src.v2.utils.time_utils import utc_now_iso
from src.v2.validation.contracts import validate_contract


def main():
    import argparse

    ap = argparse.ArgumentParser(description="NSC Equities Offensive Runner (Skeleton V0)")
    ap.add_argument("--inputs", default="/opt/nsc/data/preprod/equities_offensive/inputs.json")
    ap.add_argument("--out", default="/opt/nsc/data/preprod/equities_offensive/out")
    args = ap.parse_args()

    res = run(inputs_path=args.inputs, out_dir=args.out)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


ensure_preprod_artifacts()

if __name__ == "__main__":
    rc = main()
    subprocess.run(
        [sys.executable, "src/v2/portfolio/offensive_equity_curve_updater.py"],
        check=False,
    )
    finalize_equities_state()
    raise SystemExit(rc)
