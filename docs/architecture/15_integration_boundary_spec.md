# 15 — Integration Boundary Spec

**Date:** 2026-04-01  
**Purpose:** Define what stays external, what moves into Odoo, and the API contracts between them.  

---

## Integration Inventory

The middleware currently connects to 8 external systems. Each must be
classified as **Absorb** (move fully into Odoo), **Bridge** (Odoo controller
receives/sends, logic in Odoo), or **Daemon** (keep as external service,
sync via cron or webhook).

| # | System | Current Tech | Classification | Rationale |
|---|--------|-------------|----------------|-----------|
| 1 | 3CX PBX | REST API polling (15min cron + 30sec active calls) | **Daemon** | Real-time call monitoring needs sub-minute polling; Odoo crons minimum 1min. Keep external collector, push to Odoo via JSON-RPC. |
| 2 | Discord | REST API + webhooks | **Deprecate** | Replaced by Odoo Discuss (Phase 0 work). Existing Discord channels kept read-only during transition. |
| 3 | Stripe | Webhooks + REST API | **Bridge** | Odoo controller receives Stripe webhooks, creates `account.payment` records. Odoo's payment module handles reconciliation. |
| 4 | Zoho Books | REST API (2-way sync) | **Bridge** | Odoo controller syncs invoices/payments. Eventually replace with Odoo Accounting if Enterprise upgrade happens. |
| 5 | OpenAI | REST API (transcription, QA grading, AI assist) | **Bridge** | Odoo server actions call OpenAI API directly. No daemon needed — triggered by record events. |
| 6 | WorkMarket | REST API + webhooks | **Bridge** | Odoo controller receives assignment webhooks, REST calls for dispatch actions. |
| 7 | Twilio/SMS | REST API | **Bridge** | Odoo controller sends SMS via Twilio. Can use Odoo's `sms` module as abstraction layer. |
| 8 | Email (SendGrid/SMTP) | SMTP relay | **Absorb** | Odoo handles email natively. Configure outbound SMTP in Odoo. Already set up: `mail.onservice.us:587`. |

---

## Detailed Boundary Definitions

### 1. 3CX PBX — DAEMON

```
┌─────────────┐         ┌──────────────────┐         ┌───────────┐
│   3CX PBX   │◄───────►│  3CX Collector   │────────►│   Odoo    │
│  (SIP/PBX)  │  REST   │  (Node.js daemon) │ JSON-RPC│ ons.interaction │
└─────────────┘         └──────────────────┘         └───────────┘
                              │
                              ├── Poll active calls (30 sec)
                              ├── Poll call log (15 min)
                              ├── Fetch recordings (on new call)
                              └── Push to Odoo via XML-RPC/JSON-RPC
```

**Daemon Responsibilities:**
- Poll 3CX REST API for active calls (30-second interval)
- Poll 3CX call log for completed calls (15-minute interval)
- Download call recordings and store in Odoo `ir.attachment`
- Create/update `ons.interaction` records via Odoo external API
- Monitor queue status and push to `ons.threecx.queue`

**Odoo Side:**
- `ons.interaction` model accepts external writes (access rules for API user)
- Webhook endpoint `/ons/3cx/webhook` for real-time events (if 3CX supports push)
- Cron job to reconcile missed records (hourly)

**API Contract (Daemon → Odoo):**
```python
# Create interaction
odoo.execute_kw('ons.interaction', 'create', [{
    'source': 'phone',
    'caller_number': '+15551234567',
    'agent_id': agent_uid,
    'duration': 342,
    'recording_url': 'https://3cx.example.com/rec/12345.wav',
    'threecx_call_id': 'ext-12345',
    'state': 'completed',
}])
```

---

### 2. Discord — DEPRECATE

**Transition Plan:**
1. Keep existing Discord bot running (read-only) during migration
2. All new work journal entries go to Odoo Discuss channels
3. After 30-day parallel period, archive Discord channels
4. Backfill historical Discord threads to Odoo Discuss (optional, low priority)

**No new code required.** Phase 0 `ons_discuss_*` modules already provide
the replacement functionality.

---

### 3. Stripe — BRIDGE

```
┌──────────┐  webhook   ┌───────────────────────┐
│  Stripe  │──────────►│  /ons/stripe/webhook   │
│          │           │  (Odoo HTTP controller) │
└──────────┘           └───────────┬─────────────┘
                                   │
                          ┌────────▼────────┐
                          │ account.payment  │
                          │ ons.interaction  │
                          │ (link payment)   │
                          └─────────────────┘
```

**Odoo Controller:** `ons_ops_billing`
- `POST /ons/stripe/webhook` — receives Stripe events
- Verify webhook signature (HMAC-SHA256)
- Handle events: `payment_intent.succeeded`, `charge.refunded`, `dispute.created`
- Create `account.payment` linked to `ons.session`

**Outbound (Odoo → Stripe):**
- Create payment intent when session starts billing
- Server action: `ons.session` → `action_create_payment_intent()`
- Use `stripe` Python library in server action

