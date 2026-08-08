from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shutil
import sys


APP_DIR = Path(
    os.getenv(
        "NSC_APP_DIR",
        "/opt/nsc/app",
    )
)

DATA_DIR = Path(
    os.getenv(
        "NSC_DATA_DIR",
        "/opt/nsc/data/preprod",
    )
)

RELEASE_GATE_PATH = (
    DATA_DIR
    / "releases"
    / "RC1"
    / "rc1_release_gate.json"
)

CURRENT_BASELINE_PATH = (
    DATA_DIR
    / "releases"
    / "RC1"
    / "current_baseline.json"
)

MASTER_STATUS_PATH = (
    DATA_DIR
    / "governance"
    / "nsc_master_status.json"
)

MASTER_HISTORY_PATH = (
    DATA_DIR
    / "governance"
    / "nsc_master_history.jsonl"
)

BEGIN_MARKER = (
    "<!-- BEGIN NSC OFFICIAL RELEASE STATUS -->"
)

END_MARKER = (
    "<!-- END NSC OFFICIAL RELEASE STATUS -->"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(
            f"Required file missing: {path}"
        )

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON file: {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected JSON object in: {path}"
        )

    return data


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def resolve_master_path() -> Path:
    forced_path = os.getenv("NSC_MASTER_PATH")

    if forced_path:
        return Path(forced_path)

    candidates = [
        APP_DIR / "docs" / "MASTER_NOVA_STAR_CAPITAL.md",
        APP_DIR / "docs" / "NOVA_STAR_CAPITAL_MASTER.md",
        APP_DIR / "docs" / "NSC_MASTER.md",
        APP_DIR / "MASTER_NOVA_STAR_CAPITAL.md",
        APP_DIR / "NOVA_STAR_CAPITAL_MASTER.md",
        APP_DIR / "NSC_MASTER.md",
        DATA_DIR / "governance" / "MASTER_NOVA_STAR_CAPITAL.md",
    ]

    existing = [
        path
        for path in candidates
        if path.is_file()
    ]

    if existing:
        return existing[0]

    return (
        APP_DIR
        / "docs"
        / "MASTER_NOVA_STAR_CAPITAL.md"
    )


def validate_release_gate(
    gate: dict[str, Any],
    pointer: dict[str, Any],
) -> None:
    failures: list[str] = []

    expected_values = {
        "release": "RC1",
        "decision": "APPROVED",
        "baseline_status": "FROZEN",
    }

    for key, expected in expected_values.items():
        if gate.get(key) != expected:
            failures.append(
                f"{key}={gate.get(key)!r}, "
                f"expected {expected!r}"
            )

    certification = gate.get(
        "certification",
        {},
    )

    if not isinstance(certification, dict):
        failures.append(
            "certification section missing"
        )
    else:
        if certification.get("status") != "PASS":
            failures.append(
                "certification.status is not PASS"
            )

        if (
            certification.get("name")
            != "RC1_END_TO_END_CERTIFIED"
        ):
            failures.append(
                "certification.name is invalid"
            )

        if certification.get("checks_total") != 38:
            failures.append(
                "certification.checks_total is not 38"
            )

        if certification.get("checks_passed") != 38:
            failures.append(
                "certification.checks_passed is not 38"
            )

        if certification.get("checks_failed") != 0:
            failures.append(
                "certification.checks_failed is not 0"
            )

        if certification.get("warnings_count") != 0:
            failures.append(
                "certification.warnings_count is not 0"
            )

        if certification.get("rc1_blocker") is not False:
            failures.append(
                "certification.rc1_blocker is not false"
            )

    allocation_policy = gate.get(
        "allocation_policy",
        {},
    )

    if not isinstance(allocation_policy, dict):
        failures.append(
            "allocation_policy section missing"
        )
    else:
        if (
            allocation_policy.get("model")
            != "DYNAMIC_POLICY_DRIVEN"
        ):
            failures.append(
                "allocation model is not "
                "DYNAMIC_POLICY_DRIVEN"
            )

        if (
            allocation_policy.get(
                "weights_permanently_fixed"
            )
            is not False
        ):
            failures.append(
                "weights_permanently_fixed "
                "is not false"
            )

        if (
            allocation_policy.get(
                "policy_frozen"
            )
            is not True
        ):
            failures.append(
                "policy_frozen is not true"
            )

    governance = gate.get(
        "governance",
        {},
    )

    if not isinstance(governance, dict):
        failures.append(
            "governance section missing"
        )
    else:
        if (
            governance.get("action_policy")
            != "SIMULATED_ONLY"
        ):
            failures.append(
                "governance.action_policy "
                "is not SIMULATED_ONLY"
            )

        if (
            governance.get(
                "real_execution_allowed"
            )
            is not False
        ):
            failures.append(
                "real execution is not disabled"
            )

    if (
        pointer.get("baseline_id")
        != gate.get("baseline", {}).get(
            "baseline_id"
        )
    ):
        failures.append(
            "current baseline pointer does not "
            "match the Release Gate"
        )

    if failures:
        formatted = "\n - ".join(failures)

        raise RuntimeError(
            "Release Gate validation failed:\n"
            f" - {formatted}"
        )


def percentage(
    value: Any,
    decimals: int = 4,
) -> str:
    try:
        number = float(value) * 100
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"

    return f"{number:.{decimals}f} %"


def bool_fr(value: Any) -> str:
    return "OUI" if value is True else "NON"


def build_master_section(
    gate: dict[str, Any],
    pointer: dict[str, Any],
    updated_at: str,
) -> str:
    certification = gate["certification"]
    allocation = gate["allocation_policy"]
    governance = gate["governance"]
    baseline = gate["baseline"]
    executive = gate.get(
        "executive_decision_snapshot",
        {},
    )
    scope = gate.get(
        "scope",
        {},
    )
    next_release = gate.get(
        "next_release",
        {},
    )

    snapshot = allocation.get(
        "certification_snapshot",
        {},
    )

    governed_bricks = scope.get(
        "governed_bricks",
        [],
    )

    governed_bricks_md = "\n".join(
        f"- {brick}"
        for brick in governed_bricks
    )

    excluded_components = scope.get(
        "excluded_components",
        {},
    )

    excluded_md = "\n".join(
        (
            f"- **{name}** : "
            f"`{details.get('status', 'unknown')}` — "
            f"{details.get('reason', 'n/a')}"
        )
        for name, details
        in excluded_components.items()
    )

    technical_debt = gate.get(
        "accepted_non_blocking_debt",
        [],
    )

    technical_debt_md = "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(
            technical_debt,
            start=1,
        )
    )

    planned_scope = next_release.get(
        "planned_scope",
        [],
    )

    planned_scope_md = "\n".join(
        f"- {item}"
        for item in planned_scope
    )

    return f"""{BEGIN_MARKER}

# Statut officiel des releases Nova Star Capital

Dernière mise à jour automatique : {updated_at}

---

## RC1 — Core Portfolio Engine

### Statut officiel

- **Release :** RC1
- **Composant :** Core Portfolio Engine
- **Décision :** APPROVED
- **Statut de baseline :** FROZEN
- **Certification :** RC1_END_TO_END_CERTIFIED
- **Résultat :** PASS
- **Date d’approbation :** {gate.get('approved_at')}
- **Baseline ID :** `{baseline.get('baseline_id')}`
- **Empreinte globale SHA-256 :** `{baseline.get('aggregate_sha256')}`

La RC1 du Core Portfolio Engine est officiellement
certifiée, approuvée et gelée.

Elle constitue la baseline institutionnelle de référence
pour les développements, audits de non-régression et
certifications ultérieurs.

Toute évolution fonctionnelle postérieure à cette
certification appartient à la RC2 ou à une release
ultérieure.

### Résultat de certification

- Contrôles exécutés : {certification.get('checks_total')}
- Contrôles réussis : {certification.get('checks_passed')}
- Contrôles en échec : {certification.get('checks_failed')}
- Warnings : {certification.get('warnings_count')}
- Blockers : {certification.get('blocking_failures_count')}
- RC1 blocker : {str(certification.get('rc1_blocker')).lower()}
- Artefacts archivés : {baseline.get('artifact_count')}

### Périmètre gouverné certifié

{governed_bricks_md}

### Politique d’allocation certifiée

Le modèle d’allocation RC1 est :

**DYNAMIC_POLICY_DRIVEN**

La RC1 ne certifie pas des poids permanents par classe
d’actifs.

Elle certifie une politique d’allocation dynamique pilotée
par :

- le régime de marché ;
- les signaux des briques ;
- les niveaux de conviction et de confiance ;
- les contraintes de risque ;
- les caps par famille ;
- les conditions cross-asset ;
- les règles de gouvernance ;
- le maintien du buffer de liquidités.

Éléments figés :

- logique d’allocation ;
- règles de normalisation ;
- familles d’actifs ;
- caps et contraintes de risque ;
- politique de cash ;
- exclusions de politique ;
- règles de gouvernance ;
- règles d’autorisation d’exécution.

Poids définitivement figés :

**{bool_fr(allocation.get('weights_permanently_fixed'))}**

Politique figée :

**{bool_fr(allocation.get('policy_frozen'))}**

### Photographie du run certifié

| Brique | Pondération |
|---|---:|
| Crypto | {percentage(snapshot.get('crypto'))} |
| Actions offensives | {percentage(snapshot.get('equities_offensive'))} |
| Actions défensives | {percentage(snapshot.get('equities_defensive'))} |
| Obligations | {percentage(snapshot.get('bonds'))} |
| Métaux précieux | {percentage(snapshot.get('precious_metals'))} |
| Cash | {percentage(allocation.get('cash_buffer'))} |

Ces pondérations sont une photographie du run certifié.
Elles ne constituent pas des cibles permanentes.

### Gouvernance et sécurité

- Action policy : `{governance.get('action_policy')}`
- Execution mode : `{governance.get('execution_mode')}`
- Exécution réelle autorisée : {str(governance.get('real_execution_allowed')).lower()}
- Exécution simulée autorisée : {str(governance.get('simulated_execution_allowed')).lower()}
- Rebalance automatique autorisé : {str(governance.get('automatic_rebalance_allowed')).lower()}
- Funding automatique autorisé : {str(governance.get('automatic_funding_allowed')).lower()}
- Validation manuelle obligatoire : {str(governance.get('manual_approval_required')).lower()}
- Transfert inter-pools automatique : {str(governance.get('automatic_inter_universe_transfer')).lower()}

### Executive Decision observée lors de la certification

- Décision : `{executive.get('decision')}`
- Brique recommandée : `{executive.get('recommended_brick')}`
- Montant recommandé : {executive.get('recommended_amount_eur')} EUR
- Confiance : {percentage(executive.get('confidence'), 2)}
- Execution posture : `{executive.get('execution_posture')}`
- Risk posture : `{executive.get('risk_posture')}`

Cette décision est une photographie de certification et
non une instruction permanente d’investissement.

### Composants exclus du périmètre gouverné RC1

{excluded_md}

Ces composants peuvent rester observables, mais ne
participent pas à l’allocation gouvernée RC1.

### Dette technique acceptée

{technical_debt_md}

Cette dette est non bloquante pour la RC1 et doit être
suivie pendant le hardening RC2 et la préparation de la
production.

---

## RC2 — Multi-Asset Engine

### Statut

**OUVERTE POUR CADRAGE ET DÉVELOPPEMENT**

### Objectif

Transformer le Core Portfolio Engine RC1 en un moteur
Multi-Asset intégrant les Options US comme classe d’actifs
gouvernée.

### Date cible de démarrage de la préproduction

**Au plus tard le 1er août 2026**

### Durée cible

**30 jours de préproduction**

### Périmètre prévu

{planned_scope_md}

### Sous-jacents Options prioritaires

- QQQ
- SPY
- NVDA
- AAPL
- MSFT
- AMZN
- META
- TSLA

### Règles de transition RC1 vers RC2

- la baseline RC1 reste immuable ;
- aucun artefact de la baseline RC1 ne doit être modifié ;
- toute évolution fonctionnelle doit être versionnée RC2 ;
- les tests de non-régression doivent comparer RC2 à RC1 ;
- l’exécution réelle demeure interdite ;
- les Options restent en observation tant que leur
  gouvernance RC2 n’est pas certifiée ;
- le passage en préproduction RC2 exige un Release Gate
  d’entrée dédié ;
- la sortie de RC2 exige une certification End-to-End
  Multi-Asset.

### Livrable attendu

**Multi-Asset Engine Approved**

---

## Roadmap institutionnelle

### RC1 — Core Portfolio Engine

**TERMINÉE — CERTIFIÉE — APPROUVÉE — GELÉE**

### RC2 — Multi-Asset Engine

**OUVERTE**

Objectif principal : intégration gouvernée des Options US
et préproduction Multi-Asset de 30 jours.

### RC3 — Production Readiness

Périmètre principal :

- Dashboard Production Readiness ;
- UI Data Integrity Audit ;
- alignement UI / API / artefacts backend ;
- suppression des données statiques ;
- audit runners et automatisations ;
- audit sécurité, logs, alertes et reprises ;
- audit OpenAI Codex ;
- tests de non-régression ;
- Go/No-Go production.

### RC4 — Controlled Production Launch

Périmètre principal :

- capital réel limité ;
- tailles de positions réduites ;
- validation humaine ;
- limites renforcées ;
- journalisation complète ;
- comparaison préproduction / production ;
- montée en charge progressive.

### RC5 — Institutional Scaling

Périmètre possible :

- multi-broker ;
- nouvelles classes d’actifs ;
- optimisation avancée du budget de risque ;
- stress tests ;
- reporting investisseurs ;
- architecture Family Office ;
- consolidation patrimoniale globale.

---

## Références officielles

- Release Gate JSON :
  `{RELEASE_GATE_PATH}`

- Baseline courante :
  `{CURRENT_BASELINE_PATH}`

- Baseline archivée :
  `{pointer.get('baseline_path')}`

- Master machine-readable :
  `{MASTER_STATUS_PATH}`

{END_MARKER}"""


