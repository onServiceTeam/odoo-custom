# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    discuss_giphy_api_key = fields.Char(
        string="GIPHY API Key",
        help="GIPHY API key for the GIF picker in Discuss. Get one free at developers.giphy.com.",
        config_parameter="discuss.giphy_api_key",
    )
