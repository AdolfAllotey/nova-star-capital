from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List

from src.v2.portfolio.adapters.crypto_adapter import (
    export_crypto_to_portfolio_input,
)
from src.v2.portfolio.adapters.defensive_equities_adapter import (
    export_defensive_equities_to_portfolio_input,
)
from src.v2.portfolio.adapters.offensive_equities_adapter import (
    export_offensive_equities_to_portfolio_input,
)
from src.v2.portfolio.adapters.options_us_adapter import (
    export_options_us_to_portfolio_input,
)


AdapterFunction = Callable[[], Dict[str, Any]]


def run_adapter(
    function: AdapterFunction,
    name: str,
) -> Dict[str, Any]:
    result = function()

    if not isinstance(result, dict):
        raise RuntimeError(
            f"{name} adapter returned a non-dict payload"
        )

    brick = result.get("brick")

    if not brick:
        raise RuntimeError(
            f"{name} adapter returned no brick identifier"
        )

    return {
        "adapter": name,
        "brick": brick,
        "enabled": result.get("enabled"),
        "target_weight": result.get("target_weight"),
        "confidence": result.get("confidence"),
        "regime": result.get("regime"),
        "source_file": result.get("source_file"),
    }


def main() -> int:
    adapters: List[tuple[str, AdapterFunction]] = [
        (
            "equities_defensive",
            export_defensive_equities_to_portfolio_input,
        ),
        (
            "equities_offensive",
            export_offensive_equities_to_portfolio_input,
        ),
        (
            "crypto",
            export_crypto_to_portfolio_input,
        ),
        (
            "options_us",
            export_options_us_to_portfolio_input,
        ),
    ]

    results = []
    errors = []

    for name, function in adapters:
        try:
            result = run_adapter(function, name)
            results.append(result)
            print(
                f"[portfolio_adapters][OK] "
                f"{name}: {result['brick']}"
            )
        except Exception as exc:
            errors.append({
                "adapter": name,
                "error": str(exc),
            })
            print(
                f"[portfolio_adapters][ERROR] "
                f"{name}: {exc}",
                file=sys.stderr,
            )

    report = {
        "status": "ok" if not errors else "failed",
        "results": results,
        "errors": errors,
    }

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
