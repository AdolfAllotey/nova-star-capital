# Nova Star Capital
# Data Dictionary
Status: Official Documentation
Classification: Master Book Governance

Version : V1.0

Status : Official Documentation

------------------------------------------------------------------------------

Purpose

The Data Dictionary defines every JSON artifact produced and consumed by Nova Star Capital.

Every file must have:

- Owner
- Producer
- Consumers
- Update frequency
- Validation rules
- Criticality
- Backup policy

No undocumented artifact may exist.

------------------------------------------------------------------------------

==============================================================================
portfolio_state.json
==============================================================================

Owner

Portfolio Engine

Purpose

Represents the current state of the portfolio.

Produced by

Portfolio Engine

Consumed by

Dashboard

Risk Engine

Capital Brain

Funding Engine

Executive Dashboard

Update

Continuous

Criticality

★★★★★

Backup

Daily

Failure impact

Critical


==============================================================================
portfolio_target.json
==============================================================================

Owner

Portfolio Engine

Purpose

Official target allocation.

Produced by

Portfolio Engine

Consumed by

Rebalance Engine

Capital Brain

Risk Engine

Dashboard

Criticality

★★★★★


==============================================================================
capital_state.json
==============================================================================

Owner

Capital Brain

Purpose

Represents deployable capital.

Contains

Cash

Reserved Cash

Taxes

Safety Buffer

Available Capital

Consumers

Funding Engine

Portfolio Engine

Treasury

Criticality

★★★★★


==============================================================================
governance_engine_pro.json
==============================================================================

Owner

Governance Engine

Purpose

Official governance status.

Contains

Execution Mode

Hard Blocks

Kill Switch

Policies

Compliance

Consumers

Execution Engine

Dashboard

Executive Dashboard

Criticality

★★★★★


==============================================================================
execution_plan.json
==============================================================================

Owner

Execution Engine

Purpose

Final executable orders.

Contains

Orders

Broker

Priority

Sizing

Execution mode

Consumers

Broker Layer

Dashboard

Audit

Criticality

★★★★★


==============================================================================
discovery_candidates.json
==============================================================================

Owner

Discovery Engine

Purpose

Detected opportunities.

Contains

Assets

Discovery score

Sources

Narratives

Persistence

Consumers

Persistence Engine

Meta Ranking

Criticality

★★★★☆


==============================================================================
meta_ranking.json
==============================================================================

Owner

Meta Ranking Engine

Purpose

Official ranking.

Contains

Meta Score

Confidence

Tradability

Verdict

Consumers

Meta Validation

Portfolio Engine

Dashboard

Criticality

★★★★★


==============================================================================
meta_validation.json
==============================================================================

Owner

Meta Validation Engine

Purpose

Validate execution quality.

Contains

Alignment

Coverage

Drift

Quality

Consumers

Executive Dashboard

Audit

Criticality

★★★★★


==============================================================================
market_memory.json
==============================================================================

Owner

Market Memory

Purpose

Historical memory.

Contains

Observations

Persistence

Historical highs

Historical lows

Consumers

Discovery

Meta Ranking

Executive Decision

Criticality

★★★★☆


==============================================================================
funding_plan.json
==============================================================================

Owner

Funding Engine

Purpose

Capital deployment plan.

Contains

Transfers

Funding requirements

Available cash

Approval state

Consumers

Portfolio Engine

Dashboard

Treasury

Criticality

★★★★★


==============================================================================
rebalance_plan.json
==============================================================================

Owner

Portfolio Engine

Purpose

Portfolio corrections.

Contains

Drift

Actions

Priority

Expected allocation

Consumers

Execution Engine

Dashboard

Capital Brain

Criticality

★★★★★
