# -*- coding: utf-8 -*-
from odoo import fields, models


class DispatchStatus(models.Model):
    _name = "ons.dispatch.status"
    _description = "Dispatch Status"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    is_terminal = fields.Boolean(default=False, help="No further transitions allowed")
    color = fields.Integer(default=0)
    description = fields.Text()

    _code_unique = models.UniqueIndex("(code)", "Status code must be unique.")
