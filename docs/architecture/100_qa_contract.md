# 100 — QA Contract: Operational Quality Assurance Engine

## Purpose
Define what gets reviewed, how scoring works, what states a QA evaluation passes through,
and ownership/permissions for the `ons_ops_qa` addon.

---

## 1  What Gets Reviewed

| Subject            | Source Model       | Required? | Notes |
|--------------------|--------------------|-----------|-------|
| Call               | `ons.call.log`     | Yes       | Primary review object – needs answered call with agent |
| Interaction        | `ons.interaction`  | Optional  | Linked via call → interaction chain |
| Case               | `ons.case`         | Optional  | Linked if case exists for the interaction |

**Trigger:** A QA evaluation is created against a **call log** record.
The call must have `disposition = 'answered'` and `agent_id` set.

---

## 2  QA Result Structure

### 2.1  `ons.qa.result` — the main evaluation record

| Field | Type | Notes |
|-------|------|-------|
| `call_log_id` | M2O `ons.call.log` | Required, primary link |
| `agent_id` | M2O `res.users` | Related from call log – the agent being evaluated |
| `evaluator_id` | M2O `res.users` | Who created / graded this evaluation |
| `call_type` | Selection | first_time_intake / callback / verification / billing / subscription / transfer / voicemail / outbound |
| `final_score` | Float(5,2) | 0–100 weighted score |
| `auto_fail` | Boolean | Auto-fail rule triggered |
| `auto_fail_reasons` | Text | Newline-separated reasons |
| `score_cap` | Integer | If auto-fail, max allowed score (typically 40) |
| `state` | Selection | draft / graded / in_review / reviewed / ack_pending / acknowledged / disputed |
| `needs_human_review` | Boolean | Confidence below threshold or auto-fail |
| `human_review_reasons` | Text | Why human review flagged |

### 2.2  Scoring breakdown

| Field | Type | Notes |
|-------|------|-------|
| `phase_scores_json` | Text | JSON of per-phase breakdowns |
| `rule_results_json` | Text | JSON of individual rule results |
| `global_violations_json` | Text | JSON of global rule violations |
| `operational_summary` | Text | Machine/evaluator summary |
| `coaching_summary` | Text | Summary for coaching |

### 2.3  Review fields

| Field | Type | Notes |
|-------|------|-------|
| `reviewed_at` | Datetime | When manager reviewed |
| `reviewed_by` | M2O `res.users` | Manager |
| `review_notes` | Text | Manager's notes |
| `override_score` | Float(5,2) | Manager's override (blank = accept final_score) |

### 2.4  Acknowledgement fields

| Field | Type | Notes |
|-------|------|-------|
| `acknowledged_at` | Datetime | When agent signed off |
| `dispute_reason` | Text | If agent disputes |

### 2.5  Links

| Field | Type | Notes |
|-------|------|-------|
| `interaction_id` | M2O `ons.interaction` | Via call_log or explicit |
| `case_id` | M2O `ons.case` | If case exists |
| `finding_ids` | O2M `ons.qa.finding` | Detail findings |
| `coaching_id` | M2O `ons.qa.coaching` | Linked coaching artifact |
| `ai_run_ids` | O2M `ons.ai.run` | AI runs for this QA |

---

## 3  QA Finding Structure

### `ons.qa.finding` — individual rule check result

| Field | Type | Notes |
|-------|------|-------|
| `result_id` | M2O `ons.qa.result` | Parent |
| `rule_key` | Char | Rule identifier |
| `rule_name` | Char | Display name |
| `phase` | Char | Which phase (opening, foundations, etc.) |
| `finding_type` | Selection | behavior / forbidden_word / policy_violation / sequence |
| `severity` | Selection | low / medium / high / critical |
| `status` | Selection | hit / missed / partial / not_applicable / needs_review |
| `evidence_quote` | Text | Transcript excerpt |
| `evidence_start_ms` | Integer | Timestamp in recording |
| `evidence_end_ms` | Integer | End timestamp |
| `evidence_speaker` | Selection | agent / customer / unknown |
| `points_earned` | Float | Points for this finding |
| `points_possible` | Float | Max points available |
| `needs_human_review` | Boolean | Flagged for verification |
| `verified_by` | M2O `res.users` | Who verified evidence |
| `verified_at` | Datetime | When verified |
| `verification_notes` | Text | Verifier notes |

