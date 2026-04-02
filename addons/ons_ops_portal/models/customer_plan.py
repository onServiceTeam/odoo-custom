# -*- coding: utf-8 -*-
from odoo import models


class CustomerPlan(models.Model):
    _name = "ons.customer.plan"
    _inherit = ["ons.customer.plan", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = "/my/plans/%s" % rec.id
