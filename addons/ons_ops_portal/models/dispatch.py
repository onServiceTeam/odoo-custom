# -*- coding: utf-8 -*-
from odoo import models


class Dispatch(models.Model):
    _name = "ons.dispatch"
    _inherit = ["ons.dispatch", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = "/my/dispatches/%s" % rec.id
