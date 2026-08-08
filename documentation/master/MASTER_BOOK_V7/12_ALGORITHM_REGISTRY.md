# Nova Star Capital
# Algorithm Registry

Classification: Master Book Governance
Version: V1.0
Status: Official Master Registry

---

# Purpose

The Algorithm Registry is the official inventory of every algorithm composing Nova Star Capital.

Its objectives are to:

- identify every algorithm;
- assign a unique identifier;
- track versions;
- define ownership;
- document dependencies;
- monitor lifecycle;
- support audits;
- support explainability.

Every algorithm entering NSC must first be registered here.

---

# Status Definitions

R&D

Prototype under development.

---

Shadow

Running without impacting production decisions.

---

PreProduction

Validated in simulated trading.

---

Production

Official production component.

---

Deprecated

Scheduled for removal.

---

Archived

Historical reference only.

---

# Domains

MARKET

DISCOVERY

LEARNING

VALIDATION

PORTFOLIO

CAPITAL

TREASURY

RISK

GOVERNANCE

EXECUTION

LONG_TERM

OPTIONS

BONDS

METALS

DEFENSIVE

OFFENSIVE

UI

INFRASTRUCTURE

SECURITY

FAMILY_OFFICE

COMMERCIAL

---

# Registry

| ID | Algorithm | Version | Domain | Status |
|----|-----------|----------|---------|---------|


---

# Core Engines

| ID | Algorithm | Version | Domain | Status |
|----|-----------|----------|---------|---------|
| ALG-0001 | Portfolio Engine | V3 | PORTFOLIO | Production |
| ALG-0002 | Capital Brain | V2 | CAPITAL | Production |
| ALG-0003 | Allocation Engine | V2 | CAPITAL | Production |
| ALG-0004 | Funding Engine | V2 | TREASURY | Production |
| ALG-0005 | Rebalance Engine | V2 | PORTFOLIO | Production |
| ALG-0006 | Portfolio State Engine | V2 | PORTFOLIO | Production |
| ALG-0007 | Capital State Engine | V2 | CAPITAL | Production |
| ALG-0008 | Governance Engine | V2 | GOVERNANCE | Production |
| ALG-0009 | Risk Engine | V2 | RISK | Production |
| ALG-0010 | Execution Engine | V2 | EXECUTION | Production |


---

# Market Intelligence

| ID | Algorithm | Version | Domain | Status |
|----|-----------|----------|---------|---------|
| ALG-0100 | Discovery Engine | V2 | DISCOVERY | Production |
| ALG-0101 | Binance Discovery | V1 | DISCOVERY | Production |
| ALG-0102 | MEXC Discovery | V1 | DISCOVERY | Production |
| ALG-0103 | CoinGecko Discovery | V1 | DISCOVERY | Production |
| ALG-0104 | CoinMarketCap Discovery | V1 | R&D |
| ALG-0105 | Bitpanda Discovery | V1 | PreProduction |
| ALG-0106 | Persistence Engine | V2 | LEARNING | Production |
| ALG-0107 | Market Memory | V1 | LEARNING | Production |
| ALG-0108 | Top Movers Engine | V2 | MARKET | Production |
| ALG-0109 | Top Losers Engine | V2 | MARKET | Production |


---

# Meta Intelligence

| ID | Algorithm | Version | Domain | Status |
|----|-----------|----------|---------|---------|
| ALG-0200 | Meta Ranking | V2 | VALIDATION | Production |
| ALG-0201 | Meta Validation | V2 | VALIDATION | Production |
| ALG-0202 | Opportunity Coverage | V1 | VALIDATION | Production |
| ALG-0203 | Discovery Accuracy | V1 | LEARNING | PreProduction |
| ALG-0204 | Executive Decision | V1 | GOVERNANCE | Production |
| ALG-0205 | Executive Brief | V1 | GOVERNANCE | Production |
| ALG-0206 | Opportunity Lifecycle | V1 | LEARNING | R&D |


---

# Crypto Intelligence

| ID | Algorithm | Version | Domain | Status |
|----|-----------|----------|---------|---------|
| ALG-0300 | Market Momentum | V2 | MARKET | Production |
| ALG-0301 | Social Momentum | V2 | MARKET | Production |
| ALG-0302 | Whale Tracking | V1 | MARKET | Production |
| ALG-0303 | Narrative Engine | V1 | MARKET | Production |
| ALG-0304 | Signal Voting | V2 | MARKET | Production |
| ALG-0305 | Position Manager | V2 | EXECUTION | Production |
| ALG-0306 | Position Sizing | V2 | CAPITAL | Production |
| ALG-0307 | Profitability Engine | V2 | LEARNING | Production |
| ALG-0308 | Worst Trades Engine | V2 | LEARNING | Production |
| ALG-0309 | Stop Loss Cooldown | V2 | RISK | Production |


---

# Roadmap Addendum — Performance Reporting Clarity

| ID | Item | Domain | Status |
|----|------|--------|--------|
| ROAD-PERF-001 | Rename “Realized PnL total” to “Net Realized PnL total” in Daily Review and UI to clarify that realized PnL is cumulative net PnL and can decrease after losing exits | REPORTING | To Do |
| ROAD-PERF-002 | Add Performance Ledger concept as future immutable source of truth for realized PnL, exits and trade history | REPORTING | Roadmap |
| ROAD-PERF-003 | Add Daily Review note explaining difference between gross wins, gross losses, net realized PnL and 24h realized PnL | REPORTING | To Do |
