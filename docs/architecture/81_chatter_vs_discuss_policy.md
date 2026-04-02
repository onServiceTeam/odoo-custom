# 81 — Chatter vs Discuss Policy

> Defines what communication goes to record chatter (mail.thread) vs
> Discuss channels vs external thread models.

---

## Decision Tree

```
Event occurs on a business record (case, dispatch, plan, etc.)
│
├── Is it a field change / status transition / internal note?
│   └─→ Record chatter (mail.thread.message_post)
│       Rationale: Native Odoo pattern. Stays on the record.
│       Followers receive email/inbox notification automatically.
│
├── Is it an external customer SMS message (inbound or outbound)?
│   └─→ ons.sms.thread / ons.sms.message
│       Rationale: Separate from chatter to preserve raw channel
│       fidelity (phone numbers, delivery status, media).
│       A summary note is also posted to linked record chatter.
│
├── Is it an external customer email message?
│   └─→ ons.email.thread / ons.email.message
│       Rationale: Same as SMS — preserve raw email headers,
│       threading, HTML body separately from chatter.
│       A summary note is also posted to linked record chatter.
│
├── Is it an internal team alert that needs real-time attention?
│   └─→ Discuss channel post (via ons.notification.rule)
│       Rationale: Discuss is the team's real-time workspace.
│       Use for: new applicants, urgent dispatch events,
│       payment received, escalation alerts.
│
├── Is it a customer-facing notification (reminder, confirmation)?
│   └─→ External delivery (SMS/email via notification rule)
│       + ons.notification.log for tracking
│       The sidecar/middleware handles actual transport.
│
└── Is it a simple record activity (follow-up, review request)?
    └─→ mail.activity
        Rationale: Native Odoo activity system with deadlines.
```

---

## What Goes to Record Chatter

| Event | Auto-post? | Content |
|-------|-----------|---------|
| Status/stage change | Yes (tracking) | Field tracking messages |
| Agent internal note | Yes (manual) | via form chatter widget |
| SMS received on linked thread | Yes (auto) | "SMS from +1..." summary |
| Email received on linked thread | Yes (auto) | "Email from..." summary |
| Dispatch created from case | Yes (auto) | "Dispatch DSP-XXXXX created" |
| Payment recorded | Yes (auto) | "Payment of $X received" |
| Applicant accepted/rejected | Yes (auto) | "Applicant X accepted" |

---

## What Goes to Discuss

| Event | Channel | Content |
|-------|---------|---------|
| New dispatch applicant | Agent's channel | Embed with applicant details |
| Dispatch cancelled | Case thread | Cancellation notice |
| Voice outcome (confirm/cancel) | Case thread | Outcome embed |
| Payment received | Case thread | Payment summary |
| Escalation alert | Manager channel | Alert with urgency |

---

## What Stays in External Thread Models Only

| Data | Model | Why Not Chatter? |
|------|-------|------------------|
| Raw SMS with delivery status | ons.sms.message | Chatter can't track Twilio SID, delivery callbacks, MMS media |
| Raw email with headers | ons.email.message | Chatter can't track RFC Message-ID threading, bounce status |
| Notification delivery log | ons.notification.log | Operational audit, not conversation history |
