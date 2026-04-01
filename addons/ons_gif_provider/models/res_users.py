# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_store_data(self, store):
        super()._init_store_data(store)
        # Enable GIF picker if GIPHY key is configured
        giphy_key = self.env["ir.config_parameter"].sudo().get_param("discuss.giphy_api_key")
        if giphy_key:
            store.add_global_values(hasGifPickerFeature=True)
