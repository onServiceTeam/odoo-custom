# -*- coding: utf-8 -*-
from odoo import fields, models


class DispatchVoiceCall(models.Model):
    _name = "ons.dispatch.voice.call"
    _description = "Dispatch Voice Call"
    _order = "queued_at desc, id desc"

    dispatch_id = fields.Many2one(
        "ons.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    reminder_id = fields.Many2one(
        "ons.dispatch.reminder",
        ondelete="set null",
    )

    # ── Call config ─────────────────────────────────────────────────
    call_type = fields.Selection(
        [
            ("customer_reminder", "Customer Reminder"),
            ("tech_confirmation", "Tech Confirmation"),
            ("tech_cancellation", "Tech Cancellation"),
            ("manual", "Manual"),
            ("escalation", "Escalation"),
        ],
        required=True,
    )
    target_phone = fields.Char(required=True)
    target_type = fields.Selection(
        [("customer", "Customer"), ("technician", "Technician")],
        required=True,
    )

    # ── Status ──────────────────────────────────────────────────────
    status = fields.Selection(
        [
            ("queued", "Queued"),
            ("dialing", "Dialing"),
            ("ringing", "Ringing"),
            ("answered", "Answered"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("no_answer", "No Answer"),
            ("busy", "Busy"),
            ("failed", "Failed"),
            ("retry_scheduled", "Retry Scheduled"),
            ("skipped", "Skipped"),
        ],
        default="queued",
        required=True,
        index=True,
    )

    # ── Outcome ─────────────────────────────────────────────────────
    outcome = fields.Selection(
        [
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
            ("reschedule_requested", "Reschedule Requested"),
            ("voicemail_left", "Voicemail Left"),
            ("no_answer", "No Answer"),
            ("failed", "Failed"),
            ("transferred", "Transferred"),
            ("skipped", "Skipped"),
        ],
        index=True,
    )
    outcome_notes = fields.Text()
    cancellation_reason_id = fields.Many2one(
        "ons.dispatch.cancellation.reason",
        string="Cancellation Reason",
    )
    transferred_to = fields.Char(help="Queue name if transferred to agent.")

    # ── DTMF tracking ──────────────────────────────────────────────
    dtmf_inputs = fields.Char(help="Comma-separated DTMF digits pressed.")
    dtmf_final_action = fields.Char(help="Resolved action from last DTMF.")

    # ── External references ─────────────────────────────────────────
    threecx_call_id = fields.Char(string="3CX / Twilio Call ID")
    from_extension = fields.Char()

    # ── Timing ──────────────────────────────────────────────────────
    queued_at = fields.Datetime(default=fields.Datetime.now)
    dialed_at = fields.Datetime()
    answered_at = fields.Datetime()
    completed_at = fields.Datetime()
    duration_seconds = fields.Integer()

    # ── Retry ───────────────────────────────────────────────────────
    attempt_number = fields.Integer(default=1)
    max_attempts = fields.Integer(default=3)
    retry_after = fields.Datetime()

    # ── TTS ─────────────────────────────────────────────────────────
    script_template = fields.Text(help="TTS template with {{vars}}")
    script_rendered = fields.Text(help="Final rendered script")
