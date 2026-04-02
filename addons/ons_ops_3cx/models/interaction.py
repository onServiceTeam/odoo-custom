# -*- coding: utf-8 -*-
from odoo import fields, models


class Interaction(models.Model):
    _inherit = "ons.interaction"

    call_log_id = fields.Many2one(
        "ons.call.log",
        string="Call Log",
        index=True,
        help="The underlying 3CX CDR record for this interaction.",
    )
