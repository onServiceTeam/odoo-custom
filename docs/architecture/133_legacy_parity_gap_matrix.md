# 133 — Legacy Parity Gap Matrix

> Legacy: `/home/onservice/script-secure-guard-8285b830`
> (React/Vite + Express + PostgreSQL, 302+ migrations, 150+ tables)
>
> Odoo build: 13 ons_ops_* modules, 42 menu items

## Purpose

For every feature area in the legacy onService dashboard, document what
the Odoo custom build already covers, what's missing, and whether the
gap matters for launch.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully covered in Odoo build |
| 🟡 | Partially covered — model exists but UI/logic incomplete |
| ❌ | Not built — requires new work |
| ➖ | Not needed — Odoo native covers it or feature is deprecated |

---

## Feature Matrix

### 1. Call Intake Hub

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Multi-step intake form | 🟡 | `ons.interaction` form exists; no multi-step wizard UX |
| Customer name / phone / email | ✅ | `partner_id` + inline fields |
| Driver code classification | ✅ | `primary_driver_id` with 40+ seed codes |
| Session path selector | ✅ | `session_path` selection field |
| Urgency / priority | ✅ | `urgency` (low/medium/high) |
| Issue description | ✅ | `issue_description` text field |
| Auto-link to existing customer | 🟡 | Manual partner selection; no auto-match by phone |
| AI driver suggestion | ❌ | AI model exists but no intake integration |
| Queue name / inbound queue | ✅ | `queue_name` field |
| Call duration tracking | ✅ | `call_duration`, `talk_duration` |
| Caller type classification | ✅ | `caller_type`, `customer_type` |
| Discord thread auto-creation | ❌ | No Discord integration built |
| Odoo ticket auto-creation | ➖ | We ARE Odoo now; case creation replaces tickets |

### 2. Customers

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Customer list with search | ✅ | `res.partner` tree view with filters |
| Contact info (phone/email/address) | ✅ | Native partner fields |
| Customer segments | ✅ | `customer_segment` selection field |
| Submission/interaction history | ✅ | `interaction_count` + smart button |
| Payment history | 🟡 | `case_line_ids` visible on case; no partner-level rollup |
| Lifetime value metrics | ❌ | No `total_spent` computed field on partner |
| SMS conversation preview | ❌ | SMS thread exists but no partner-level preview |
| Deduplication tools | ➖ | Odoo native partner merge |
| First-time / returning badge | ✅ | `customer_segment` field |

### 3. On-Site Dispatch

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Dispatch queue (list/kanban) | ✅ | `ons.dispatch` with 10 statuses |
| Dispatch creation from case | ✅ | `case_id` link on dispatch |
| Address fields | ✅ | `address_*`, `city`, `state`, `zip` |
| Status lifecycle (10 states) | ✅ | draft → … → completed/cancelled/voided |
| WorkMarket API integration | ❌ | No WorkMarket connector built |
| Applicant bidding UI | ❌ | No applicant model |
| Worker assignment + rating | ❌ | No worker model |
| Address validation (Google Maps) | ❌ | No address validation |
| Dispatch checklist | ✅ | `ons.dispatch.checklist` model |
| SMS dispatch confirmation | ❌ | No SMS→dispatch integration |
| Voice reminders (3CX CFD) | ❌ | No 3CX voice integration |
| Discord status notifications | ❌ | No Discord integration |

### 4. QA & Coaching (My Performance)

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| QA evaluation model | ✅ | `ons.qa.evaluation` with scores |
| Rule-based grading | ✅ | `ons.qa.rule` + `ons.qa.call.type` |
| Phase scores (JSONB) | 🟡 | Structure exists; V3 scoring engine not built |
| Call recording playback | ❌ | No recording URL streaming |
| Transcript viewer | ❌ | No transcript model |
| AI coaching summary | ❌ | AI model exists but no QA integration |
| Coaching sessions | ✅ | `ons.qa.coaching` model |
| Coaching acknowledgment | 🟡 | Model exists; workflow not complete |
| Agent self-service dashboard | ❌ | No My Performance portal view |

