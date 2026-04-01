# 14 — Reporting & Metrics Catalog

**Date:** 2026-04-01  
**Source:** onService middleware analysis (MyPerformance, TeamPerformance, ReportsPage, OperationsInsights)  

---

## KPI Reference Table

Below is every metric currently tracked in the middleware, mapped to its Odoo data source.

### Agent-Level KPIs (My Performance)

| Metric | Middleware Source | Odoo Source | Type |
|--------|-----------------|-------------|------|
| Calls Handled Today | `call_logs` count WHERE agent | `ons.interaction` domain `[('agent_id','=',uid), ('create_date','>=',today)]` | Counter |
| Average Handle Time | `call_logs` avg(duration) | `ons.interaction` avg(`duration`) | Duration |
| Intakes Completed | `submissions` count WHERE agent, status=completed | `ons.interaction` domain `[('state','=','completed')]` | Counter |
| Sessions Closed | `service_sessions` count WHERE agent, status=completed | `ons.session` domain `[('state','=','completed')]` | Counter |
| Revenue Collected | `payment_transactions` sum(amount) WHERE agent | `account.payment` sum(`amount`) WHERE agent | Currency |
| QA Score Average | `qa_evaluations` avg(score) WHERE agent | `ons.qa.evaluation` avg(`overall_score`) | Percentage |
| QA Pass Rate | `qa_evaluations` count(pass)/count(*) | `ons.qa.evaluation` count/domain | Percentage |
| Cases Resolved | `cases` count WHERE agent, status=resolved | `ons.case` domain `[('state','in',['resolved','closed'])]` | Counter |
| Dispatch Success Rate | `workmarket_assignments` completed/total | `ons.dispatch` completed/total | Percentage |
| First Call Resolution | derived: sessions where 1 call → resolved | `ons.case` WHERE interaction_count=1, state=resolved | Percentage |

### Team-Level KPIs (Team Performance)

| Metric | Odoo Source | Granularity |
|--------|-------------|-------------|
| Total Calls | `ons.interaction` count | Daily/Weekly/Monthly |
| Total Revenue | `account.payment` sum | Daily/Weekly/Monthly |
| Average QA Score | `ons.qa.evaluation` avg | Per Agent, Team |
| Open Case Count | `ons.case` WHERE state != closed | Real-time |
| Pending Dispatch | `ons.dispatch` WHERE state = pending | Real-time |
| SLA Compliance | `ons.case` WHERE closed within SLA | Percentage |
| Agent Utilization | `ons.session` hours/available_hours | Per Agent |
| Conversion Rate | `crm.lead` won/total | Monthly |
| Average Revenue per Call | revenue / call count | Monthly |
| Customer Satisfaction | `ons.qa.evaluation` external score | Monthly |

### Operations Insights

| Metric | Odoo Source | Notes |
|--------|-------------|-------|
| Call Volume by Hour | `ons.interaction` group by hour | Heatmap chart |
| Call Volume by Day | `ons.interaction` group by day | Bar chart |
| Top Call Drivers | `ons.call.driver` count | Pie chart |
| Revenue by Service Type | `ons.session` group by type | Stacked bar |
| Dispatch by Region | `ons.dispatch` group by zip | Map/geo chart |
| Agent Ranking | composite KPI score | Leaderboard |
| Queue Wait Time | `ons.interaction` avg(queue_seconds) | Line chart |
| Abandonment Rate | `ons.interaction` WHERE state=abandoned | Percentage |

---

## Dashboard Implementation Plan

### Approach: Odoo Spreadsheet + Custom Dashboard Action

Odoo 19 includes `spreadsheet` module for Enterprise. Since we're on Community,
we use:

1. **Graph views** on each model — built-in, no code required
2. **Pivot views** for cross-tab analysis
3. **Custom client action** for the home dashboard (Owl component)
4. **Scheduled computations** for derived metrics (stored compute fields)

### Dashboard Architecture

```
┌─────────────────────────────────────────────────┐
│  Operations Dashboard (ir.actions.client)        │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Calls    │ │ Revenue  │ │ QA Score │        │
│  │ Today: 47│ │ $12,340  │ │ 87.2%    │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ┌─────────────────────┐ ┌───────────────────┐  │
│  │ Call Volume (24h)   │ │ Top Call Drivers  │  │
│  │ ▁▂▃▅▇█▇▅▃▂▁        │ │ ■ Lockout 34%    │  │
│  │ graph view embed    │ │ ■ Plumbing 22%   │  │
│  └─────────────────────┘ │ ■ HVAC 18%       │  │
│                          └───────────────────┘  │
│  ┌─────────────────────────────────────────┐    │
│  │ My Active Cases (kanban embed)          │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Stored Compute Fields for Performance

To avoid expensive on-the-fly calculations, key metrics should be stored
via scheduled cron jobs:

| Field | Model | Frequency | Computation |
|-------|-------|-----------|-------------|
| `daily_call_count` | `res.users` (extend) | Hourly | Count interactions today |
| `weekly_revenue` | `res.users` (extend) | Hourly | Sum payments this week |
| `qa_score_avg` | `res.users` (extend) | Daily | Avg QA score last 30 days |
| `daily_call_volume` | `ons.ops.metric` (new) | Hourly | Count by hour bucket |
| `daily_revenue` | `ons.ops.metric` (new) | Hourly | Sum by day |

The `ons.ops.metric` model stores pre-aggregated time-series data for
fast dashboard rendering.

---

## Odoo Report Types

| Report Type | Use Case | Module |
|-------------|----------|--------|
| Graph View | Per-model analytics | Each model's XML |
| Pivot View | Cross-tab drill-down | Each model's XML |
| QWeb Report | Printable PDF reports | `ons_ops_reports` |
| Client Action | Interactive dashboard | `ons_ops_shell` |
| Spreadsheet | Ad-hoc analysis | Enterprise only (defer) |

---

## Migration Note

The middleware currently renders charts via React (Recharts/Chart.js on the
frontend). Odoo's built-in `graph` and `pivot` views handle most cases. For
the real-time dashboards (live calls, agent status), we'll need custom Owl
components with polling — similar to the existing middleware approach but
using Odoo RPC instead of REST API calls.