**Secrets Management:**
- Store API keys in `ir.config_parameter`:
  - `ons_ops_billing.stripe_secret_key`
  - `ons_ops_billing.stripe_webhook_secret`
  - `ons_ops_billing.stripe_publishable_key`
- Access via `self.env['ir.config_parameter'].sudo().get_param()`

---

### 4. Zoho Books — BRIDGE

```
┌──────────┐  REST API  ┌────────────────────────┐
│  Zoho    │◄──────────►│  ons_ops_billing        │
│  Books   │            │  (Odoo cron + actions)   │
└──────────┘            └────────────────────────┘
```

**Sync Strategy:**
- Odoo cron (every 2 hours): pull new Zoho invoices → create `account.move`
- On `account.payment` confirm: push payment to Zoho via REST
- OAuth2 token management via `ir.config_parameter`

**Long-Term:** If Enterprise upgrade happens, replace Zoho with Odoo Accounting.
The `account.move`/`account.payment` models are the same — only the sync
layer changes.

---

### 5. OpenAI — BRIDGE

```
┌──────────┐  REST API  ┌────────────────────────┐
│  OpenAI  │◄──────────►│  ons_ops_ai             │
│  API     │            │  (Odoo server actions)   │
└──────────┘            └────────────────────────┘
```

**Trigger Points:**
| Trigger | Action | Model |
|---------|--------|-------|
| Recording attached to interaction | Transcribe via Whisper API | `ons.interaction` |
| Transcription completed | Auto-grade via GPT | `ons.qa.evaluation` |
| Agent requests AI assist | Summarize/suggest via GPT | `ons.session` |
| Case notes updated | Auto-classify call driver | `ons.case` |

**Implementation:**
- Python `openai` library called from Odoo server actions
- Async pattern: create `queue.job` record, process via cron (1-min interval)
- Store results as computed fields on the target model
- Rate limiting: max 10 concurrent API calls, exponential backoff

**Config Parameters:**
- `ons_ops_ai.openai_api_key`
- `ons_ops_ai.openai_model` (default: `gpt-4o`)
- `ons_ops_ai.whisper_model` (default: `whisper-1`)
- `ons_ops_ai.auto_transcribe` (boolean)
- `ons_ops_ai.auto_qa_grade` (boolean)

---

### 6. WorkMarket — BRIDGE

```
┌──────────────┐  webhook   ┌──────────────────────┐
│  WorkMarket  │──────────►│ /ons/workmarket/hook   │
│              │           │ (Odoo HTTP controller)  │
│              │◄──────────│                        │
│              │  REST API │ ons_ops_dispatch        │
└──────────────┘           └──────────────────────┘
```

**Inbound Webhooks:**
- Assignment status changes (accepted, declined, completed)
- Technician check-in/check-out
- Update `ons.dispatch` record state

**Outbound REST:**
- Create assignment: `ons.dispatch` → `action_send_to_workmarket()`
- Cancel assignment: `ons.dispatch` → `action_cancel_workmarket()`
- Approve assignment: `ons.dispatch` → `action_approve_workmarket()`

---

### 7. Twilio/SMS — BRIDGE

```
┌──────────┐  REST API  ┌────────────────────────┐
│  Twilio  │◄──────────►│  ons_ops_comms           │
│          │  webhook   │  (Odoo controller)       │
└──────────┘            └────────────────────────┘
```

**Outbound:** Send SMS from case/session context via Twilio REST API.  
**Inbound:** `POST /ons/sms/webhook` receives replies, creates `mail.message`.  
**Alternative:** Use Odoo `sms` module's IAP framework (if cost-effective).

---

### 8. Email — ABSORB

Already configured. Odoo handles all email via:
- Outbound: `mail.onservice.us:587` STARTTLS
- Inbound: Odoo fetchmail (if needed) or alias routing
- Templates: `mail.template` records for automated emails

**No additional integration code required.**

---

## Security Requirements for All Bridges

| Requirement | Implementation |
|-------------|---------------|
| Webhook signature verification | HMAC-SHA256 for Stripe, WorkMarket |
| API key storage | `ir.config_parameter` (not source code) |
| Rate limiting | Per-integration counters, exponential backoff |
| Audit logging | `ir.logging` records for all external API calls |
| Error handling | Retry queue with dead-letter after 3 failures |
| TLS | All external calls via HTTPS only |
| IP allowlisting | nginx rules for webhook endpoints (optional) |

---

## Daemon Deployment

The 3CX collector daemon runs as a separate process:

```
/home/onservice/ons-3cx-collector/
├── collector.ts          # Main polling loop
├── odoo-client.ts        # JSON-RPC client to Odoo
├── package.json
└── ecosystem.config.cjs  # PM2 process manager
```

Managed by PM2 alongside the middleware during the transition period.
After migration, only the 3CX collector remains as an external daemon.
