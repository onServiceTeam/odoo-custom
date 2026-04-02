# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Dispatch(models.Model):
    _inherit = "ons.dispatch"

    sms_thread_ids = fields.One2many("ons.sms.thread", "dispatch_id", string="SMS Threads")
    email_thread_ids = fields.One2many("ons.email.thread", "dispatch_id", string="Email Threads")
    sms_thread_count = fields.Integer(compute="_compute_comms_counts")
    email_thread_count = fields.Integer(compute="_compute_comms_counts")

    @api.depends("sms_thread_ids", "email_thread_ids")
    def _compute_comms_counts(self):
        for rec in self:
            rec.sms_thread_count = len(rec.sms_thread_ids)
            rec.email_thread_count = len(rec.email_thread_ids)

    def action_view_sms_threads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.sms.thread",
            "name": "SMS Threads",
            "view_mode": "list,form",
            "domain": [("dispatch_id", "=", self.id)],
        }

    def action_view_email_threads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.email.thread",
            "name": "Email Threads",
            "view_mode": "list,form",
            "domain": [("dispatch_id", "=", self.id)],
        }