def update_markdown_master(
    master_path: Path,
    section: str,
    timestamp: str,
) -> Path | None:
    master_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_path: Path | None = None

    if master_path.is_file():
        original = master_path.read_text(
            encoding="utf-8"
        )

        backup_path = master_path.with_name(
            master_path.name
            + f".bak_{timestamp}"
        )

        shutil.copy2(
            master_path,
            backup_path,
        )
    else:
        original = (
            "# Nova Star Capital — Master\n\n"
            "Document de référence institutionnel du projet.\n"
        )

    if (
        BEGIN_MARKER in original
        and END_MARKER in original
    ):
        before = original.split(
            BEGIN_MARKER,
            1,
        )[0].rstrip()

        after = original.split(
            END_MARKER,
            1,
        )[1].lstrip()

        updated = (
            before
            + "\n\n"
            + section
            + "\n\n"
            + after
        ).rstrip() + "\n"

    elif (
        BEGIN_MARKER in original
        or END_MARKER in original
    ):
        raise RuntimeError(
            "Only one Master marker was found. "
            "Manual inspection is required."
        )

    else:
        updated = (
            original.rstrip()
            + "\n\n"
            + section
            + "\n"
        )

    temporary = master_path.with_suffix(
        master_path.suffix + ".tmp"
    )

    temporary.write_text(
        updated,
        encoding="utf-8",
    )

    temporary.replace(master_path)

    return backup_path