---

## 4  Rule/Rubric Definitions

### `ons.qa.rule` — scoring rules

| Field | Type | Notes |
|-------|------|-------|
| `key` | Char unique | Rule identifier (e.g. `greeting_proper`) |
| `name` | Char | Display name |
| `rule_type` | Selection | required / forbidden / sequence / call_control |
| `check_type` | Selection | phrase_present / phrase_absent / sequence_order / talk_time / manual |
| `phase` | Char | Which call phase |
| `points` | Integer | Points if passed |
| `penalty_points` | Integer | Penalty if failed |
| `is_auto_fail` | Boolean | Triggers auto-fail on violation |
| `score_cap` | Integer | Max score if auto-fail |
| `coaching_text` | Text | Coaching explanation for rule |
| `coaching_examples` | Text | Good/bad examples |
| `is_active` | Boolean | |

### `ons.qa.call.type` — call type definitions with phase weights

| Field | Type | Notes |
|-------|------|-------|
| `key` | Char unique | e.g. `first_time_intake` |
| `name` | Char | Display name |
| `phases` | Text | Comma-separated ordered phases |
| `phase_weights_json` | Text | JSON: `{"call_control": 15, "opening": 10, ...}` summing to 100 |
| `detection_priority` | Integer | Higher checked first |
| `is_active` | Boolean | |

### `ons.qa.call.type.rule` — maps rules to call types

| Field | Type | Notes |
|-------|------|-------|
| `call_type_id` | M2O `ons.qa.call.type` | |
| `rule_id` | M2O `ons.qa.rule` | |
| `phase` | Char | Override phase from rule |
| `applicability` | Selection | required / optional / forbidden / not_applicable |
| `points_override` | Integer | Override rule default |
| `is_active` | Boolean | |

---

## 5  Coaching Structure

### `ons.qa.coaching` — coaching artifact linked to a QA result

| Field | Type | Notes |
|-------|------|-------|
| `result_id` | M2O `ons.qa.result` | Parent evaluation |
| `agent_id` | M2O `res.users` | Related from result |
| `priority` | Selection | low / medium / high / critical |
| `quality` | Selection | rich / generic / insufficient_data |
| `summary` | Text | 2-4 sentence overview |
| `strengths_json` | Text | JSON array of what went well |
| `improvements_json` | Text | JSON array of improvement areas |
| `action_steps_json` | Text | JSON array of action items |
| `example_phrases_json` | Text | JSON of better phrase examples |
| `manager_notes` | Text | Manager addendum |
| `ai_run_id` | M2O `ons.ai.run` | If AI-generated |
| `state` | Selection | draft / published / acknowledged |

---

## 6  Ownership & Permissions

| Role | Can do |
|------|--------|
| **Agent** | View own QA results (read), acknowledge results |
| **Manager** | Create/edit QA results, review, override scores, publish coaching, view all agents |
| **Admin** | Full CRUD on all QA objects + rule/rubric management |

---

## 7  Invariants

1. A QA result MUST reference a call log with an agent.
2. `final_score` is always 0–100. `override_score` replaces it for aggregation when set.
3. Auto-fail caps the score — it does not zero it.
4. Acknowledgement can only happen after state reaches `ack_pending` or `reviewed`.
5. Disputed results revert to `in_review` for manager re-evaluation.
6. AI never owns the final score directly — it produces a draft that enters the review flow.
7. Coaching artifacts are advisory only — no business field writes.
8. Evidence timestamps reference the call recording, not Odoo timestamps.

---

## 8  Module Dependencies

```
ons_ops_qa depends:
  ├── ons_ops_3cx       (ons.call.log)
  ├── ons_ops_ai        (ons.ai.run for coaching/scoring AI audit)
  └── (implicitly) ons_ops_cases, ons_ops_intake via transitive deps
```
