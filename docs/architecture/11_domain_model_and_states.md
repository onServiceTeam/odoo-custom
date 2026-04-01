# 11 — Domain Model and States

**Date:** 2026-04-01  
**Source:** onService middleware schema (213+ migrations)  
**Target:** Odoo Community 19 custom addon models  

---

## Core Entity Hierarchy

```
res.partner (Odoo stock)          ← customer master
├── ons.interaction               ← every inbound contact (call/email/sms/web)
│   ├── links to crm.lead        ← if CRM path
│   └── links to ons.case        ← if service path
│
├── ons.case                      ← support case (1 customer : many cases)
│   ├── ons.session               ← individual sessions within a case
│   │   └── ons.session.call      ← calls linked to this session
│   ├── ons.dispatch              ← on-site dispatch assignments
│   └── account.move              ← invoices / payments
│
├── crm.lead (Odoo stock)         ← CRM lead/opportunity
│   └── mail.activity             ← follow-up tasks
│
└── ons.qa.evaluation             ← quality assessment of a call/session
```

---

## Model Definitions

### ons.interaction (replaces: submissions + call_logs)

The atomic unit of contact. Every phone call, email, SMS, or web form submission
creates one interaction record.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Auto-computed: "INT-YYYYMMDD-XXXX" |
| interaction_type | Selection | phone / email / sms / web_form / callback |
| direction | Selection | inbound / outbound / internal |
| partner_id | Many2one → res.partner | Resolved customer |
| customer_name | Char | As provided (before resolution) |
| customer_phone | Char | Raw phone number |
| customer_email | Char | Raw email |
| agent_id | Many2one → res.users | Intake agent |
| assisting_agent_id | Many2one → res.users | Technician |
| billing_agent_id | Many2one → res.users | VBT |
| queue_name | Char | 3CX queue |
| primary_driver_code | Char | AI-classified call driver |
| secondary_driver_codes | Char | Comma-separated |
| caller_type | Selection | new / returning / callback |
| customer_type | Selection | home / business |
| service_purchased | Char | Product sold |
| issue_description | Text | Customer's issue |
| call_start | Datetime | |
| call_end | Datetime | |
| call_duration | Integer | Seconds |
| talk_duration | Integer | Seconds |
| disposition | Selection | answered / missed / abandoned / voicemail / no_answer |
| has_recording | Boolean | |
| recording_url | Char | S3 presigned or 3CX URL |
| transcript | Text | AI transcription |
| transcript_status | Selection | pending / processing / completed / failed |
| case_id | Many2one → ons.case | If service path |
| lead_id | Many2one → crm.lead | If CRM path |
| session_id | Many2one → ons.session | Active session |
| discord_thread_id | Char | Legacy Discord ref |
| odoo_ticket_id | Char | Legacy Odoo ticket ref |
| threecx_cdr_id | Char | 3CX CDR primary ID (dedup key) |
| state | Selection | new / classified / assigned / completed |

**State Machine:**
```
new → classified (AI classification done)
    → assigned (linked to case or lead)
    → completed (case closed or lead converted)
```

---

### ons.case (replaces: cases)

A support case groups related sessions and tracks the customer's problem to resolution.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Auto: "CASE-YYYYMMDD-XXXX" |
| case_number | Char | Human-readable, unique |
| partner_id | Many2one → res.partner | Customer |
| primary_interaction_id | Many2one → ons.interaction | Originating interaction |
| assigned_agent_id | Many2one → res.users | Primary owner |
| escalated_to_id | Many2one → res.users | Escalation target |
| subject | Char | Brief summary |
| description | Text | Detailed issue |
| priority | Selection | low / normal / high / urgent |
| category | Selection | technical_support / billing / sales / renewal |
| stage_id | Many2one → ons.case.stage | Kanban stage |
| sla_due_date | Datetime | SLA deadline |
| sla_breached | Boolean | |
| first_response_date | Datetime | |
| resolved_date | Datetime | |
| closed_date | Datetime | |
| resolution | Text | How it was resolved |
| session_ids | One2many → ons.session | Child sessions |
| interaction_ids | One2many → ons.interaction | Related interactions |
| dispatch_ids | One2many → ons.dispatch | Dispatch assignments |
| invoice_ids | One2many → account.move | Invoices |
| tag_ids | Many2many → ons.case.tag | Tags |
| odoo_sync_status | Selection | pending / synced / failed |

**Stage Flow (Kanban):**
```
Open → In Progress → Pending Customer → Resolved → Closed
```

---

### ons.case.stage (pipeline stages)

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Stage name |
| sequence | Integer | Order |
| fold | Boolean | Folded in kanban |
| is_closing | Boolean | Marks case as closed |

---

### ons.session (replaces: service_sessions)

