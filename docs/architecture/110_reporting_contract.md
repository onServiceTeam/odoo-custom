# 110 — Reporting & Analytics Contract

## Purpose

`ons_ops_reports` provides read-only reporting models that aggregate data
from the operational modules into pre-computed, queryable records.
Reports are exposed under **Operations → Management → Reports** (manager+).

## Design Principles

1. **Read-only aggregates** — report models are populated by scheduled
   computation, not by direct user entry.
2. **Stored computed fields** — heavy aggregation runs in a cron job
   (`_cron_recompute_daily`).  Dashboard-time reads remain fast.
3. **No data duplication** — aggregate records reference source models
   via relational or computed fields; raw data stays in source models.
4. **Source-of-truth alignment** — KPI definitions match the legacy
   `canonicalReportingService`, `threecx-reports`, and
   `agentMetricsService` where applicable.
5. **Test-backed** — every KPI has at least one deterministic test.

## Report Models

| Model | Grain | Purpose |
|---|---|---|
| `ons.report.agent.daily` | agent + date | Calls, conversions, revenue, QA score, dispatch count per agent per day |
| `ons.report.queue.daily` | queue + date | Call volume, dispositions, conversion rate per queue per day |
| `ons.report.driver.daily` | driver + date | Call volume and case creation per driver per day |

## Source Models → KPI Mapping

| KPI | Source Model(s) | Fields Used |
|---|---|---|
| Total Calls | `ons.call.log` | COUNT per agent/queue/date, direction |
| Answered Calls | `ons.call.log` | disposition = 'answered' |
| Missed Calls | `ons.call.log` | disposition = 'missed' |
| Avg Talk Duration | `ons.call.log` | AVG(talk_duration) |
| Cases Created | `ons.case` | COUNT per agent per day |
| Cases Won | `ons.case` | is_won = True |
| Cases Lost | `ons.case` | is_closed AND NOT is_won |
| Revenue (Billed) | `ons.case` (billing ext) | SUM(amount_total) WHERE payment_status = 'paid' |
| QA Average Score | `ons.qa.result` | AVG(effective_score) WHERE state != 'draft' |
| QA Auto-Fail Rate | `ons.qa.result` | COUNT(auto_fail) / COUNT(*) |
| Dispatches | `ons.dispatch` | COUNT per day |
| AI Cost | `ons.ai.run` | SUM(total_cost) |

## Time Handling

All date grouping uses `report_date` stored as `fields.Date`.
The cron job computes records for yesterday by default;
a `recompute_range(date_from, date_to)` method allows backfill.

## Permissions

- **Agent** (`group_ops_agent`): read own `ons.report.agent.daily` only
  (via record rule `report_date` agent domain).
- **Manager** (`group_ops_manager`): read all report models.
- **Admin** (`group_ops_admin`): full CRUD (for manual recompute/cleanup).

## Cron

| Job | Schedule | Model | Method |
|---|---|---|---|
| Daily Report Recompute | 05:00 UTC daily | `ons.report.agent.daily` | `_cron_recompute_daily` |

## Menu Placement

```
Operations (seq 3)
└── Management (seq 50, manager+)
    └── Reports (seq 60)
        ├── Agent Daily (seq 10)
        ├── Queue Daily (seq 20)
        └── Driver Daily (seq 30)
```
