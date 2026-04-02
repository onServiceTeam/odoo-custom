# -*- coding: utf-8 -*-
from odoo import fields, models


class NotificationLog(models.Model):
    _name = "ons.notification.log"
    _description = "Notification Delivery Log"
    _order = "create_date desc, id desc"

    rule_id = fields.Many2one("ons.notification.rule", string="Rule", index=True, ondelete="set null")
    event_type = fields.Char(index=True)
    res_model = fields.Char(string="Record Model")
    res_id = fields.Integer(string="Record ID")
    channel = fields.Selection(
        [
            ("sms", "SMS"),
            ("email", "Email"),
            ("chatter", "Chatter"),
            ("discuss", "Discuss"),
        ],
        required=True,
        index=True,
    )
    status = fields.Selection(
        [
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
        ],
        default="queued",
        index=True,
    )
    error_message = fields.Text()
    template_id = fields.Many2one("ons.message.template", string="Template Used", ondelete="set null")
    sent_to = fields.Char(help="Phone number, email address, or channel name.")
