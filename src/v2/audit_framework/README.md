# Nova Star Capital Audit Framework

## Purpose

The Audit Framework provides a provider-independent and
traceable process for reviewing certified Nova Star Capital
releases and baselines.

## Core principles

- Certified baselines are immutable.
- Audit and remediation are separate activities.
- No auditor may modify code automatically.
- Every recommendation requires human validation.
- Audit packages are reproducible and checksum protected.
- Provider output must be normalized before governance use.
- Codex is an audit provider, not the framework itself.

## Foundation v1 status

Implemented:

- package structure;
- common constants;
- enumerations;
- exceptions;
- utility functions;
- audit data models;
- provider-independent interfaces;
- JSON schemas;
- framework registry;
- foundation tests.

Not yet implemented:

- artifact collection;
- baseline integrity validation;
- package manifest generation;
- Codex provider;
- report normalization;
- recommendation engine;
- engineering scoring calculations.

## Planned institutional flow

Architecture and governance

→ Artifact collection

→ Baseline validation

→ Audit package

→ Provider review

→ Report normalization

→ Recommendation classification

→ Human validation

→ Roadmap

→ Development

## Safety rule

The framework must never modify a certified baseline.

## Artifact Collector v1

Implemented:

- declarative RC1 artifact definitions;
- exact-path and recursive-pattern discovery;
- required versus optional artifact classification;
- read-only source handling;
- copy verification using SHA-256;
- source metadata stability checks;
- isolated audit package creation;
- JSON artifact inventory;
- JSON and Markdown collection reports;
- aggregate package fingerprint;
- framework registry and history updates.

The collector does not:

- validate the semantic integrity of the baseline;
- execute Codex or another provider;
- modify source artifacts;
- normalize an audit report;
- generate remediation actions.

## Baseline Validator v1

Implemented:

- package artifact presence checks;
- SHA-256 verification of every collected artifact;
- aggregate package fingerprint verification;
- baseline identifier consistency;
- RC1 release identity checks;
- frozen baseline validation;
- approved release decision validation;
- dynamic policy-driven allocation validation;
- frozen policy validation;
- non-frozen allocation weights validation;
- canonical RC1 aggregate SHA-256 consistency checks;
- certification artifact validation;
- Master RC1 and RC2 status consistency;
- JSON and Markdown validation reports;
- framework registry and history updates.

The validator does not:

- review source code quality;
- modify baseline artifacts;
- invoke Codex;
- fix validation failures;
- create roadmap recommendations.

## Audit Package Builder v1

Implemented:

- provider-independent RC1 audit package assembly;
- executive audit brief;
- audit scope definition;
- provider operating instructions;
- engineering review checklist;
- expected deliverables specification;
- recommendation classification policy;
- human-readable package index;
- machine-readable package readiness gate;
- complete package manifest;
- per-file SHA-256 checksum manifest;
- deterministic package-readiness fingerprint;
- registry and audit-history updates.

Package status:

`READY_FOR_PROVIDER_AUDIT`

The package builder does not:

- invoke Codex or another provider;
- modify the frozen RC1 baseline;
- apply recommendations;
- execute live or simulated trades;
- enable automatic remediation.

## Audit Package Builder v1

Implemented:

- provider-independent RC1 audit package assembly;
- executive audit brief;
- audit scope definition;
- provider operating instructions;
- engineering review checklist;
- expected deliverables specification;
- recommendation classification policy;
- human-readable package index;
- machine-readable package readiness gate;
- complete package manifest;
- per-file SHA-256 checksum manifest;
- deterministic package-readiness fingerprint;
- registry and audit-history updates.

Package status:

`READY_FOR_PROVIDER_AUDIT`

The package builder does not:

- invoke Codex or another provider;
- modify the frozen RC1 baseline;
- apply recommendations;
- execute live or simulated trades;
- enable automatic remediation.

## Package Determinism Hardening v1

Implemented:

- stable package-readiness fingerprint;
- exclusion of volatile readiness metadata from the readiness hash;
- preservation of the original package `created_at`;
- separate mutable `last_verified_at`;
- deterministic rebuild detection;
- duplicate `RC1_AUDIT_PACKAGE_READY` event prevention;
- independent package verification events;
- repeated-build idempotence tests.

Institutional rule:

Identical package evidence must produce an identical
`package_readiness_sha256`.

## Provider Adapter v1

Implemented:

- provider-independent adapter contract;
- generic provider capability model;
- generic execution-policy model;
- provider audit payload contract;
- Codex adapter v1;
- RC1 package compatibility validation;
- deterministic integrity verification;
- sensitive-filename detection;
- Codex dry-run payload generation;
- human approval requirement;
- explicit provider-execution prohibition;
- explicit source-write prohibition;
- explicit automatic-remediation prohibition;
- provider preparation registry and history records.

Provider status:

`OPENAI_CODEX = PREPARED_DRY_RUN`

No external provider invocation occurs in this phase.

## Codex Execution Gate v1

Implemented:

- explicit human approval;
- package-hash binding;
- payload-hash binding;
- unique execution-gate identity;
- gate expiration;
- single-use authorization;
- revocation support;
- consumed-state support;
- read-only execution policy;
- recommendation-only execution;
- no source writes;
- no live trading;
- no production credentials;
- no automatic remediation;
- no automatic provider invocation.

The gate may authorize one controlled future provider
invocation, but the invocation remains disabled until the
Codex Adapter phase is explicitly implemented.

## Audit Package Builder v1

Implemented:

- provider-independent RC1 audit package assembly;
- executive audit brief;
- audit scope definition;
- provider operating instructions;
- engineering review checklist;
- expected deliverables specification;
- recommendation classification policy;
- human-readable package index;
- machine-readable package readiness gate;
- complete package manifest;
- per-file SHA-256 checksum manifest;
- deterministic package-readiness fingerprint;
- registry and audit-history updates.

Package status:

`READY_FOR_PROVIDER_AUDIT`

The package builder does not:

- invoke Codex or another provider;
- modify the frozen RC1 baseline;
- apply recommendations;
- execute live or simulated trades;
- enable automatic remediation.
