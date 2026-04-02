# 80 — Communications Contract

> Locked by Prompt 9 build.  Covers what `ons_ops_comms` owns, what it
> delegates to Odoo-native `mail.*`, and what stays in the Discuss addons.

---

## 1  Problem Statement

The legacy middleware owns five external channels (Discord, Twilio SMS,
SMTP email, in-app notifications, voice/TTS) plus a notification cascade
engine that fires multi-channel blasts on dispatch events.  The Odoo stack
must:

1. Log external SMS and email threads inside Odoo so operators can see
   full customer communication history on the record itself.
2. Automate posting to record chatter / Discuss when lifecycle events
   fire (case, dispatch, reminders).
3. Provide a configuration surface for notification routing rules.
4. Keep the actual send/delivery in external sidecar workers (Twilio,
   SMTP, Discord bot) — Odoo owns the *data model and intent*, the
   middleware owns the *transport*.

---

## 2  What Belongs Where

| Concern | Owner | Rationale |
|---------|-------|-----------|
| Record chatter (case, dispatch, plan) | `mail.thread` (native) | Already inherited by `ons.case`, `ons.dispatch`, `ons.customer.plan` |
| Internal Discuss channels | Existing `ons_discuss_*` addons | Discord-style threads, voice channels, intake sub-channels |
| SMS thread/message log | `ons_ops_comms` | New `ons.sms.thread` + `ons.sms.message` |
| Email thread/message log | `ons_ops_comms` | New `ons.email.thread` + `ons.email.message` |
| Notification routing config | `ons_ops_comms` | New `ons.notification.rule` |
| Notification event log | `ons_ops_comms` | New `ons.notification.log` |
| Transport (Twilio, SMTP, Discord API) | External sidecar / middleware | Odoo writes intent; sidecar reads + delivers |
| Template rendering | `ons_ops_comms` | `ons.message.template` with `{{variable}}` interpolation |
| In-app notifications | `mail.activity` / `bus.bus` | Use Odoo-native bus for real-time; activity for action items |

---

## 3  SMS Thread Model

Mirrors legacy `sms_threads` + `sms_messages`.

### `ons.sms.thread`
| Field | Type | Notes |
|-------|------|-------|
| phone_number | Char | Normalized 10-digit, indexed |
| partner_id | Many2one res.partner | Resolved customer |
| case_id | Many2one ons.case | Linked case |
| dispatch_id | Many2one ons.dispatch | Linked dispatch |
| is_active | Boolean | Thread still accepting messages |
| unread_count | Integer | Operator unread count |
| last_message_at | Datetime | |
| last_message_preview | Char | Truncated last body |
| message_ids | One2many ons.sms.message | |

### `ons.sms.message`
| Field | Type | Notes |
|-------|------|-------|
| thread_id | Many2one ons.sms.thread | cascade |
| direction | Selection inbound/outbound | |
| from_number / to_number | Char | |
| body | Text | |
| media_urls | Text | JSON array for MMS |
| status | Selection queued/sent/delivered/failed/received | |
| external_sid | Char | Twilio SID |
| sent_by_user_id | Many2one res.users | For outbound |
| error_message | Text | |

---

## 4  Email Thread Model

Mirrors legacy `inbox_messages` with thread grouping.

### `ons.email.thread`
| Field | Type | Notes |
|-------|------|-------|
| subject | Char | Thread subject |
| partner_id | Many2one res.partner | |
| case_id | Many2one ons.case | |
| dispatch_id | Many2one ons.dispatch | |
| email_from | Char | Originator |
| external_thread_id | Char | RFC Message-ID thread grouping |
| is_active | Boolean | |
| unread_count | Integer | |
| last_message_at | Datetime | |
| message_ids | One2many ons.email.message | |

### `ons.email.message`
| Field | Type | Notes |
|-------|------|-------|
| thread_id | Many2one ons.email.thread | cascade |
| direction | Selection inbound/outbound | |
| from_address / to_address | Char | |
| cc_addresses | Char | |
| subject | Char | Per-message subject |
| body_text | Text | Plain text |
| body_html | Html | Rich HTML |
| external_message_id | Char | RFC Message-ID |
| in_reply_to | Char | RFC In-Reply-To |
| status | Selection draft/queued/sent/delivered/bounced/failed | |
| sent_by_user_id | Many2one res.users | |
| error_message | Text | |

---

## 5  Notification Rules

Replaces legacy `dispatch_automation_config` with a broader, record-
type-agnostic rule engine.

### `ons.notification.rule`
| Field | Type | Notes |
|-------|------|-------|
| name | Char | Human label |
| event_type | Selection | case_created, case_stage_change, dispatch_created, dispatch_status_change, dispatch_reminder, voice_outcome_confirmed, voice_outcome_cancelled, voice_outcome_reschedule, voice_outcome_no_answer, payment_received |
| is_active | Boolean | |
| target_model | Char | e.g. "ons.case", "ons.dispatch" |
| notify_customer_sms | Boolean | |
| notify_customer_email | Boolean | |
| notify_internal_chatter | Boolean | |
| notify_internal_discuss | Boolean | |
| sms_template_id | Many2one ons.message.template | |
| email_template_id | Many2one ons.message.template | |
| chatter_template | Text | Simple text with {{vars}} |
| discuss_channel_id | Many2one discuss.channel | Explicit target |

### `ons.notification.log`
| Field | Type | Notes |
|-------|------|-------|
| rule_id | Many2one ons.notification.rule | Which rule fired |
| event_type | Char | Denormalized for search |
| res_model | Char | Target record model |
| res_id | Integer | Target record ID |
| channel | Selection sms/email/chatter/discuss | |
| status | Selection queued/sent/delivered/failed | |
| error_message | Text | |
| template_id | Many2one ons.message.template | |
| sent_to | Char | Phone/email/channel name |

---

## 6  Message Templates

### `ons.message.template`
| Field | Type | Notes |
|-------|------|-------|
| name | Char | Internal reference |
| code | Char(unique) | e.g. `dispatch_confirm_sms` |
| channel | Selection sms/email | |
| subject | Char | Email subject (with {{vars}}) |
| body | Text | Template body with {{vars}} |
| available_variables | Text | Documented list |
| is_active | Boolean | |

---

## 7  Record Linkage Rules

- Every SMS/email thread SHOULD link to a partner if identity is resolved.
- Threads MAY link to a case or dispatch.
- When a message arrives on a thread linked to a case, post a summary
  note to the case chatter automatically.
- When a notification rule fires, the log records which channels were
  attempted and their delivery status.

---

## 8  What This Prompt Does NOT Build

- Actual Twilio/SMTP transport (stays in sidecar)
- Discord bot integration (stays in middleware + existing Discuss addons)
- Voice/TTS call execution (stays in middleware)
- Push notifications (native Odoo `bus.bus` is sufficient)
- AI-powered message drafting (Prompt 10)

The middleware will be updated in Prompt 14 (migration) to read
notification rules from Odoo instead of its own config tables.
