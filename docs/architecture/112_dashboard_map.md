# 112 — Dashboard Map

## Menu Structure

```
Operations → Management → Reports (seq 60, manager+)
├── Agent Daily   (seq 10) — list + pivot + graph
├── Queue Daily   (seq 20) — list + pivot + graph
└── Driver Daily  (seq 30) — list + pivot + graph
```

## Agent Daily Dashboard

| View | Purpose |
|---|---|
| List | Date, Agent, Calls, Answered, Revenue, QA Avg, Cases Created — sortable, filterable |
| Pivot | Agent × Date / Agent × KPI matrix |
| Graph | Bar chart — calls/revenue by agent; Line chart — QA trend |

### Filters
- Today, Yesterday, This Week, This Month, Last 30 Days
- My Reports (agent_id = current user)

### Group By
- Agent, Date, Date:Week, Date:Month

## Queue Daily Dashboard

| View | Purpose |
|---|---|
| List | Date, Queue, Total Calls, Answered, Missed, Avg Talk, Avg Wait, Cases |
| Pivot | Queue × Date matrix |
| Graph | Bar — call volume by queue; Line — answer rate trend |

### Filters
- Today, Yesterday, This Week, This Month

### Group By
- Queue, Date, Date:Week, Date:Month

## Driver Daily Dashboard

| View | Purpose |
|---|---|
| List | Date, Driver, Interactions, Cases Created, Conversion Rate |
| Pivot | Driver Category × Date |
| Graph | Bar — interactions by driver; Line — conversion rate trend |

### Filters
- Today, Yesterday, This Week, This Month

### Group By
- Driver, Driver Category, Date, Date:Week, Date:Month

## Data Freshness

Reports are recomputed daily at 05:00 UTC by `_cron_recompute_daily`.
Managers can trigger a manual recompute for any date range via the
`action_recompute_wizard` action (admin only).
