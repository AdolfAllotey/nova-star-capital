"""
Legacy/compat entrypoint.
If your services start via src.v2.api.app, this file can remain minimal.
"""

from __future__ import annotations

def main() -> int:
    # Keep import-safe; real startup handled elsewhere.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
