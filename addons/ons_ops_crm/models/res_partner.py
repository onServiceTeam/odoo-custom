# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    consent_ids = fields.One2many(
        "ons.contact.consent",
        "partner_id",
        string="Consent Records",
    )
    consent_count = fields.Integer(compute="_compute_consent_count")

    def _compute_consent_count(self):
        data = self.env["ons.contact.consent"]._read_group(
            [("partner_id", "in", self.ids)],
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        counts = {partner.id: count for partner, count in data}
        for rec in self:
            rec.consent_count = counts.get(rec.id, 0)

    def has_consent(self, channel, scope):
        """Return True if partner has active opted-in consent for channel+scope."""
        self.ensure_one()
        return bool(self.env["ons.contact.consent"].search_count([
            ("partner_id", "=", self.id),
            ("channel", "=", channel),
            ("scope", "=", scope),
            ("status", "in", ("opted_in", "double_opted_in")),
            ("active", "=", True),
        ]))

    def action_view_consents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Consent Records",
            "res_model": "ons.contact.consent",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
