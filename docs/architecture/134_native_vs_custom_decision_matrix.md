# 134 — Native vs Custom Decision Matrix

> Context: Odoo 19 Community Edition on Hetzner VPS
> 13 custom `ons_ops_*` modules installed

## Purpose

For each functional domain, decide: keep the custom module, pivot to
native Odoo / OCA, or build a connector.  The goal is to minimize custom
code while preserving the onService workflow that the legacy dashboard
proved works.

---

## Decision Framework

| Decision | When to use |
|----------|------------|
| **Keep Custom** | Domain has unique onService logic that Odoo native can't model (stage matrix, driver codes, 3-role assignment) |
| **Custom Now → Map Later** | Custom module works today; may migrate to native/OCA when Odoo adds the capability or Enterprise is licensed |
| **Pivot to Native** | Odoo OOTB module covers 80%+ of the need; custom module adds unnecessary maintenance |
| **Build Connector** | External API integration needed; build as a thin custom module that calls external service |
| **Skip / Defer** | Feature has low ROI or owner hasn't requested it |

---

## Domain Decisions

### 1. CRM & Lead Management

| | |
|---|---|
| **Module** | `ons_ops_crm` |
| **Decision** | **Keep Custom** |
| **Rationale** | Extends native `crm.lead` with `interaction_id`, `primary_driver_id`, `is_convertible` gating, and `action_convert_to_case()`. These are core onService workflows. Native CRM stays underneath. |
| **Risk** | Low — extends, doesn't replace |

### 2. Intake & Interactions

| | |
|---|---|
| **Module** | `ons_ops_intake` |
| **Decision** | **Keep Custom** |
| **Rationale** | `ons.interaction` is a new model with no native equivalent. Call driver codes, session paths, urgency classification, and interaction→lead→case flow are all custom onService IP. |
| **Risk** | Low — standalone model |

### 3. Cases & Pipeline

| | |
|---|---|
| **Module** | `ons_ops_cases` |
| **Decision** | **Keep Custom** |
| **Rationale** | `ons.case` with 12-stage validated pipeline, ALLOWED_TRANSITIONS matrix, 3-role assignment (intake/tech/billing), stage history audit trail, aging computation, and needs_attention flag. No native Odoo model does this. |
| **Risk** | Medium — most complex module; good test coverage essential |

### 4. Billing & Plans

| | |
|---|---|
| **Module** | `ons_ops_billing` |
| **Decision** | **Custom Now → Map Later** |
| **Rationale** | `ons.case.line` + payment tracking works for current single-payment workflow. When Stripe connector is built, should map `ons.case.line` → `account.move.line` (Odoo invoices) for proper accounting. `ons.customer.plan` may map to Odoo Subscriptions (Enterprise) in future. |
| **Migration path** | Case line → Invoice line; customer plan → Odoo Subscription |

### 5. Telephony

| | |
|---|---|
| **Module** | `ons_ops_telephony` |
| **Decision** | **Keep Custom + Build Connector** |
| **Rationale** | `ons.call.log` and `ons.extension` are the right models. Need a 3CX API connector (scheduled action that polls 3CX every 15 min and upserts call records). `ons.agent.status` needs real-time data from 3CX agent status API. |
| **Next step** | Build `ons_ops_3cx_connector` module |

### 6. Dispatch

| | |
|---|---|
| **Module** | `ons_ops_dispatch` |
| **Decision** | **Keep Custom + Build Connector** |
| **Rationale** | `ons.dispatch` with 10-status lifecycle mirrors the legacy WorkMarket flow. Need a WorkMarket API connector for create/send/accept/complete operations. Until connector is built, dispatches are tracked manually in Odoo. |
| **Next step** | Build `ons_ops_workmarket_connector` module |

### 7. Communication

| | |
|---|---|
| **Module** | `ons_ops_comms` |
| **Decision** | **Custom Now → Map Later** |
| **Rationale** | `ons.sms.thread` and `ons.email.thread` model external conversations. Odoo native `mail.thread` + Discuss handles internal communication. For SMS: evaluate Odoo IAP SMS vs. Twilio connector. For Discord: build thin bot connector or skip entirely (Discuss replaces it). |
| **Options** | (a) Twilio connector for SMS, (b) Odoo IAP SMS, (c) Skip Discord |

