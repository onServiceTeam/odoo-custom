# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    plan_ids = fields.One2many(
        "ons.customer.plan",
        "partner_id",
        string="Plans",
    )
    plan_count = fields.Integer(compute="_compute_plan_count")
    active_plan_id = fields.Many2one(
        "ons.customer.plan",
        compute="_compute_active_plan",
        string="Active Plan",
    )

    def _compute_plan_count(self):
        for rec in self:
            rec.plan_count = len(rec.plan_ids)

    def _compute_active_plan(self):
        for rec in self:
            active = rec.plan_ids.filtered(
                lambda p: p.state in ("active", "expiring_soon")
            )
            rec.active_plan_id = active[:1] if active else False

    def action_view_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Customer Plans",
            "res_model": "ons.customer.plan",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
