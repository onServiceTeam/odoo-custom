# -*- coding: utf-8 -*-
from odoo import fields, models


class Case(models.Model):
    _inherit = "ons.case"

    dispatch_ids = fields.One2many("ons.dispatch", "case_id", string="Dispatches")
    dispatch_count = fields.Integer(compute="_compute_dispatch_count")
    active_dispatch_id = fields.Many2one(
        "ons.dispatch",
        compute="_compute_active_dispatch",
        string="Active Dispatch",
    )

    def _compute_dispatch_count(self):
        for rec in self:
            rec.dispatch_count = len(rec.dispatch_ids)

    def _compute_active_dispatch(self):
        for rec in self:
            active = rec.dispatch_ids.filtered(lambda d: not d.is_terminal)
            rec.active_dispatch_id = active[:1] if active else False

    def action_create_dispatch(self):
        """Create a dispatch from this case."""
        self.ensure_one()
        dispatch = self.env["ons.dispatch"].create_from_case(self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.dispatch",
            "res_id": dispatch.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_dispatches(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.dispatch",
            "name": "Dispatches",
            "view_mode": "list,form",
            "domain": [("case_id", "=", self.id)],
        }
