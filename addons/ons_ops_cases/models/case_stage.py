# -*- coding: utf-8 -*-
from odoo import fields, models


class CaseStage(models.Model):
    _name = "ons.case.stage"
    _description = "Case Pipeline Stage"
    _order = "sequence, id"
    _rec_name = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    is_closed = fields.Boolean(string="Closing Stage", help="Cases in this stage are considered closed.")
    is_won = fields.Boolean(string="Won Stage", help="Terminal success stage.")
    fold = fields.Boolean(string="Folded in Kanban")
    color = fields.Integer()

    _code_unique = models.UniqueIndex("(code)", "Stage code must be unique.")
