# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


# session_path → case stage code mapping
SESSION_STAGE_MAP = {
    "session_now": "online_session_started",
    "callback": "callback_scheduled",
    "onsite_queue": "onsite_dispatched",
}


class Interaction(models.Model):
    _inherit = "ons.interaction"

    case_id = fields.Many2one("ons.case", string="Service Case", tracking=True, index=True)

    def _hook_after_intake(self):
        """Auto-create case + lead when interaction is service-ready."""
        super()._hook_after_intake()
        for rec in self:
            if rec.case_id:
                continue
            if rec.session_path == "no_session":
                continue
            if not rec.partner_id:
                continue
            rec._auto_create_case()

    def _auto_create_case(self):
        """Create CRM lead + service case from a service-ready interaction."""
        self.ensure_one()
        # Auto-create CRM lead if not present
        if not self.lead_id:
            lead_vals = {
                "name": self.subject or self.issue_description[:80] if self.issue_description else self.name,
                "partner_id": self.partner_id.id,
                "phone": self.customer_phone or self.partner_id.phone,
                "email_from": self.customer_email or self.partner_id.email,
                "user_id": self.agent_id.id if self.agent_id else self.env.uid,
                "interaction_id": self.id,
                "primary_driver_id": self.primary_driver_id.id if self.primary_driver_id else False,
            }
            lead = self.env["crm.lead"].create(lead_vals)
            self.lead_id = lead

        # Create case
        Case = self.env["ons.case"]
        case_vals = {
            "partner_id": self.partner_id.id,
            "lead_id": self.lead_id.id,
            "source_interaction_id": self.id,
            "primary_driver_id": self.primary_driver_id.id if self.primary_driver_id else False,
            "intake_agent_id": self.agent_id.id if self.agent_id else self.env.uid,
            "assigned_tech_id": self.assisting_agent_id.id if self.assisting_agent_id else False,
            "billing_agent_id": self.billing_agent_id.id if self.billing_agent_id else False,
            "issue_description": self.issue_description,
            "online_session_started": self.session_path == "session_now",
        }
        case = Case.create(case_vals)
        self.case_id = case
        if self.lead_id and not self.lead_id.case_id:
            self.lead_id.case_id = case

        # Advance case stage based on session_path
        target_code = SESSION_STAGE_MAP.get(self.session_path)
        if target_code:
            target_stage = self.env["ons.case.stage"].search([("code", "=", target_code)], limit=1)
            if target_stage:
                case.stage_id = target_stage

        # If callback, create a reminder activity on the case
        if self.session_path == "callback" and self.callback_time:
            case.activity_schedule(
                "mail.mail_activity_data_call",
                date_deadline=self.callback_time.date(),
                summary="Callback: %s" % (self.subject or self.partner_id.name),
                note="Callback scheduled from intake %s. Timezone: %s" % (
                    self.name, self.callback_timezone or "US/Eastern",
                ),
                user_id=self.assisting_agent_id.id or self.agent_id.id or self.env.uid,
            )

        # Post chatter message on interaction
        self.message_post(
            body="Auto-created case <b>%s</b> (stage: %s)" % (
                case.name, case.stage_id.name if case.stage_id else "Intake",
            ),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )

    def action_create_case(self):
        """Create a service case directly from a service-ready interaction."""
        self.ensure_one()
        if self.case_id:
            raise UserError("This interaction already has a case: %s" % self.case_id.name)
        if self.state not in ("classified", "assigned", "completed"):
            raise UserError("Interaction must be classified before creating a case.")
        if self.session_path == "no_session":
            raise UserError("This interaction path does not qualify for a case.")
        if not self.partner_id:
            raise UserError("A customer must be resolved before creating a case.")
        self._auto_create_case()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.case",
            "res_id": self.case_id.id,
            "view_mode": "form",
            "target": "current",
        }
