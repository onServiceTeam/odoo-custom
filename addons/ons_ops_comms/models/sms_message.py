# -*- coding: utf-8 -*-
from odoo import fields, models


class SmsMessage(models.Model):
    _name = "ons.sms.message"
    _description = "SMS Message"
    _order = "create_date desc, id desc"

    thread_id = fields.Many2one(
        "ons.sms.thread",
        required=True,
        ondelete="cascade",
        index=True,
    )
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )
    from_number = fields.Char()
    to_number = fields.Char()
    body = fields.Text()
    media_urls = fields.Text(help="JSON array of media URLs for MMS.")
    status = fields.Selection(
        [
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("received", "Received"),
        ],
        default="queued",
        index=True,
    )
    external_sid = fields.Char(string="External SID", index=True, help="Twilio Message SID")
    sent_by_user_id = fields.Many2one("res.users", string="Sent By")
    is_read = fields.Boolean(default=False)
    error_message = fields.Text()
    error_code = fields.Char()
