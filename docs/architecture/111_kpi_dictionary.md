# 111 — KPI Dictionary

Every KPI in `ons_ops_reports` is defined below with its exact
calculation, source, and test reference.

## Agent Daily KPIs (`ons.report.agent.daily`)

| KPI | Field | Type | Calculation | Source |
|---|---|---|---|---|
| Total Calls | `total_calls` | Integer | COUNT(call_log) WHERE agent_id AND DATE(call_start) | `ons.call.log` |
| Inbound Calls | `inbound_calls` | Integer | COUNT WHERE direction='inbound' | `ons.call.log` |
| Outbound Calls | `outbound_calls` | Integer | COUNT WHERE direction='outbound' | `ons.call.log` |
| Answered Calls | `answered_calls` | Integer | COUNT WHERE disposition='answered' | `ons.call.log` |
| Missed Calls | `missed_calls` | Integer | COUNT WHERE disposition='missed' | `ons.call.log` |
| Avg Talk Duration (s) | `avg_talk_duration` | Integer | AVG(talk_duration) WHERE disposition='answered' | `ons.call.log` |
| Cases Created | `cases_created` | Integer | COUNT(case) WHERE intake_agent_id AND DATE(create_date) | `ons.case` |
| Cases Won | `cases_won` | Integer | COUNT WHERE is_won=True AND DATE(write_date) | `ons.case` |
| Revenue | `revenue` | Float | SUM(amount_total) WHERE payment_status='paid' AND billing_agent_id | `ons.case` |
| QA Average Score | `qa_avg_score` | Float | AVG(effective_score) WHERE agent_id AND state not in ('draft') | `ons.qa.result` |
| QA Evaluations | `qa_eval_count` | Integer | COUNT(qa_result) WHERE agent_id | `ons.qa.result` |
| QA Auto-Fail Count | `qa_auto_fail_count` | Integer | COUNT WHERE auto_fail=True | `ons.qa.result` |
| Dispatches Created | `dispatch_count` | Integer | COUNT(dispatch) WHERE case_id.intake_agent_id | `ons.dispatch` |

## Queue Daily KPIs (`ons.report.queue.daily`)

| KPI | Field | Type | Calculation | Source |
|---|---|---|---|---|
| Total Calls | `total_calls` | Integer | COUNT(call_log) WHERE queue_name AND DATE(call_start) | `ons.call.log` |
| Answered Calls | `answered_calls` | Integer | COUNT WHERE disposition='answered' | `ons.call.log` |
| Missed Calls | `missed_calls` | Integer | COUNT WHERE disposition='missed' | `ons.call.log` |
| Avg Talk Duration (s) | `avg_talk_duration` | Integer | AVG(talk_duration) WHERE answered | `ons.call.log` |
| Avg Wait Duration (s) | `avg_wait_duration` | Integer | AVG(wait_duration) | `ons.call.log` |
| Cases Created | `cases_created` | Integer | COUNT(interaction → case) WHERE queue_name | Via `ons.interaction.queue_name` → `ons.case.source_interaction_id` |

## Driver Daily KPIs (`ons.report.driver.daily`)

| KPI | Field | Type | Calculation | Source |
|---|---|---|---|---|
| Total Interactions | `total_interactions` | Integer | COUNT(interaction) WHERE primary_driver_id AND DATE(call_start) | `ons.interaction` |
| Cases Created | `cases_created` | Integer | COUNT(case) WHERE primary_driver_id AND DATE(create_date) | `ons.case` |
| Conversion Rate | `conversion_rate` | Float | cases_created / total_interactions × 100 | Computed |
