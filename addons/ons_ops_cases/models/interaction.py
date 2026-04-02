# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class Interaction(models.Model):
    _inherit = "ons.interaction"

    case_id = fields.Many2one("ons.case", string="Service Case", tracking=True, index=True)

    def action_create_case(self):
        """Create a service case directly from a service-ready interaction."""
        self.ensure_one()
        if self.case_id:
            raise UserError("This interaction already has a case: %s" % self.case_id.name)
        if self.state not in ("classified", "assigned", "completed"):
            raise UserError("Interaction must be classified before creating a case.")
        if self.session_path in ("no_session", "not_applicable"):
            raise UserError("This interaction path does not qualify for a case.")
        if not self.partner_id:
            raise UserError("A customer must be resolved before creating a case.")

        Case = self.env["ons.case"]
        vals = {
            "partner_id": self.partner_id.id,
            "source_interaction_id": self.id,
            "lead_id": self.lead_id.id if self.lead_id else False,
            "primary_driver_id": self.primary_driver_id.id if self.primary_driver_id else False,
            "intake_agent_id": self.agent_id.id if self.agent_id else False,
            "assigned_tech_id": self.assisting_agent_id.id if self.assisting_agent_id else False,
            "billing_agent_id": self.billing_agent_id.id if self.billing_agent_id else False,
            "issue_description": self.issue_description,
            "online_session_started": self.session_path == "session_now",
        }
        case = Case.create(vals)
        self.case_id = case
        if self.lead_id and not self.lead_id.case_id:
            self.lead_id.case_id = case
        # If session_now, advance stage
        if case.online_session_started:
            oss_stage = self.env["ons.case.stage"].search([("code", "=", "online_session_started")], limit=1)
            if oss_stage:
                case.stage_id = oss_stage
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.case",
            "res_id": case.id,
            "view_mode": "form",
            "target": "current",
        }
