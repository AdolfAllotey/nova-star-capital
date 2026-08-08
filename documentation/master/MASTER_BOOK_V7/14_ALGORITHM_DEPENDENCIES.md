# Nova Star Capital
# Algorithm Dependency Graph
Status: Official Documentation
Classification: Master Book Governance

Version : V1.0

Status : Official Documentation

---

# Purpose

This document describes every dependency between algorithms.

It defines:

- execution order
- data flow
- orchestration
- critical dependencies
- failure propagation
- ownership


==============================================================================
GLOBAL EXECUTION CHAIN
==============================================================================

Market Data

↓

Discovery Engine

↓

Market Memory

↓

Persistence Engine

↓

Meta Ranking

↓

Meta Validation

↓

Investment Engines

↓

Portfolio Engine

↓

Capital Brain

↓

Risk Engine

↓

Governance Engine

↓

Execution Engine

↓

Portfolio State

↓

Dashboard

↓

Executive Dashboard


==============================================================================
Portfolio Engine
==============================================================================

Consumes

Crypto Engine

Offensive Equities

Defensive Equities

Bonds

Precious Metals

Options

Long Term

Capital Brain

Funding Engine

Produces

portfolio_state.json

portfolio_target.json

rebalance_plan.json

Feeds

Risk Engine

Governance Engine

Dashboard

Family Office Dashboard

Executive Dashboard


==============================================================================
Discovery Engine
==============================================================================

Consumes

Binance

MEXC

CoinGecko

CoinMarketCap

Bitpanda

Produces

candidate universe

discovery score

Feeds

Persistence Engine

Market Memory

Meta Ranking


==============================================================================
Meta Ranking
==============================================================================

Consumes

Discovery

Persistence

Social

Momentum

Tradability

Produces

Meta Score

Tradability Verdict

Feeds

Meta Validation

Portfolio Engine

Executive Decision
