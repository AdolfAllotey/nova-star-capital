# Nova Star Capital
# Observability Standard

Version: V1.0
Status: Official Documentation
Classification: Engineering Library

---

# Purpose

This document defines the official observability standard for every Nova Star Capital engine.

Observability guarantees that every component can be monitored, audited, diagnosed and improved without ambiguity.

The observability model is built upon four pillars:

- Logs
- Metrics
- Traces
- Health

Every engine must implement these four capabilities.

---

# 1. Objectives

The observability platform must answer four questions.

What happened?

Why did it happen?

When did it happen?

Which engine produced the event?

---

# 2. Logging Standard

Every engine must produce structured logs.

Minimum fields:

- timestamp
- engine
- version
- execution id
- correlation id
- severity
- message

Optional fields:

- symbol
- portfolio
- strategy
- asset class
- duration
- latency
- CPU
- memory

---

# 3. Log Levels

DEBUG

Development diagnostics.

INFO

Normal execution.

WARNING

Unexpected but recoverable behaviour.

ERROR

Execution failed.

CRITICAL

Immediate operator attention required.

---

# 4. Metrics

Every engine publishes metrics.

Mandatory metrics:

- executions
- successful executions
- failed executions
- execution duration
- average duration
- memory usage
- CPU usage
- artifact count
- validation failures
- retries

Metrics must be cumulative.

---

# 5. Health Status

Every engine publishes a health status.

Possible values:

HEALTHY

DEGRADED

WAITING

RECOVERING

FAILED

STOPPED

Health must be updated continuously.

---

# 6. Heartbeat

Each engine publishes heartbeat information.

Minimum fields:

- engine
- version
- uptime
- last execution
- execution duration
- status
- timestamp

Missing heartbeat indicates an unhealthy engine.

---

# 7. Distributed Tracing

Every decision must remain traceable.

Each execution receives:

Trace ID

Correlation ID

Execution ID

These identifiers follow every artifact throughout the decision pipeline.

---

# 8. Audit Events

The following events must be recorded:

Engine started

Engine stopped

Validation failed

Retry

Recovery

Output published

Execution rejected

Governance veto

Risk veto

Execution completed

---

# 9. Latency Monitoring

Execution latency must be measured.

Metrics include:

Queue latency

Input latency

Processing latency

Validation latency

Publication latency

End-to-end latency

---

# 10. Data Freshness

Every consumed artifact is evaluated.

Possible states:

Fresh

Warning

Stale

Expired

Freshness rules are defined by each engine contract.

---

# 11. Alerts

Alerts should be generated for:

Repeated failures

Missing heartbeat

Stale inputs

High latency

Execution timeout

Validation failures

Unexpected stop

Safe Mode activation

---

# 12. Dashboards

The monitoring platform should expose:

Global System Health

Engine Status

Execution Timeline

Decision Pipeline

Portfolio Activity

Risk Activity

Governance Activity

Broker Activity

Discovery Activity

---

# 13. Historical Retention

Historical information should remain available.

Recommended retention:

Logs:
365 days

Metrics:
5 years

Audit events:
Permanent

Execution history:
Permanent

Portfolio decisions:
Permanent

---

# 14. Performance Indicators

Recommended KPIs:

Average execution duration

95th percentile latency

Failure rate

Retry rate

Validation success rate

Recovery success rate

Heartbeat availability

System uptime

---

# 15. Future Evolution

This standard has been designed for:

Prometheus

Grafana

OpenTelemetry

Jaeger

Elastic Stack

Cloud Monitoring

Kubernetes

Distributed clusters

---

# Final Principle

A system cannot be trusted if it cannot be observed.

Every important decision must be measurable.

Every anomaly must be diagnosable.

Every engine must explain its own behaviour.

