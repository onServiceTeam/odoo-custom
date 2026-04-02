# -*- coding: utf-8 -*-
from odoo import fields, models


class ChecklistConfig(models.Model):
    _name = "ons.dispatch.checklist.config"
    _description = "Dispatch Checklist Default Items"
    _order = "sequence, id"

    name = fields.Char(string="Item Name", required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    is_required = fields.Boolean(default=False)
    is_active = fields.Boolean(default=True)

    _code_unique = models.UniqueIndex("(code)", "Checklist code must be unique.")
