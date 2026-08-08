# Nova Star Capital
# Decision Hierarchy Standard

Version: V1.0
Status: Official Documentation
Classification: Investment Governance

---

# Purpose

Nova Star Capital is composed of multiple decision engines.

This standard defines the authority and priority of each engine.

When conflicting decisions occur, this hierarchy determines the final outcome.

---

# Fundamental Rule

Safety always overrides profitability.

Risk always overrides opportunity.

Platform integrity always overrides execution.

---

# Decision Priority

Level 1

Emergency Controls

Highest Authority

Includes:

Kill Switch

Emergency Stop

Trading Pause

Read Only Mode

Manual Override

No lower-level component may bypass these controls.

---

Level 2

Risk Engine

Authority:

Accept

Reduce

Reject

Terminate

Risk decisions are final.

---

Level 3

Portfolio Brain

Responsibilities:

Global allocation

Portfolio balance

Cross-asset exposure

Correlation control

Capital deployment

---

Level 4

Capital Allocator

Responsibilities:

Position sizing

Available capital

Reserve capital

Liquidity management

---

Level 5

Market Regime Engine

Responsibilities:

Risk On

Risk Off

Neutral

Defensive

Aggressive

---

Level 6

Meta Scoring Engine

Responsibilities:

Global opportunity ranking

Confidence calculation

Composite scoring

---

Level 7

Signal Voting Engine

Responsibilities:

Aggregate strategy outputs

Confirm signals

Reject weak signals

---

Level 8

Discovery Engine

Responsibilities:

Market scanning

Candidate generation

Trend identification

Opportunity detection

---

Level 9

Strategy Engines

Examples:

Momentum

Breakout

Mean Reversion

Trend Following

Defensive

Income

Options

Metals

Bonds

---

Level 10

Execution Engine

Responsibilities:

Order creation

Broker routing

Execution monitoring

Fill validation

The Execution Engine executes decisions.

It does not create investment decisions.

---

# Conflict Resolution

When multiple engines disagree:

Higher priority prevails.

Lower priority adapts.

No ambiguity shall remain.

---

# Manual Intervention

Manual intervention is exceptional.

Manual actions shall:

be documented

be justified

remain auditable

never bypass emergency protections

---

# Explainability

Every final decision shall identify:

Winning engine

Supporting engines

Rejected engines

Reasoning

Timestamp

Version

---

# Governance

Hierarchy changes require:

Architecture review

Risk review

Governance approval

Documentation update

Version increment

---

# Final Principle

Authority follows responsibility.

Risk protects capital.

Execution follows validated decisions.