An individual work session within a case (one case may need multiple sessions).

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Auto: "SES-YYYYMMDD-XXXX" |
| case_id | Many2one → ons.case | Parent case |
| partner_id | Many2one → res.partner | (related to case) |
| session_type | Selection | remote / phone_only / onsite / callback |
| pipeline_stage | Selection | new / troubleshooting / in_session / awaiting_billing / paid / completed |
| primary_agent_id | Many2one → res.users | Session owner |
| assisting_agent_id | Many2one → res.users | Helper |
| scheduled_date | Datetime | If callback/scheduled |
| start_date | Datetime | Actual start |
| end_date | Datetime | Actual end |
| duration_minutes | Integer | |
| outcome | Selection | converted / no_sale / callback_scheduled / escalated / transferred |
| outcome_reason | Text | |
| product_sold | Char | Product/service sold |
| payment_amount | Monetary | |
| payment_collected | Boolean | |
| interaction_id | Many2one → ons.interaction | Originating interaction |
| call_ids | One2many → ons.interaction | Calls in this session |
| notes | Text | Work notes |

**Pipeline Stages:**
```
New → Troubleshooting → In Session → Awaiting Billing → Paid → Completed
```

---

### ons.dispatch (replaces: workmarket_assignments)

On-site dispatch assignment, optionally synced to WorkMarket.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Auto: "DSP-YYYYMMDD-XXXX" |
| case_id | Many2one → ons.case | |
| session_id | Many2one → ons.session | |
| partner_id | Many2one → res.partner | Customer |
| dispatch_status | Selection | draft / pending_approval / sent / assigned / confirmed / in_progress / completed / cancelled |
| provider_name | Char | Field tech name |
| scheduled_start | Datetime | |
| scheduled_end | Datetime | |
| location_type | Selection | residential / commercial |
| address | Text | Full address |
| address_lat | Float | Geocoded |
| address_lng | Float | Geocoded |
| special_instructions | Text | |
| priority | Selection | low / normal / high / urgent |
| confirmed_date | Datetime | |
| started_date | Datetime | |
| completed_date | Datetime | |
| cancelled_date | Datetime | |
| cancellation_reason | Text | |
| requires_approval | Boolean | |
| approved_by_id | Many2one → res.users | |
| workmarket_id | Char | External WorkMarket ID |
| voice_reminder_sent | Boolean | TTS callback sent |

**Status Flow:**
```
Draft → Pending Approval → Sent → Assigned → Confirmed → In Progress → Completed
                                                                      → Cancelled
```

---

### ons.qa.evaluation (replaces: qa_evaluations + qa_results)

Quality assessment of a call or session.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Auto: "QA-YYYYMMDD-XXXX" |
| interaction_id | Many2one → ons.interaction | Graded call |
| agent_id | Many2one → res.users | Agent being graded |
| evaluator_id | Many2one → res.users | Reviewer |
| evaluation_type | Selection | ai / manual / hybrid |
| total_score | Float | 0-100 |
| pass_status | Selection | pass / fail |
| signoff_status | Selection | pending / acknowledged / needs_review / closed |
| evidence_status | Selection | pending / needs_review / verified / insufficient |
| section_scores | Text (JSON) | Per-section breakdown |
| strengths | Text | Identified strengths |
| improvements | Text | Areas for improvement |
| coaching_notes | Text | Coaching plan |
| findings_detail | Text (JSON) | Structured QA findings |
| auto_fail | Boolean | Rule violation detected |
| auto_fail_reason | Char | |
| reviewed_date | Datetime | |
| ai_output | Text (JSON) | Raw AI grading output |

---

### ons.qa.rule (replaces: qa_rules)

Configurable QA scoring rules.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Rule name |
| category | Selection | behavior / pattern / scope / topic |
| description | Text | What this rule checks |
| score_weight | Float | Weight in final score |
| is_auto_fail | Boolean | Triggers auto-fail if violated |
| active | Boolean | Enabled/disabled |

---

### ons.call.driver (replaces: call_driver_codes)

Catalog of call reasons.

| Field | Type | Notes |
|-------|------|-------|
| name | Char | Display name |
| code | Char | Unique code |
| category | Selection | technical / billing / sales / renewal / other |
| active | Boolean | |

---

## Odoo Stock Models We Extend (Not Replace)

| Odoo Model | How We Use It |
|------------|---------------|
| `res.partner` | Customer master — add fields for segment, subscription_status, lifetime_value |
| `crm.lead` | CRM leads from interactions that don't become cases |
| `account.move` | Invoices/credit notes for case billing |
| `account.payment` | Payment registration (Stripe/Zoho sync) |
| `product.product` | Service products (base_fix, renewal, subscription) |
| `mail.activity` | Follow-up reminders, SLA tracking |
| `discuss.channel` | Already customized (ons_discuss_* addons) |

---

## Data Migration Strategy

The middleware database will continue running during the transition period.
Bidirectional sync between the middleware and Odoo will be maintained until
all features are ported. Migration order:

1. **Customer profiles** → res.partner (already partially synced)
2. **Interactions** → ons.interaction (new, replaces submissions + call_logs)
3. **Cases** → ons.case (replaces cases table, already has odoo_ticket_id)
4. **Sessions** → ons.session (new hierarchy under cases)
5. **Payments** → account.move / account.payment (Odoo already has this)
6. **QA evaluations** → ons.qa.evaluation (new)
7. **Dispatch** → ons.dispatch (new)
