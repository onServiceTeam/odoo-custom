# 82 — External Thread Normalization

> How inbound/outbound SMS and email messages are threaded, linked to
> business records, and surfaced in the Odoo UI.

---

## 1  SMS Thread Normalization

### Thread Identity
A thread is uniquely identified by **normalized phone number** (last 10
digits, US domestic).  One thread per phone number.

### Inbound Flow (webhook → Odoo)
```
Twilio webhook → middleware sidecar
  → sidecar normalizes phone number
  → sidecar calls Odoo JSON-RPC:
      ons.sms.thread.receive_message({
        phone_number, body, media_urls, twilio_sid
      })
  → Odoo finds/creates thread by phone
  → Odoo creates ons.sms.message (direction=inbound)
  → Odoo matches thread to dispatch/case by phone
  → Odoo posts chatter summary to linked case/dispatch
  → Odoo increments unread_count on thread
```

### Outbound Flow (operator → customer)
```
Operator clicks "Send SMS" on case/dispatch
  → Odoo creates ons.sms.message (direction=outbound, status=queued)
  → Sidecar polls for queued messages (or gets notified via bus)
  → Sidecar sends via Twilio
  → Sidecar updates message status (sent/delivered/failed)
```

### Thread-to-Record Matching
Priority order:
1. Thread already has `dispatch_id` set → match
2. Thread already has `case_id` set → match
3. `partner_id` on thread → search for active dispatch/case by partner
4. Phone number → search `res.partner` by `phone` field
5. No match → thread stays unlinked (visible in unmatched queue)

---

## 2  Email Thread Normalization

### Thread Identity
A thread is identified by RFC `Message-ID` / `In-Reply-To` / `References`
header chain, collapsed into `external_thread_id`.

### Inbound Flow
```
IMAP sync (middleware sidecar)
  → sidecar reads from shared inbox
  → sidecar calls Odoo JSON-RPC:
      ons.email.thread.receive_message({
        from_address, to_address, cc, subject,
        body_text, body_html, message_id, in_reply_to
      })
  → Odoo finds thread by in_reply_to / message_id chain
  → Creates new thread if no match
  → Creates ons.email.message (direction=inbound)
  → Attempts partner match by from_address
  → Posts chatter summary to linked case/dispatch if found
```

### Outbound Flow
```
Operator clicks "Send Email" on case/dispatch
  → Odoo creates ons.email.message (direction=outbound, status=queued)
  → Sidecar picks up and sends via SMTP
  → Updates status on delivery
```

### Thread-to-Record Matching
1. Thread already has `case_id` / `dispatch_id` → match
2. `partner_id` → search active case/dispatch
3. `from_address` → search `res.partner.email`
4. `subject` keyword heuristics (e.g. "DSP-00123") → link to dispatch
5. No match → unlinked queue

---

## 3  Chatter Summary Format

When an external message links to a record, a chatter note is auto-posted:

### SMS
```
📱 SMS from +1 (512) 555-9999
"Yes I can confirm the 2pm appointment"
[View full thread →]
```

### Email
```
📧 Email from jane@example.com
Subject: Re: Appointment Confirmation
"Thanks, I'll be available at 2pm..."
[View full thread →]
```

The chatter note uses `message_post(body=..., message_type='comment',
subtype_xmlid='mail.mt_note')` so it appears in the log but does not
trigger follower emails.

---

## 4  Unmatched Thread Queue

Threads without a linked case/dispatch appear in a dedicated
"Unmatched Threads" view accessible under Operations > Communication.
Operators can:
- Manually link a thread to a case or dispatch
- Mark as spam / irrelevant
- Create a new case from the thread context

---

## 5  Data Freshness

- SMS: Near-real-time (webhook-driven via sidecar)
- Email: Periodic sync (sidecar IMAP poll every 2–5 minutes)
- Both: Odoo is system of record for thread state once synced
