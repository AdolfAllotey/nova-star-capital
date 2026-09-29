from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.v2.equities_offensive.universe.dual_universe_builder_v2 import (
    CorePolicy,
    TacticalPolicy,
    derive_metrics,
    select_dual_universe,
)


DEFAULT_ROOT = Path(
    "/opt/nsc/data/preprod/equities_offensive"
)


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"JSON object required: {path}"
        )

    return payload


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )

    tmp = Path(tmp_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp, path)
        os.chmod(path, 0o660)

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if tmp.exists():
            tmp.unlink()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def validate_governance_chain(
    *,
    primary_path: Path,
    secondary_path: Path,
    validation_path: Path,
    gate_path: Path,
    run_report_path: Path,
) -> dict[str, str]:
    for artifact in (
        primary_path,
        secondary_path,
        validation_path,
        gate_path,
        run_report_path,
    ):
        if not artifact.is_file():
            raise RuntimeError(
                f"Governance artifact missing: {artifact}"
            )

    primary_sha = file_sha256(
        primary_path
    )
    secondary_sha = file_sha256(
        secondary_path
    )
    validation_sha = file_sha256(
        validation_path
    )
    gate_sha = file_sha256(
        gate_path
    )

    validation = load_json(
        validation_path
    )
    gate = load_json(
        gate_path
    )
    run_report = load_json(
        run_report_path
    )

    if validation.get("status") != "validated":
        raise RuntimeError(
            "Cross-source validation is not validated"
        )

    inputs = validation.get(
        "input_artifacts"
    )

    if not isinstance(inputs, dict):
        raise RuntimeError(
            "Validation input_artifacts missing"
        )

    if (
        inputs.get("primary_sha256")
        != primary_sha
    ):
        raise RuntimeError(
            "Primary provider SHA mismatch"
        )

    if (
        inputs.get("secondary_sha256")
        != secondary_sha
    ):
        raise RuntimeError(
            "Secondary provider SHA mismatch"
        )

    if (
        Path(str(inputs.get("primary", "")))
        != primary_path
    ):
        raise RuntimeError(
            "Validation primary path mismatch"
        )

    if (
        Path(str(inputs.get("secondary", "")))
        != secondary_path
    ):
        raise RuntimeError(
            "Validation secondary path mismatch"
        )

    if gate.get("status") != "pass":
        raise RuntimeError(
            "Quality gate status is not pass"
        )

    if gate.get("decision") != "PASS":
        raise RuntimeError(
            "Quality gate decision is not PASS"
        )

    promotion = gate.get("promotion")

    if not isinstance(promotion, dict):
        raise RuntimeError(
            "Quality gate promotion contract missing"
        )

    if (
        promotion.get(
            "authorized_by_quality_gate"
        )
        is not True
    ):
        raise RuntimeError(
            "Quality gate did not authorize"
        )

    if (
        gate.get("input_sha256")
        != validation_sha
    ):
        raise RuntimeError(
            "Validation SHA mismatch at quality gate"
        )

    if (
        Path(str(gate.get("input_artifact", "")))
        != validation_path
    ):
        raise RuntimeError(
            "Quality gate input path mismatch"
        )

    if (
        run_report.get("status")
        != "quality_gate_passed"
    ):
        raise RuntimeError(
            "Validation run did not pass quality gate"
        )

    if (
        run_report.get(
            "quality_gate_decision"
        )
        != "PASS"
    ):
        raise RuntimeError(
            "Validation run gate decision is not PASS"
        )

    artifacts = run_report.get(
        "artifacts"
    )

    if not isinstance(artifacts, dict):
        raise RuntimeError(
            "Validation run artifacts missing"
        )

    expected_paths = {
        "primary": primary_path,
        "secondary": secondary_path,
        "validation": validation_path,
        "quality_gate": gate_path,
    }

    for key, expected_path in expected_paths.items():
        if (
            Path(str(artifacts.get(key, "")))
            != expected_path
        ):
            raise RuntimeError(
                f"Run report {key} path mismatch"
            )

    expected_hashes = {
        "primary_sha256": primary_sha,
        "secondary_sha256": secondary_sha,
        "validation_sha256": validation_sha,
        "quality_gate_sha256": gate_sha,
    }

    for key, expected_sha in expected_hashes.items():
        if artifacts.get(key) != expected_sha:
            raise RuntimeError(
                f"Run report {key} mismatch"
            )

    return {
        "primary_sha256": primary_sha,
        "secondary_sha256": secondary_sha,
        "validation_sha256": validation_sha,
        "quality_gate_sha256": gate_sha,
        "validation_generated_at": str(
            validation.get("generated_at") or ""
        ),
        "quality_gate_generated_at": str(
            gate.get("generated_at") or ""
        ),
        "validation_run_generated_at": str(
            run_report.get("generated_at") or ""
        ),
    }


