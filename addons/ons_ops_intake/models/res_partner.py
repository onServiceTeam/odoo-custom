# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_segment = fields.Selection(
        [("new", "New"), ("returning", "Returning"), ("subscriber", "Subscriber"), ("vip", "VIP")],
        string="Customer Segment",
    )
    subscription_status = fields.Selection(
        [("none", "None"), ("active", "Active"), ("cancelled", "Cancelled"), ("expired", "Expired")],
        string="Subscription Status",
        default="none",
    )
    lifetime_value = fields.Monetary(string="Lifetime Value", currency_field="currency_id")
    interaction_ids = fields.One2many("ons.interaction", "partner_id", string="Interactions")
    interaction_count = fields.Integer(compute="_compute_interaction_count")

    def _compute_interaction_count(self):
        data = self.env["ons.interaction"]._read_group(
            [("partner_id", "in", self.ids)],
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        counts = {partner.id: count for partner, count in data}
        for rec in self:
            rec.interaction_count = counts.get(rec.id, 0)

    def action_view_interactions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Interactions",
            "res_model": "ons.interaction",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