### 8. AI Services

| | |
|---|---|
| **Module** | `ons_ops_ai` |
| **Decision** | **Keep Custom** |
| **Rationale** | Provider/model registry, task routing, prompt contracts, budget tracking, and run history are all unique infrastructure. No native Odoo equivalent. This is the foundation for QA auto-grading, driver suggestion, and case summarization. |
| **Risk** | Low — self-contained |

### 9. QA & Coaching

| | |
|---|---|
| **Module** | `ons_ops_qa` |
| **Decision** | **Keep Custom** |
| **Rationale** | `ons.qa.evaluation`, `ons.qa.rule`, `ons.qa.call.type`, and `ons.qa.coaching` are domain-specific. Legacy has 100+ rules and 16 call types. Odoo Quality module is manufacturing-focused and doesn't fit. |
| **Next step** | Integrate with `ons_ops_ai` to auto-grade when transcripts available |

### 10. Reports

| | |
|---|---|
| **Module** | `ons_ops_reports` |
| **Decision** | **Custom Now → Map Later** |
| **Rationale** | `agent_daily`, `queue_daily`, `driver_daily` SQL-based reports work. Long-term, could use Odoo BI / pivot views / spreadsheet for dynamic reporting. Keep custom reports for now as they encode business KPIs (revenue, QA score, case velocity). |
| **Migration path** | May move to Odoo Spreadsheet or external BI (Metabase) |

### 11. Portal

| | |
|---|---|
| **Module** | `ons_ops_portal` |
| **Decision** | **Keep Custom** |
| **Rationale** | Customer-facing portal showing their cases, billing, and plans. Extends Odoo native portal with `ons.case` and `ons.case.line` access rules. Lightweight and well-scoped. |
| **Risk** | Low |

### 12. Shell & Admin

| | |
|---|---|
| **Module** | `ons_ops_shell` |
| **Decision** | **Keep Custom** |
| **Rationale** | Shell helpers for scripting/DevOps. Zero UI, zero risk. |

### 13. HR / Scheduling / Payroll

| | |
|---|---|
| **Module** | (not built) |
| **Decision** | **Pivot to Native** |
| **Rationale** | Odoo has mature native modules: Employees, Time Off, Planning, Timesheets, Payroll (Enterprise). No custom module needed. Install when ready. |

### 14. Reminders / Activities

| | |
|---|---|
| **Module** | (not built) |
| **Decision** | **Pivot to Native** |
| **Rationale** | Odoo `mail.activity` covers scheduled follow-ups, due dates, and assignee tracking. Use activity types to classify (callback, followup, etc.). |

---

## Connector Build Priority (Recommended Order)

| Priority | Connector | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | **3CX Polling** (`ons_ops_3cx_connector`) | Medium | High — enables call log, QA, agent status |
| 2 | **Stripe Sync** (`ons_ops_stripe_connector`) | Medium | High — enables payment verification + plan billing |
| 3 | **WorkMarket** (`ons_ops_workmarket_connector`) | Medium | Medium — enables dispatch automation |
| 4 | **Twilio SMS** (`ons_ops_twilio_connector`) | Low | Medium — enables SMS threads |
| 5 | **Discord Bot** (`ons_ops_discord_connector`) | Low | Low — Discuss may replace this need |

---

## Summary

| Decision | Count | Modules |
|----------|------:|---------|
| Keep Custom | 7 | intake, crm, cases, telephony, ai, qa, portal, shell |
| Custom → Map Later | 3 | billing, comms, reports |
| Pivot to Native | 2 | HR, Reminders |
| Build Connector | 4 | 3CX, Stripe, WorkMarket, Twilio |
| Skip / Defer | 1 | Discord (evaluate after Discuss adoption) |

**Bottom line:** The custom modules ARE the product.  They encode
onService-specific workflows that no native Odoo module handles.  The
gaps are almost entirely in external API connectors — those are the next
build priority.
