# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    interaction_id = fields.Many2one(
        "ons.interaction",
        string="Source Interaction",
        help="The interaction that originated this lead.",
    )
