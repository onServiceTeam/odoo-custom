# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CallDriver(models.Model):
    _name = "ons.call.driver"
    _description = "Call Driver Code"
    _order = "category, sort_order, name"
    _rec_name = "display_name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    category = fields.Selection(
        [
            ("boot_startup", "Boot & Startup"),
            ("performance", "Performance"),
            ("security", "Security"),
            ("network", "Network"),
            ("printer", "Printer"),
            ("email", "Email"),
            ("account", "Account"),
            ("browser", "Browser"),
            ("office", "Office"),
            ("finance", "Finance"),
            ("social", "Social"),
            ("audio_video", "Audio & Video"),
            ("display", "Display"),
            ("hardware", "Hardware"),
            ("data", "Data"),
            ("setup", "Setup"),
            ("mobile", "Mobile"),
            ("os", "OS"),
            ("billing", "Billing"),
            ("physical", "Physical"),
            ("meta", "Meta"),
        ],
        required=True,
        index=True,
    )
    description = fields.Text()
    handling_instructions = fields.Text()
    common_phrases = fields.Text(help="Customer language examples, one per line")
    detection_keywords = fields.Text(help="AI matching keywords, one per line")
    expected_resolution_minutes = fields.Integer()
    requires_callback = fields.Boolean()
    requires_onsite = fields.Boolean()
    is_upsell_opportunity = fields.Boolean()
    coaching_priority = fields.Selection(
        [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("critical", "Critical")],
        default="normal",
    )
    sort_order = fields.Integer(default=100)
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)
    interaction_count = fields.Integer(compute="_compute_interaction_count")

    _code_unique = models.UniqueIndex("(code)", "Driver code must be unique.")

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    def _compute_interaction_count(self):
        data = self.env["ons.interaction"]._read_group(
            [("primary_driver_id", "in", self.ids)],
            groupby=["primary_driver_id"],
            aggregates=["__count"],
        )
        counts = {driver.id: count for driver, count in data}
        for rec in self:
            rec.interaction_count = counts.get(rec.id, 0)

    def action_view_interactions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Interactions",
            "res_model": "ons.interaction",
            "view_mode": "list,form",
            "domain": [("primary_driver_id", "=", self.id)],
            "context": {"default_primary_driver_id": self.id},
        }
