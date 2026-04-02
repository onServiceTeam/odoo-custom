# -*- coding: utf-8 -*-
from odoo import fields, models


class CancellationReason(models.Model):
    _name = "ons.dispatch.cancellation.reason"
    _description = "Dispatch Cancellation Reason"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    dtmf_key = fields.Char(help="DTMF digit mapped in voice flows")
    is_active = fields.Boolean(default=True)

    _code_unique = models.UniqueIndex("(code)", "Cancellation reason code must be unique.")
