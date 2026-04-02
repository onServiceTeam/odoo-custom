# 42 — Session Tracker Parity Notes

**Date:** 2026-04-02  
**Purpose:** Map legacy session tracker features to the Odoo `ons.case` implementation and note any differences.

---

## 1. What the Legacy Session Tracker Is

The legacy session tracker is a **filtered table view** of the `v_customer_pipeline` database view. It is NOT a separate entity or module — it is the primary operational dashboard showing active cases in their pipeline stages.

**Source:** `SessionTrackerPage.tsx` + `v_customer_pipeline` view

---

## 2. Feature Parity Map

| Legacy Feature | Odoo Implementation | Notes |
|---------------|---------------------|-------|
| Pipeline stage column | `stage_id` with kanban coloring | 12 custom stages match legacy |
| Customer name + phone | `partner_id` + `partner_phone` related | |
| Agent role columns (intake/tech/VBT) | `intake_agent_id`, `assigned_tech_id`, `billing_agent_id` | Three distinct role fields |
| Repair status display | Absorbed into stage progression | Legacy had separate repair_status; Odoo uses stage |
| Payment status display | Future: `payment_status` from Prompt 6 | Not built yet |
| Hours in pipeline | `hours_in_pipeline` computed field | From `create_date` |
| Aging bucket | `aging_bucket` computed selection | Same 5 buckets: 0–4h, 4–24h, 24–48h, 48–72h, 72h+ |
| Gross/refund amounts | Future: Prompt 6 billing addon | Not built yet |
| Odoo ticket ID link | Not needed | We ARE Odoo now |
| Discord thread link | `legacy_discord_thread_id` on interaction | For migration reference |
| Date range filter (ET) | Standard Odoo date filters | Odoo handles timezone via user settings |
| Stage filter | Search filter groups | |
| Agent filter | Search filter | |
| Aging bucket filter | Search filter | |
| Quick date filters (Today/7d/30d) | Odoo date filter presets | |
| Custom search (name/phone) | Standard Odoo search bar | |
| Exclusion: completed/declined/N-A | Default domain on action | `[('is_closed', '=', False)]` |

---

## 3. Legacy Exclusion Rules → Odoo Defaults

Legacy session tracker excludes:
```
is_completed = true        → Odoo: is_closed = True
call_status = 'Declined'   → Odoo: stage = closed_lost
session_path = 'N/A'       → Odoo: won't create case for N/A paths
```

**Odoo equiv:** The case list action defaults to `[('is_closed', '=', False)]` so closed cases are excluded by default but accessible via "Archived" filter.

---

## 4. Legacy Stage Computation vs Odoo Stage

**Legacy:** Stage is COMPUTED from a matrix of `repair_status`, `payment_status`, `online_session_started`, `callback_status`, and override fields. It's a database view, not a stored field.

**Odoo:** Stage is an EXPLICIT field (`stage_id`) set by business actions. Stage changes are tracked in `ons.case.stage.history`.

**Why the change:**
- Odoo's kanban/pipeline UX expects an explicit stage field
- Computed stages from legacy required complex SQL views with priority logic
- Explicit stages are easier to audit, query, and report on
- The legacy override system (`pipeline_stage_override`) proves they already needed explicit control

**What to watch:** Business actions that change the stage must enforce the same invariants that the legacy computed view enforced. For example, setting stage to `paid` should require actual payment evidence (once billing is built in Prompt 6).

---

## 5. Differences from Legacy

| Area | Legacy | Odoo | Risk |
|------|--------|------|------|
| Stage storage | Computed view | Explicit field | LOW — cleaner |
| Stage override | `pipeline_stage_override` column | Manager action with audit | LOW — better |
| Payment status | Separate column | Future Prompt 6 field | NONE — sequential build |
| Amounts display | In tracker columns | Future Prompt 6 | NONE |
| AI summary | `summary_generated_at` flag | Future Prompt 10 | NONE |
| Completion eligibility | `completion_eligible_at` | Case is_closed logic | LOW |
| Dual-status system | repair_status + payment_status = stage | Single stage field | MEDIUM — must ensure stage transitions reflect both |

---

## 6. "My Active Work" View

Legacy has agent-specific filtering based on role:
- Intake agents see cases they submitted
- Technicians see cases assigned to them
- VBTs see cases in billing stage assigned to them

**Odoo implementation:** Saved search filters:
- "My Intake" → `intake_agent_id = uid`
- "My Repairs" → `assigned_tech_id = uid`
- "My Billing" → `billing_agent_id = uid`
- "Needs Attention" → `needs_attention = True`

---

## 7. Kanban Board

Legacy is list-only. The Odoo implementation adds a **kanban board** grouped by stage. This is an improvement over legacy that the business will benefit from, while the list view preserves the familiar session tracker table format.

Kanban card shows:
- Customer name
- Driver category
- Assigned tech (avatar)
- Hours in pipeline
- Aging bucket indicator (color chip)
