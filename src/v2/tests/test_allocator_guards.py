import json, importlib.util, sys
from pathlib import Path

BASE = Path("/root/src/v2")
CFG = BASE / "config" / "capital_allocator.config.json"

def load_pipeline():
    spec = importlib.util.spec_from_file_location("run_pipeline", str(BASE / "run_pipeline.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod

def test_profit_guard_triggered():
    rp = load_pipeline()
    # profit trop gros vs balance
    res = rp.allocator_run_direct(balance=1000, profit=800, bot_pct=None, bench_pct=None, dry_run=True)
    assert res["status"] == "profit_guard_triggered"

def test_no_transfer_under_trigger():
    rp = load_pipeline()
    # sous le seuil 10k
    res = rp.allocator_run_direct(balance=9000, profit=200, bot_pct=None, bench_pct=None, dry_run=True)
    assert res["status"] == "no_transfer"

def test_allocated_preview_ok():
    rp = load_pipeline()
    # au-dessus du seuil, min profit ok
    res = rp.allocator_run_direct(balance=12000, profit=200, bot_pct=12, bench_pct=5, dry_run=True)
    assert res["status"] in ("allocated_preview", "allocated")
    assert "splits" in res
