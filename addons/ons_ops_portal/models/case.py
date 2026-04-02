# -*- coding: utf-8 -*-
from odoo import models


class Case(models.Model):
    _name = "ons.case"
    _inherit = ["ons.case", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = "/my/cases/%s" % rec.id
