# -*- coding: utf-8 -*-
from odoo import models


class Interaction(models.Model):
    _inherit = "ons.interaction"

    def action_create_lead(self):
        """Create a CRM lead from this interaction via the CRM module logic."""
        self.ensure_one()
        Lead = self.env["crm.lead"]
        return Lead.action_create_lead_from_interaction(self)