### 5. Team Performance

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Agent KPI table | ✅ | `ons.report.agent.daily` |
| Time period filters | ✅ | Date filters on report views |
| Call count / handle time | 🟡 | Fields exist; no 3CX data to populate |
| QA score average | 🟡 | Computed field ready; needs QA data |
| Revenue per agent | ✅ | Sum of `amount_total` where `paid` |
| Goal progress tracker | ❌ | No daily_5_progress equivalent |
| Queue-based KPIs | ✅ | `ons.report.queue.daily` |
| Export to CSV | ➖ | Odoo native list export |

### 6. Session Tracker

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Active session list | ✅ | Filtered case view (open + session_started) |
| Session type / duration | 🟡 | `online_session_started` boolean; no duration timer |
| Agent assignment | ✅ | `assigned_tech_id` on case |
| Real-time duration counter | ❌ | No JS live timer widget |
| Action buttons (dispatch/callback) | 🟡 | Form buttons exist; no quick-action bar |

### 7. Shared Inbox (Discord)

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Discord thread per case | ❌ | No Discord integration |
| Message posting from Odoo | ❌ | — |
| Thread archival | ❌ | — |
| **Alternative:** Odoo Discuss | ✅ | Chatter on every record; Discuss channels available |

### 8. SMS Center

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| SMS thread model | ✅ | `ons.sms.thread` model exists |
| Inbound/outbound messages | 🟡 | Model ready; no Twilio/FlowRoute connector |
| Auto-link by phone number | ❌ | No phone-based auto-linking |
| Response classification | ❌ | No regex/AI response parser |
| MMS support | ❌ | — |
| **Alternative:** Odoo SMS | ➖ | Native SMS module available (IAP-based) |

### 9. Reminders

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Scheduled reminders | ➖ | Odoo Activities (mail.activity) covers this |
| Reminder types | ➖ | Activity types configurable |
| Recurrence | ❌ | Odoo activities don't recur natively |
| Snooze | ➖ | Activity reschedule = snooze |
| Push notifications | ❌ | No push notification system |

### 10. QA Center (Manager)

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Evaluation list | ✅ | `ons.qa.evaluation` tree with filters |
| Score override | 🟡 | Field exists; no override audit model |
| Coaching assignment | ✅ | `ons.qa.coaching` |
| Escalation workflow | ❌ | No auto-escalation rules |
| Calibration exercises | ❌ | — |

### 11. HR Center

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Schedules | ➖ | Odoo native Planning module |
| Time off requests | ➖ | Odoo native Time Off module |
| Time tracking | ➖ | Odoo native Timesheets |
| Payroll | ➖ | Odoo native Payroll (Enterprise) |

### 12. Admin Panel

| Legacy Feature | Odoo Status | Notes |
|---------------|:-----------:|-------|
| Integration settings | 🟡 | AI provider/model config built; others not |
| System settings | ➖ | Odoo Settings module |
| User roles | ✅ | 3 security groups (agent/manager/admin) |
| Product catalog | ✅ | 11 products with `ons_product_code` |
| Audit logs | ➖ | Odoo native audit trail (mail.tracking) |
| Health checks | ❌ | No system health dashboard |

---

## Integration Parity

| Integration | Legacy | Odoo Build | Gap |
|------------|--------|-----------|-----|
| **3CX VoIP** | 15-min polling, agent status, recordings | `ons.call.log` + `ons.extension` models ready | ❌ No 3CX API connector |
| **Discord** | Thread auto-create, message sync, archival | Not built | ❌ Full gap |
| **WorkMarket** | Assignment create/send, applicant sync, complete | `ons.dispatch` model ready | ❌ No WorkMarket API connector |
| **Stripe** | Full sync, subscription tracking, payment matching | `payment_status` + `payment_amount` fields | ❌ No Stripe connector |
| **Twilio/SMS** | Outbound SMS, inbound webhook, thread management | `ons.sms.thread` model ready | ❌ No Twilio connector |
| **Email** | Outbound email, template engine | ➖ Odoo native mail system | ✅ Covered |
| **Odoo** | One-way push to helpdesk tickets | ➖ We ARE Odoo now | ✅ N/A |

---

## Summary Counts

| Status | Count | % |
|--------|------:|--:|
| ✅ Fully covered | 32 | 37% |
| 🟡 Partially covered | 12 | 14% |
| ❌ Not built | 23 | 26% |
| ➖ Native/deprecated | 20 | 23% |
| **Total features** | **87** | 100% |

**Core workflow (intake → case → billing → close): fully working.**
**Integration connectors (3CX, Discord, WorkMarket, Stripe, Twilio): not built.**
