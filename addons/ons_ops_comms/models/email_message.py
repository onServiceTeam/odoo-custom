# -*- coding: utf-8 -*-
from odoo import fields, models


class EmailMessage(models.Model):
    _name = "ons.email.message"
    _description = "Email Message"
    _order = "create_date desc, id desc"

    thread_id = fields.Many2one(
        "ons.email.thread",
        required=True,
        ondelete="cascade",
        index=True,
    )
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )
    from_address = fields.Char()
    to_address = fields.Char()
    cc_addresses = fields.Char()
    subject = fields.Char()
    body_text = fields.Text(string="Plain Text")
    body_html = fields.Html(string="HTML Body", sanitize=True)
    external_message_id = fields.Char(string="Message-ID", index=True)
    in_reply_to = fields.Char(string="In-Reply-To")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("bounced", "Bounced"),
            ("failed", "Failed"),
            ("received", "Received"),
        ],
        default="queued",
        index=True,
    )
    sent_by_user_id = fields.Many2one("res.users", string="Sent By")
    is_read = fields.Boolean(default=False)
    error_message = fields.Text()
