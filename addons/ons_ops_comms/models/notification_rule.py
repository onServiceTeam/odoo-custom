# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


EVENT_TYPES = [
    ("case_created", "Case Created"),
    ("case_stage_change", "Case Stage Changed"),
    ("dispatch_created", "Dispatch Created"),
    ("dispatch_status_change", "Dispatch Status Changed"),
    ("dispatch_reminder", "Dispatch Reminder"),
    ("voice_outcome_confirmed", "Voice — Confirmed"),
    ("voice_outcome_cancelled", "Voice — Cancelled"),
    ("voice_outcome_reschedule", "Voice — Reschedule"),
    ("voice_outcome_no_answer", "Voice — No Answer"),
    ("payment_received", "Payment Received"),
]


class NotificationRule(models.Model):
    _name = "ons.notification.rule"
    _description = "Notification Routing Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(index=True, help="Machine-readable identifier.")
    sequence = fields.Integer(default=10)
    event_type = fields.Selection(EVENT_TYPES, required=True, index=True)
    is_active = fields.Boolean(default=True, index=True)

    # Target model filter (optional — if blank, fires for all)
    target_model = fields.Char(help="e.g. ons.case or ons.dispatch")

    # ── Channel flags ───────────────────────────────────────────────
    notify_customer_sms = fields.Boolean(string="SMS to Customer")
    notify_customer_email = fields.Boolean(string="Email to Customer")
    notify_internal_chatter = fields.Boolean(string="Post to Chatter")
    notify_internal_discuss = fields.Boolean(string="Post to Discuss")

    # ── Templates ───────────────────────────────────────────────────
    sms_template_id = fields.Many2one(
        "ons.message.template",
        string="SMS Template",
        domain="[('channel', '=', 'sms')]",
    )
    email_template_id = fields.Many2one(
        "ons.message.template",
        string="Email Template",
        domain="[('channel', '=', 'email')]",
    )
    chatter_body = fields.Text(
        string="Chatter Template",
        help="Text with {{variable}} placeholders.",
    )
    discuss_channel_id = fields.Many2one(
        "discuss.channel",
        string="Discuss Channel",
        help="Explicit target channel for internal alerts.",
    )
    discuss_body = fields.Text(
        string="Discuss Template",
        help="Text with {{variable}} placeholders.",
    )

    _rule_unique = models.UniqueIndex(
        "(code) WHERE code IS NOT NULL",
        "Rule code must be unique.",
    )

    def fire(self, record, variables=None):
        """Execute this rule for a given record and variable dict.

        Actual SMS/email transport is delegated to the sidecar.
        This method logs the intent and handles chatter/discuss posting.
        """
        self.ensure_one()
        if not self.is_active:
            return

        variables = variables or {}
        log_model = self.env["ons.notification.log"]

        # ── Chatter ─────────────────────────────────────────────────
        if self.notify_internal_chatter and hasattr(record, "message_post"):
            body = self._render_template(self.chatter_body, variables)
            if body:
                record.message_post(
                    body="<p>%s</p>" % body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
                log_model.create({
                    "rule_id": self.id,
                    "event_type": self.event_type,
                    "res_model": record._name,
                    "res_id": record.id,
                    "channel": "chatter",
                    "status": "sent",
                    "sent_to": "record chatter",
                })

        # ── Discuss ─────────────────────────────────────────────────
        if self.notify_internal_discuss and self.discuss_channel_id:
            body = self._render_template(self.discuss_body or self.chatter_body, variables)
            if body:
                self.discuss_channel_id.message_post(
                    body="<p>%s</p>" % body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
                log_model.create({
                    "rule_id": self.id,
                    "event_type": self.event_type,
                    "res_model": record._name,
                    "res_id": record.id,
                    "channel": "discuss",
                    "status": "sent",
                    "sent_to": self.discuss_channel_id.name,
                })

        # ── SMS (queued for sidecar) ────────────────────────────────
        if self.notify_customer_sms and self.sms_template_id:
            log_model.create({
                "rule_id": self.id,
                "event_type": self.event_type,
                "res_model": record._name,
                "res_id": record.id,
                "channel": "sms",
                "status": "queued",
                "template_id": self.sms_template_id.id,
                "sent_to": variables.get("customer_phone", ""),
            })

        # ── Email (queued for sidecar) ──────────────────────────────
        if self.notify_customer_email and self.email_template_id:
            log_model.create({
                "rule_id": self.id,
                "event_type": self.event_type,
                "res_model": record._name,
                "res_id": record.id,
                "channel": "email",
                "status": "queued",
                "template_id": self.email_template_id.id,
                "sent_to": variables.get("customer_email", ""),
            })

    @staticmethod
    def _render_template(template, variables):
        """Simple {{variable}} interpolation."""
        if not template:
            return ""
        result = template
        for key, value in variables.items():
            result = re.sub(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                str(value or ""),
                result,
            )
        return result
