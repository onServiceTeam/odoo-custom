# -*- coding: utf-8 -*-
from odoo import fields, models


class DispatchReminder(models.Model):
    _name = "ons.dispatch.reminder"
    _description = "Dispatch Reminder"
    _order = "scheduled_for, id"

    dispatch_id = fields.Many2one(
        "ons.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    minutes_before = fields.Integer(
        required=True,
        help="Minutes before scheduled visit.",
    )
    scheduled_for = fields.Datetime(
        required=True,
        index=True,
        help="Exact UTC fire time.",
    )
    sent = fields.Boolean(default=False, index=True)
    sent_at = fields.Datetime()
    error_message = fields.Text()
    retry_count = fields.Integer(default=0)

    # ── Per-channel delivery tracking ───────────────────────────────
    discord_sent = fields.Boolean(default=False)
    sms_sent = fields.Boolean(default=False)
    email_sent = fields.Boolean(default=False)
    voice_queued = fields.Boolean(default=False)

    _reminder_unique = models.UniqueIndex(
        "(dispatch_id, minutes_before)",
        "Each interval can only exist once per dispatch.",
    )

    def action_mark_sent(self):
        """Mark reminder as sent (for manual override)."""
        self.write({"sent": True, "sent_at": fields.Datetime.now()})

    def action_cancel(self):
        """Cancel unsent reminder."""
        self.filtered(lambda r: not r.sent).write({"sent": True, "sent_at": fields.Datetime.now()})
