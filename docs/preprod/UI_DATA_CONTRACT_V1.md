# NSC PREPROD — UI Data Contract V1

Date: 2026-05-26  
Scope: J7 global preprod coherence audit  
Status: active reference before J11 strategy analysis

## 1. Principle

The UI must not invent or recompute institutional KPIs when an official source exists.

Pages must distinguish:
- portfolio/global KPIs
- rebalance/funding actions
- execution guard state
- real simulated engine orders
- equity curve history

## 2. Official source of truth by KPI

### Global KPIs

| KPI | Official source |
|---|---|
| Daily PnL | `/dashboard/v3.global.pnlDaily` |
| MTD PnL | `/dashboard/v3.global.pnlMTD` |
| YTD PnL | `/dashboard/v3.global.pnlYTD` |
| Global PnL | `/dashboard/v3.global.pnlGlobal` |
| Drawdown | `/dashboard/v3.global.drawdown` |
| Drawdown value | `/dashboard/v3.global.drawdownValue` |
| Portfolio confidence | `/dashboard/v3.global.confidence` or `/dashboard/v3.global.confidencePct` |
| Open positions | `/dashboard/v3.global.openPositions` |
| Protected bricks | `/dashboard/v3.global.protectedBricksCount` |
| Risk flags | `/dashboard/v3.global.riskFlags` |
| Governance mode | `/dashboard/v3.global.governanceMode` + `/governance/status` |

### Execution

| KPI | Official source |
|---|---|
| Global/master orders count | `/dashboard/v3.global.ordersCount` |
| Simulated engine orders | `/api/execution-orders.orders_count` |
| Blocked simulated orders | `/api/execution-orders.blocked_orders_count` |
| Simulated order symbols | `/api/execution-orders.symbols` |
| Execution guard / bridge state | `/api/execution-plan` |

Important:
- `/api/execution-plan` is not the real engine orders endpoint.
- `/api/execution-orders` exposes `/opt/nsc/data/preprod/trading/execution_plan.json.orders[]`.

### Funding

| KPI | Official source |
|---|---|
| Global funding summary | `/dashboard/v3.global.masterFundingByPool` |
| Detailed funding plan | `/api/funding-plan.funding_pools` |
| Manual funding required | `/api/funding-plan.funding_pools[].manual_transfer_required` |

### Rebalance

| KPI | Official source |
|---|---|
| Rebalance summary | `/api/rebalance-plan.summary` |
| Rebalance actions | `/api/rebalance-plan.actions` |
| Proposed actions count | `/api/rebalance-plan.summary.actions_proposed` |
| Deferred actions count | `/api/rebalance-plan.summary.actions_deferred` |

### Allocation / Portfolio

| KPI | Official source |
|---|---|
| Target allocation | `/api/portfolio-target.final_brick_weights` |
| Brick confidence | `/api/portfolio-target.brick_confidence` |
| Portfolio state | `/api/portfolio-state.bricks` |
| Funding pools target split | `/api/portfolio-state.funding_pools` |

Warning:
`/api/portfolio-state.bricks` currently has incomplete `current_weight` and `current_amount_eur`.
Until completed, UI drift derived from current fallback must be labelled as estimate/governed drift.

### Equity curve

| KPI | Official source |
|---|---|
| PnL chart history | `/dashboard/v3.equityCurve.history[].total_pnl_eur` |
| Realized PnL history | `/dashboard/v3.equityCurve.history[].realized_pnl_eur` |

Forbidden as source:
- `/dashboard/v3.equityCurve.history[].capital_observed_eur`
- `/dashboard/v3.equityCurve.history[].capital_engaged_eur`
- `/dashboard/v3.equityCurve.history[].live_exposure_ratio`
- `/dashboard/v3.equityCurve.history[].phase`
- `/dashboard/v3.equityCurve.history[].regime`

These fields are currently `0` or `UNKNOWN`.

## 3. Endpoint conventions

Use hyphenated API routes:
- `/api/portfolio-state`
- `/api/portfolio-target`
- `/api/rebalance-plan`
- `/api/funding-plan`
- `/api/execution-plan`
- `/api/execution-orders`

Do not use legacy aliases:
- `/api/portfolio_state`
- `/portfolio-target`

## 4. Page mapping

### DashboardV4

Allowed:
- `/dashboard/v3`
- `/api/portfolio-state`
- `/api/portfolio-target`

DashboardV4 may show:
- global KPIs from `/dashboard/v3.global`
- equity curve from `/dashboard/v3.equityCurve.history`
- allocation target/state from portfolio target/state

### ControlRoom

Allowed:
- `/dashboard/v3`
- `/api/portfolio-state`
- `/api/portfolio-target`
- `/api/execution-orders`
- preprod review endpoints

ControlRoom must display:
- Execution Orders from `/api/execution-orders.orders_count`
- Blocked Sim Orders from `/api/execution-orders.blocked_orders_count`

### RiskOverview

Allowed:
- `/api/portfolio-state`
- `/api/portfolio-target`
- `/api/rebalance-plan`
- `/api/funding-plan`
- `/governance/status`
- `/api/execution-plan`
- `/api/execution-orders`

RiskOverview must distinguish:
- Portfolio Actions = `/api/execution-plan.actions.length`
- Simulated Orders = `/api/execution-orders.orders_count`

### Portfolio

Allowed:
- `/api/portfolio-state`
- `/api/portfolio-target`
- `/api/rebalance-plan`
- `/api/funding-plan`

### FundingPools

Allowed:
- `/api/funding-plan`
- `/api/portfolio-target`

FundingPools must support:
- `funding_pools` as array
- `pools` as object fallback

### AllocationRebalance

Allowed:
- `/api/portfolio-state`
- `/api/portfolio-target`
- `/api/rebalance-plan`
- `/api/execution-plan`
- `/api/aggregator-audit`

`/api/execution-plan` remains execution guard / bridge audit only.

## 5. Current known gaps

1. `/api/portfolio-state.bricks` lacks real `current_weight` and `current_amount_eur`.
2. `equityCurve.history` has invalid capital/exposure/regime fields.
3. `/api/rebalance-plan.actions` has proposed actions with `action=null` and `delta_eur=null`.
4. Dashboard global `ordersCount` and `/api/execution-orders.orders_count` have different meanings and must stay visually distinct.

## 6. Rule before J11 strategy analysis

No new UI polish should be merged unless:
- endpoint sources comply with this contract
- build passes
- no legacy endpoint usage remains in active pages
- execution actions and execution orders are not mixed
