# -*- coding: utf-8 -*-
from odoo import fields, models


class DispatchActivityLog(models.Model):
    _name = "ons.dispatch.activity.log"
    _description = "Dispatch Activity Log"
    _order = "create_date desc, id desc"

    dispatch_id = fields.Many2one(
        "ons.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event_type = fields.Selection(
        [
            ("created", "Created"),
            ("status_change", "Status Change"),
            ("approved", "Approved"),
            ("applicant_accepted", "Applicant Accepted"),
            ("applicant_rejected", "Applicant Rejected"),
            ("checklist", "Checklist Update"),
            ("reminder", "Reminder Event"),
            ("voice_outcome", "Voice Outcome"),
            ("note", "Note"),
        ],
        required=True,
        index=True,
    )
    description = fields.Text()
    user_id = fields.Many2one("res.users", default=lambda self: self.env.uid)
