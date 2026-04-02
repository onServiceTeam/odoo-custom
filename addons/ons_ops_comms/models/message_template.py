# -*- coding: utf-8 -*-
from odoo import fields, models


class MessageTemplate(models.Model):
    _name = "ons.message.template"
    _description = "Message Template"
    _order = "channel, name"
    _rec_name = "name"

    name = fields.Char(required=True)
    code = fields.Char(index=True, help="Machine-readable identifier.")
    channel = fields.Selection(
        [("sms", "SMS"), ("email", "Email")],
        required=True,
        index=True,
    )
    subject = fields.Char(help="Email subject line. Supports {{variable}} placeholders.")
    body = fields.Text(required=True, help="Template body. Supports {{variable}} placeholders.")
    available_variables = fields.Text(
        help="Documented list of available variables for this template.",
    )
    is_active = fields.Boolean(default=True)

    _template_unique = models.UniqueIndex(
        "(code) WHERE code IS NOT NULL",
        "Template code must be unique.",
    )
