# 10 — Customer Journey Master Map

**Date:** 2026-04-01  
**Source of Truth:** onService middleware repo (`script-secure-guard-8285b830`)  
**Target:** Odoo Community 19 custom addon suite  

---

## The Real Business Flow

The business is **not** "helpdesk tickets." It is a full-cycle contact center operation
where many inbound contacts never become service cases. The journey has 8 distinct
stages, and the system must handle each one.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER JOURNEY MAP                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌──────────────┐    │
│  │ INBOUND  │───>│ IDENTITY  │───>│ QUALIFY / │───>│ SERVICE CASE │    │
│  │ CONTACT  │    │ RESOLVE   │    │ CLASSIFY  │    │ OR CRM LEAD  │    │
│  └──────────┘    └───────────┘    └───────────┘    └──────┬───────┘    │
│   3CX call        Phone dedup      AI classify            │            │
│   Email            Odoo partner      Driver code      ┌───┴───┐       │
│   SMS              lookup            caller_type      │       │       │
│   Web form                                            ▼       ▼       │
│                                                   SERVICE   CRM       │
│                                                    PATH    PATH       │
│                                                      │       │       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐   │       │       │
│  │ FULFILLMENT  │<─┤  CASE MGMT   │<─┤ SESSION  │<──┘       │       │
│  │ (remote or   │  │  assign,     │  │ pipeline │           │       │
│  │  on-site)    │  │  escalate,   │  │ stages   │           │       │
│  └──────┬───────┘  │  track SLA   │  └──────────┘           │       │
│         │          └──────────────┘                          │       │
│         ▼                                                    │       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │       │
│  │   BILLING    │  │  QA / GRADE  │  │  COMPLETION  │      │       │
│  │  invoice,    │  │  auto-grade, │  │  summary,    │      │       │
│  │  payment     │  │  coaching    │  │  archive     │      │       │
│  │  collection  │  │              │  │              │      │       │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘      │       │
│         │                                    │              │       │
│         ▼                                    ▼              ▼       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  RETENTION / REACTIVATION                    │   │
│  │   subscription renewal, win-back campaigns, upsell          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Inbound Contact

**Current System:** 3CX PBX → call_logs table, polling every 15 min  
**Channels:** Phone (3CX), Email (IMAP/SMTP), SMS (Twilio-like), Web form  

**Key Data:**
- caller_number, callee_number, queue_name, direction
- disposition (answered/missed/abandoned/voicemail)
- recording_url, call_duration, talk_duration  

**Odoo Mapping:**
- `mail.activity` for inbound call logging
- `crm.phonecall` equivalent via custom model
- Phone calls tracked as `ons.interaction` records

---

## Stage 2: Identity Resolution

**Current System:** Phone number dedup via `customer_profiles.phone_clean`, Odoo partner lookup  
**Logic:**
1. Normalize phone → digits-only
2. Search `customer_profiles` by phone_clean
3. If not found → search Odoo partners by phone
4. If not found → create new customer profile
5. Link submission to `linked_customer_id`

**Odoo Mapping:**
- `res.partner` is the master customer record
- Phone normalization via `phone_validation` module (already in Odoo)
- `ons.interaction` links to partner automatically

---

## Stage 3: Qualify / Classify

**Current System:** AI polish + classify via OpenAI  
**Key Outputs:**
- `primary_driver_code` — why they called (billing, tech support, sales, renewal)
- `caller_type` — first_time_caller / returning_caller
- `customer_type` — home / business
- `service_purchased` — what product was sold

**Decision Point:**
- **Service path** → Create case + session + Discord thread + Odoo ticket
- **CRM path** → Create CRM lead (no case, nurture flow)
- **Inquiry only** → Log interaction, no further action

**Odoo Mapping:**
- Classification stored on `ons.interaction` record
- Driver codes as configurable selection/tags
- CRM leads → standard `crm.lead`
- Service cases → `ons.case`

---

## Stage 4: Service Case / Session

**Current System:** `cases` table + `service_sessions` table (1:M)  
**Status Flow:**
```
Case:    open → in_progress → pending_customer → resolved → closed
Session: new → troubleshooting → in_session → awaiting_billing → paid → completed
```

**Roles:**
- `phone_tech` — intake agent who answered
- `assisting_tech` — technician doing the fix
- `billing_tech` — VBT who collects payment

**Odoo Mapping:**
- `ons.case` model with kanban stages
- `ons.session` child model (one case has many sessions)
- Assignment via `user_id` fields
- Chatter for work journal (replaces Discord threads)

---

## Stage 5: Fulfillment (Remote or On-Site)

**Current System:** `jobs` (remote fixes), `workmarket_assignments` (on-site dispatch)  
**Remote:** Tech works with customer over phone/remote session  
**On-site:**
1. Create dispatch job → WorkMarket API
2. Generate voice reminder (TTS → WAV → 3CX CFD)
3. Provider accepts → confirmed → in_progress → completed

**Odoo Mapping:**
- Remote: Session stages track progress
- On-site: `ons.dispatch` model → optional OCA field-service bridge
- Voice callbacks: Keep as daemon service (sub-second latency required)

---

## Stage 6: Billing & Payment

**Current System:** `payment_transactions` (source of truth for revenue)  
**Sources:** Stripe (primary), Zoho Payments (secondary), Manual entry  
**Status:** pending → paid → refunded → disputed  
**Products:** base_fix, renewal, subscription, addon, downsell  

**Odoo Mapping:**
- `account.move` (invoices) — Odoo is already the billing system
- Payment registration via `account.payment`
- Stripe sync via custom controller (webhook receiver)
- Product catalog → `product.product`

---

## Stage 7: QA & Coaching

**Current System:** AI auto-grading + human review  
**Flow:** Transcription → auto-grade → command center review → coaching  
**Score:** 0-100, auto-fail if < 70 or rule violation  

**Odoo Mapping:**
- `ons.qa.evaluation` model linked to interactions
- QA rules as configurable records
- Dashboard for command center view
- Coaching notes via chatter / mail.activity

---

## Stage 8: Completion & Retention

**Current System:** Auto-completion 24h after payment  
**Flow:**
1. Payment matched → eligible
2. 24h delay → fetch Discord thread messages
3. AI summarize → generate customer report
4. Post to Odoo ticket + email customer
5. Archive Discord thread

**Odoo Mapping:**
- Automated action (ir.cron) for completion check
- Report generation via QWeb templates
- Email via standard mail.template
- Chatter history replaces Discord thread archive

---

## The CRM Path (Currently Underdeveloped)

The current system doesn't have a formal CRM pipeline — all contacts are treated as
potential service cases. But many callers are:
- Inquiries that never convert
- Leads that need nurturing
- Renewals of existing subscriptions
- Upsell opportunities

**Odoo Opportunity:**
- Standard `crm.lead` with pipeline stages
- Lead scoring from interaction history
- Nurture campaigns via email marketing
- Conversion tracking from lead → case → payment

This is a significant gap in the current middleware that Odoo fills natively.