def build_machine_status(
    gate: dict[str, Any],
    pointer: dict[str, Any],
    master_path: Path,
    updated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "project": "Nova Star Capital",
        "updated_at": updated_at,
        "master_document": {
            "path": str(master_path),
            "sha256": sha256_file(master_path),
        },
        "current_release": {
            "name": "RC1",
            "component": "Core Portfolio Engine",
            "status": "CERTIFIED_APPROVED_FROZEN",
            "decision": gate["decision"],
            "baseline_status": gate[
                "baseline_status"
            ],
            "baseline_id": gate[
                "baseline"
            ]["baseline_id"],
            "certification": gate[
                "certification"
            ]["name"],
            "certification_status": gate[
                "certification"
            ]["status"],
            "checks": {
                "total": gate[
                    "certification"
                ]["checks_total"],
                "passed": gate[
                    "certification"
                ]["checks_passed"],
                "failed": gate[
                    "certification"
                ]["checks_failed"],
                "warnings": gate[
                    "certification"
                ]["warnings_count"],
                "blockers": gate[
                    "certification"
                ][
                    "blocking_failures_count"
                ],
            },
            "allocation": {
                "model": gate[
                    "allocation_policy"
                ]["model"],
                "weights_permanently_fixed": gate[
                    "allocation_policy"
                ][
                    "weights_permanently_fixed"
                ],
                "policy_frozen": gate[
                    "allocation_policy"
                ]["policy_frozen"],
                "cash_buffer": gate[
                    "allocation_policy"
                ]["cash_buffer"],
            },
            "governance": gate["governance"],
            "aggregate_sha256": gate[
                "baseline"
            ]["aggregate_sha256"],
            "release_gate_path": str(
                RELEASE_GATE_PATH
            ),
            "baseline_path": pointer[
                "baseline_path"
            ],
        },
        "next_release": {
            "name": "RC2",
            "component": "Multi-Asset Engine",
            "status": "OPEN_FOR_SCOPING_AND_DEVELOPMENT",
            "preproduction_target_start": (
                "2026-08-01"
            ),
            "preproduction_duration_days": 30,
            "real_execution_allowed": False,
            "primary_scope": gate[
                "next_release"
            ]["planned_scope"],
            "priority_underlyings": [
                "QQQ",
                "SPY",
                "NVDA",
                "AAPL",
                "MSFT",
                "AMZN",
                "META",
                "TSLA",
            ],
        },
        "roadmap": {
            "RC1": (
                "CERTIFIED_APPROVED_FROZEN"
            ),
            "RC2": (
                "OPEN_FOR_SCOPING_AND_DEVELOPMENT"
            ),
            "RC3": "PLANNED_PRODUCTION_READINESS",
            "RC4": "PLANNED_CONTROLLED_PRODUCTION",
            "RC5": "PLANNED_INSTITUTIONAL_SCALING",
        },
    }


