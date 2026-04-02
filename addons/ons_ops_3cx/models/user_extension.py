# -*- coding: utf-8 -*-
from odoo import api, fields, models


class UserExtension(models.Model):
    _name = "ons.user.extension"
    _description = "3CX Extension → User Mapping"
    _order = "extension"
    _rec_name = "display_name"

    extension = fields.Char(
        string="3CX Extension",
        required=True,
        index=True,
        help="2-4 digit extension in 3CX PBX (e.g. 1000, 1001).",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Odoo User",
        required=True,
        index=True,
    )
    is_active = fields.Boolean(default=True, index=True)
    notes = fields.Text()

    _extension_unique = models.UniqueIndex(
        "(extension) WHERE is_active = true",
        "Active extension must be unique.",
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("extension", "user_id.name")
    def _compute_display_name(self):
        for rec in self:
            user = rec.user_id.name or "Unassigned"
            rec.display_name = "%s — %s" % (rec.extension, user)
