# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    case_id = fields.Many2one("ons.case", string="Service Case", tracking=True, index=True)

    def action_convert_to_case(self):
        """Create a service case from a qualified CRM lead."""
        self.ensure_one()
        if self.case_id:
            # Already has a case — navigate to it
            return {
                "type": "ir.actions.act_window",
                "res_model": "ons.case",
                "res_id": self.case_id.id,
                "view_mode": "form",
                "target": "current",
            }
        if not self.is_convertible:
            raise UserError(
                "Lead is not convertible. Ensure it has a partner, a service-ready "
                "interaction, no decline date, and is not already won."
            )
        # Find interaction — prefer the forward link on the lead, fall back
        # to the reverse relation (interaction.lead_id → this lead).
        interaction = self.interaction_id or self.env["ons.interaction"].search(
            [("lead_id", "=", self.id)], limit=1, order="id desc"
        )
        Case = self.env["ons.case"]
        vals = {
            "partner_id": self.partner_id.id,
            "lead_id": self.id,
            "source_interaction_id": interaction.id if interaction else False,
            "primary_driver_id": self.primary_driver_id.id if self.primary_driver_id else False,
            "intake_agent_id": self.user_id.id if self.user_id else False,
            "assigned_tech_id": (interaction.assisting_agent_id.id if interaction and interaction.assisting_agent_id else False),
            "billing_agent_id": (interaction.billing_agent_id.id if interaction and interaction.billing_agent_id else False),
            "issue_description": interaction.issue_description if interaction else False,
            "online_session_started": (
                interaction.session_path == "session_now" if interaction else False
            ),
        }
        case = Case.create(vals)
        self.case_id = case
        if interaction:
            interaction.case_id = case
        # If session_now, advance to online_session_started stage
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