def generation_id_for(
    *,
    market_session: str,
    reference_time: str,
    provider_generated_at: str,
) -> str:
    material = "|".join(
        (
            market_session,
            reference_time,
            provider_generated_at,
        )
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()



def build_universe_candidates(
    *,
    shortlist: dict[str, Any],
    provider: dict[str, Any],
    governance: dict[str, str],
    provider_path: Path,
    tactical_output: Path,
    core_status: str,
    tactical_status: str,
    schema_version: str,
    shadow_only: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    universe = str(
        shortlist.get("universe") or ""
    ).strip()

    if universe != "nasdaq_core":
        raise RuntimeError(
            "Unexpected shortlist universe: "
            f"{universe!r}"
        )

    expected_symbols = {
        str(symbol).strip().upper()
        for symbol in shortlist.get(
            "symbols",
            [],
        )
        if str(symbol).strip()
    }

    if not expected_symbols:
        raise RuntimeError(
            "Shortlist is empty"
        )

    provider_status = str(
        provider.get("status") or ""
    ).strip().lower()

    if provider_status != "healthy":
        raise RuntimeError(
            "Provider is not healthy: "
            f"{provider_status!r}"
        )

    provider_session = str(
        provider.get("market_session") or ""
    ).strip()

    provider_reference_time = str(
        provider.get("reference_time") or ""
    ).strip()

    provider_generated_at = str(
        provider.get("generated_at") or ""
    ).strip()

    if not provider_session:
        raise RuntimeError(
            "Missing provider market_session"
        )

    if not provider_reference_time:
        raise RuntimeError(
            "Missing provider reference_time"
        )

    if not provider_generated_at:
        raise RuntimeError(
            "Missing provider generated_at"
        )

    provider_symbols = (
        provider.get("symbols") or {}
    )

    if not isinstance(
        provider_symbols,
        dict,
    ):
        raise RuntimeError(
            "Provider symbols must be an object"
        )

    metrics = derive_metrics(
        provider_symbols,
        expected_symbols=expected_symbols,
    )

    core_policy = CorePolicy()
    tactical_policy = TacticalPolicy()

    result = select_dual_universe(
        metrics,
        core_policy=core_policy,
        tactical_policy=tactical_policy,
    )

    core_symbols = result["core"]
    tactical_symbols = result["tactical"]

    overlap = (
        set(core_symbols)
        & set(tactical_symbols)
    )

    if overlap:
        raise RuntimeError(
            "Core/Tactical overlap detected: "
            + ", ".join(sorted(overlap))
        )

    generated_at = utc_now_iso()

    generation_id = generation_id_for(
        market_session=provider_session,
        reference_time=provider_reference_time,
        provider_generated_at=provider_generated_at,
    )

    common = {
        "schema_version": schema_version,
        "generation_id": generation_id,
        "engine": (
            "offensive_dual_universe_builder_v2"
        ),
        "status": core_status,
        "source": str(
            provider.get("provider")
            or provider.get("source")
            or "unknown"
        ),
        "market_scope": "NASDAQ",
        "asset_type": "individual_equities",
        "etf_allowed": False,
        "source_market_universe": universe,
        "provider_artifact": str(
            provider_path
        ),
        "provider_generated_at": (
            provider_generated_at
        ),
        "governance_provenance": governance,
        "reference_time": (
            provider_reference_time
        ),
        "market_session": provider_session,
        "ts": generated_at,
        "broker_executed": False,
        "pipeline_executed": False,
        "signals_executed": False,
    }

    core_policy_payload = {
        "direct_execution_allowed": False,
        "shadow_only": shadow_only,
    }

    tactical_policy_payload = {
        "direct_execution_allowed": False,
        "requires_tactical_risk_engine": True,
        "reduced_sizing_required": True,
        "sector_concentration_control_required": True,
        "enhanced_exit_protection_required": True,
        "shadow_only": shadow_only,
    }

    core_payload = {
        **common,
        "universe": (
            "nasdaq_offensive_core"
        ),
        "universe_role": "core",
        "count_in": len(
            expected_symbols
        ),
        "count_out": len(
            core_symbols
        ),
        "symbols": core_symbols,
        "filters": policy_dict(
            core_policy
        ),
        "metrics": {
            symbol: metrics[symbol]
            for symbol in core_symbols
        },
        "tactical_watchlist_path": str(
            tactical_output
        ),
        "execution_policy": (
            core_policy_payload
        ),
    }

    tactical_payload = {
        **common,
        "status": tactical_status,
        "universe": (
            "nasdaq_offensive_tactical"
        ),
        "universe_role": (
            "tactical_high_volatility"
        ),
        "count_in": len(
            expected_symbols
        ),
        "count_out": len(
            tactical_symbols
        ),
        "symbols": tactical_symbols,
        "filters": policy_dict(
            tactical_policy
        ),
        "metrics": {
            symbol: metrics[symbol]
            for symbol in tactical_symbols
        },
        "execution_policy": (
            tactical_policy_payload
        ),
        "risk_limits_pending": {
            "max_tactical_positions": None,
            "max_tactical_weight": None,
            "position_size_factor": None,
        },
    }

    return core_payload, tactical_payload


def write_pair_with_rollback(
    *,
    core_output: Path,
    core_payload: dict[str, Any],
    tactical_output: Path,
    tactical_payload: dict[str, Any],
) -> None:
    if (
        core_payload.get("generation_id")
        != tactical_payload.get("generation_id")
    ):
        raise RuntimeError(
            "Shadow pair generation mismatch"
        )

    if (
        core_payload.get("market_session")
        != tactical_payload.get("market_session")
    ):
        raise RuntimeError(
            "Shadow pair market_session mismatch"
        )

    if (
        core_payload.get("reference_time")
        != tactical_payload.get("reference_time")
    ):
        raise RuntimeError(
            "Shadow pair reference_time mismatch"
        )

    core_before = (
        core_output.read_bytes()
        if core_output.exists()
        else None
    )

    tactical_before = (
        tactical_output.read_bytes()
        if tactical_output.exists()
        else None
    )

    try:
        atomic_write_json(
            core_output,
            core_payload,
        )

        atomic_write_json(
            tactical_output,
            tactical_payload,
        )

    except BaseException:
        if core_before is None:
            core_output.unlink(
                missing_ok=True
            )
        else:
            core_output.write_bytes(
                core_before
            )

        if tactical_before is None:
            tactical_output.unlink(
                missing_ok=True
            )
        else:
            tactical_output.write_bytes(
                tactical_before
            )

        raise


def policy_dict(
    policy: CorePolicy | TacticalPolicy,
) -> dict[str, Any]:
    return {
        "min_average_dollar_volume20": (
            policy.min_average_dollar_volume20
        ),
        "min_relative_strength_6m": (
            policy.min_relative_strength_6m
        ),
        "min_return60": policy.min_return60,
        "max_atr_pct14": policy.max_atr_pct14,
        "minimum_history_rows": (
            policy.minimum_history_rows
        ),
    }


def _main_locked() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
    )

    parser.add_argument(
        "--provider",
        default=None,
    )

    parser.add_argument(
        "--secondary",
        default=None,
    )

    parser.add_argument(
        "--validation",
        default=None,
    )

    parser.add_argument(
        "--quality-gate",
        default=None,
    )

    parser.add_argument(
        "--validation-run",
        default=None,
    )

    parser.add_argument(
        "--core-output",
        default=None,
    )

    parser.add_argument(
        "--tactical-output",
        default=None,
    )

    args = parser.parse_args()

    root = Path(args.root)

    shortlist_path = (
        root
        / "universe/shortlist_nasdaq.json"
    )

    provider_path = Path(
        args.provider
        or (
            root
            / "market/providers/"
            "market_data_yfinance_v1.json"
        )
    )

    secondary_path = Path(
        args.secondary
        or (
            root
            / "market/providers/"
            "market_data_massive_v1.json"
        )
    )

    validation_path = Path(
        args.validation
        or (
            root
            / "market/providers/"
            "cross_source_validation_v1.json"
        )
    )

    gate_path = Path(
        args.quality_gate
        or (
            root
            / "market/providers/"
            "provider_quality_gate_v1.json"
        )
    )

    validation_run_path = Path(
        args.validation_run
        or (
            root
            / "market/providers/"
            "provider_validation_run_v1.json"
        )
    )

    core_output = Path(
        args.core_output
        or (
            root
            / "universe/"
            "universe_filtered_v2_shadow.json"
        )
    )

    tactical_output = Path(
        args.tactical_output
        or (
            root
            / "universe/"
            "tactical_watchlist_v2_shadow.json"
        )
    )

    governance = validate_governance_chain(
        primary_path=provider_path,
        secondary_path=secondary_path,
        validation_path=validation_path,
        gate_path=gate_path,
        run_report_path=validation_run_path,
    )

    shortlist = load_json(shortlist_path)
    provider = load_json(provider_path)

    core_payload, tactical_payload = (
        build_universe_candidates(
            shortlist=shortlist,
            provider=provider,
            governance=governance,
            provider_path=provider_path,
            tactical_output=tactical_output,
            core_status="shadow_only",
            tactical_status="shadow_only",
            schema_version="2.0-shadow",
            shadow_only=True,
        )
    )

    write_pair_with_rollback(
        core_output=core_output,
        core_payload=core_payload,
        tactical_output=tactical_output,
        tactical_payload=tactical_payload,
    )

    print(
        json.dumps(
            {
                "status": "shadow_only",
                "market_session": (
                    provider_session
                ),
                "reference_time": (
                    provider_reference_time
                ),
                "core": core_symbols,
                "tactical": (
                    tactical_symbols
                ),
                "core_output": str(
                    core_output
                ),
                "tactical_output": str(
                    tactical_output
                ),
            },
            indent=2,
        )
    )

    return 0


def main() -> int:
    lock_path = Path(
        "/run/lock/"
        "nsc-equities-provider-refresh.lock"
    )

    lock_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with lock_path.open("r") as lock_handle:
        fcntl.flock(
            lock_handle.fileno(),
            fcntl.LOCK_SH,
        )

        try:
            return _main_locked()
        finally:
            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_UN,
            )


if __name__ == "__main__":
    raise SystemExit(main())