def append_history(
    payload: dict[str, Any],
) -> None:
    MASTER_HISTORY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MASTER_HISTORY_PATH.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )


def main() -> int:
    now = utc_now()
    updated_at = now.isoformat()
    timestamp = now.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    gate = read_json(
        RELEASE_GATE_PATH
    )

    pointer = read_json(
        CURRENT_BASELINE_PATH
    )

    validate_release_gate(
        gate,
        pointer,
    )

    master_path = resolve_master_path()

    section = build_master_section(
        gate,
        pointer,
        updated_at,
    )

    backup_path = update_markdown_master(
        master_path,
        section,
        timestamp,
    )

    machine_status = build_machine_status(
        gate,
        pointer,
        master_path,
        updated_at,
    )

    write_json(
        MASTER_STATUS_PATH,
        machine_status,
    )

    history_entry = {
        "event": "MASTER_UPDATED",
        "project": "Nova Star Capital",
        "updated_at": updated_at,
        "master_path": str(master_path),
        "master_sha256": sha256_file(
            master_path
        ),
        "backup_path": (
            str(backup_path)
            if backup_path
            else None
        ),
        "current_release": "RC1",
        "current_release_status": (
            "CERTIFIED_APPROVED_FROZEN"
        ),
        "baseline_id": gate[
            "baseline"
        ]["baseline_id"],
        "baseline_aggregate_sha256": gate[
            "baseline"
        ]["aggregate_sha256"],
        "next_release": "RC2",
        "next_release_status": (
            "OPEN_FOR_SCOPING_AND_DEVELOPMENT"
        ),
        "allocation_model": gate[
            "allocation_policy"
        ]["model"],
    }

    append_history(
        history_entry
    )

    print(
        "===== NSC MASTER UPDATE COMPLETE ====="
    )
    print(
        f"Master path: {master_path}"
    )
    print(
        "RC1 status: "
        "CERTIFIED_APPROVED_FROZEN"
    )
    print(
        "RC2 status: "
        "OPEN_FOR_SCOPING_AND_DEVELOPMENT"
    )
    print(
        "Allocation model: "
        f"{gate['allocation_policy']['model']}"
    )
    print(
        "Weights permanently fixed: "
        f"{gate['allocation_policy']['weights_permanently_fixed']}"
    )
    print(
        "Policy frozen: "
        f"{gate['allocation_policy']['policy_frozen']}"
    )
    print(
        "Baseline ID: "
        f"{gate['baseline']['baseline_id']}"
    )
    print(
        "Master SHA-256: "
        f"{sha256_file(master_path)}"
    )
    print(
        "Machine status: "
        f"{MASTER_STATUS_PATH}"
    )
    print(
        "Master history: "
        f"{MASTER_HISTORY_PATH}"
    )

    if backup_path:
        print(
            f"Backup: {backup_path}"
        )
    else:
        print(
            "Backup: none — new Master created"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"NSC MASTER UPDATE FAILED: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
