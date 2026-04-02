# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CaseStageHistory(models.Model):
    _name = "ons.case.stage.history"
    _description = "Case Stage History Entry"
    _order = "entered_at desc, id desc"

    case_id = fields.Many2one("ons.case", required=True, ondelete="cascade", index=True)
    stage_id = fields.Many2one("ons.case.stage", required=True, string="Stage")
    entered_at = fields.Datetime(required=True)
    exited_at = fields.Datetime()
    duration_hours = fields.Float(
        compute="_compute_duration_hours",
        store=True,
        digits=(10, 1),
    )
    user_id = fields.Many2one("res.users", string="Changed By")
    is_override = fields.Boolean(string="Manual Override")
    notes = fields.Text()

    @api.depends("entered_at", "exited_at")
    def _compute_duration_hours(self):
        for rec in self:
            if rec.entered_at and rec.exited_at:
                delta = rec.exited_at - rec.entered_at
                rec.duration_hours = round(delta.total_seconds() / 3600.0, 1)
            else:
                rec.duration_hours = 0.0
