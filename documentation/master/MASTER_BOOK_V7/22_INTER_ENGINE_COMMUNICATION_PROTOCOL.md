# Nova Star Capital
# Inter-Engine Communication Protocol

Version: V1.0
Status: Official Documentation
Classification: Engineering Library

---

# Purpose

This document defines how every engine inside Nova Star Capital communicates.

The objective is to guarantee:

- deterministic behaviour
- loose coupling
- complete auditability
- future scalability
- engine independence

No engine is allowed to directly manipulate another engine's internal state.

Every interaction must follow this protocol.

---

# 1. Design Principles

The communication model follows five principles.

1. Engines produce information.
2. Engines consume information.
3. Engines never modify another engine.
4. Information flows through standardized artifacts.
5. Every decision remains reproducible.

---

# 2. Communication Model

Every engine belongs to one of three communication categories.

## Input Engines

Input Engines produce observations.

Examples:

- Discovery Engine
- Market Regime Engine
- Whale Engine
- Sentiment Engine
- Macro Engine

## Decision Engines

Decision Engines transform observations into investment decisions.

Examples:

- Signal Voting Engine
- Position Sizing Engine
- Portfolio Brain
- Risk Engine
- Governance Engine

## Execution Engines

Execution Engines transform authorised decisions into operational actions.

Examples:

- Execution Engine
- Broker Adapter
- Portfolio Updater
- Fill Monitor

---

# 3. Communication Layers

Raw Market Data

↓

Normalized Data

↓

Scored Signals

↓

Portfolio Decisions

↓

Risk Validation

↓

Governance Validation

↓

Execution Orders

↓

Execution Results

↓

Portfolio State

Every layer must be auditable.

---

# 4. Allowed Communication

Valid communication example:

Discovery Engine

↓

Market Memory

↓

Meta Ranking

↓

Meta Validation

↓

Portfolio Engine

↓

Risk Engine

↓

Governance Engine

↓

Execution Engine

Invalid communication example:

Discovery Engine

↓

Execution Engine

Direct communication from discovery to execution is forbidden.

---

# 5. Standard Message Format

Every exchanged artifact should contain:

- timestamp
- producer engine
- producer version
- schema version
- generation time
- confidence
- source
- payload
- checksum
- trace id
- correlation id

This guarantees traceability and reproducibility.

---

# 6. Communication Rules

An engine may:

- read published artifacts;
- produce new artifacts;
- reject invalid artifacts;
- log inconsistencies.

An engine may never:

- overwrite another engine output;
- delete another engine output;
- modify another engine internal state;
- bypass governance;
- bypass risk validation.

---

# 7. Synchronization

Communication is asynchronous.

Each engine waits until required artifacts become available.

No engine should block the entire platform.

If required data is missing, the engine must enter a controlled waiting or degraded state.

---

# 8. Failure Handling

If an expected artifact is missing:

Engine status:

WAITING

If an artifact is corrupted:

Engine status:

INVALID_INPUT

If an artifact is stale:

Engine status:

STALE_INPUT

If a dependency is unavailable:

Engine status:

DEGRADED

No invalid artifact may enter the decision pipeline.

---

# 9. Version Compatibility

Every artifact must include:

- schema version;
- engine version;
- generation version.

Backward compatibility must be maintained whenever possible.

Breaking changes require:

- documentation;
- migration plan;
- validation;
- rollback plan.

---

# 10. Validation

Before consuming data, every engine should perform:

- schema validation;
- integrity validation;
- timestamp validation;
- checksum validation;
- freshness validation;
- policy validation when applicable.

Only validated artifacts may enter decision-making.

---

# 11. Audit Trail

Every communication should generate an audit trail containing:

- producer;
- consumer;
- artifact;
- timestamp;
- validation result;
- latency;
- decision impact.

This ensures every decision can be reconstructed later.

---

# 12. Security

Artifacts are treated as read-only once produced.

Checksums must be verified where possible.

Unauthorized modifications invalidate the artifact.

Sensitive artifacts must never expose:

- broker secrets;
- API keys;
- credentials;
- private tokens;
- production execution permissions.

---

# 13. Future Evolution

This protocol is designed to support:

- distributed engines;
- multiple execution nodes;
- cloud deployment;
- high availability;
- microservices;
- real-time streaming;
- event bus architecture.

---

# Final Principle

Engines communicate only through standardized artifacts.

No engine owns another engine.

Every decision remains reproducible.

