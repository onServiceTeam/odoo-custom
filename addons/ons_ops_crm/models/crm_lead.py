# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # ── Lead classification ─────────────────────────────────────────
    lead_type = fields.Selection(
        [
            ("inquiry", "Inquiry"),
            ("callback_request", "Callback Request"),
            ("service_lead", "Service Lead"),
            ("nurture", "Nurture"),
            ("renewal", "Renewal"),
        ],
        string="Lead Type",
        tracking=True,
        index=True,
    )
    caller_relationship = fields.Selection(
        [
            ("first_time_lead", "First-Time Lead"),
            ("returning_no_plan", "Returning — No Plan"),
            ("active_subscriber", "Active Subscriber"),
            ("past_subscriber", "Past Subscriber"),
        ],
        string="Caller Relationship",
        tracking=True,
    )

    # ── Callback ────────────────────────────────────────────────────
    callback_requested = fields.Boolean(tracking=True)
    callback_preferred_time = fields.Char(string="Preferred Callback Time")

    # ── Decline / no-sale ───────────────────────────────────────────
    declined_reason = fields.Text(string="Decline Reason")
    decline_date = fields.Date()

    # ── Driver link (copied from interaction for quick pipeline filtering)
    primary_driver_id = fields.Many2one(
        "ons.call.driver",
        string="Primary Driver",
        tracking=True,
        index=True,
    )

    # ── Computed flags ──────────────────────────────────────────────
    is_nurture_eligible = fields.Boolean(
        compute="_compute_is_nurture_eligible",
        store=True,
    )
    is_convertible = fields.Boolean(
        compute="_compute_is_convertible",
        store=True,
    )

    @api.depends("partner_id", "lead_type", "stage_id", "active")
    def _compute_is_nurture_eligible(self):
        for rec in self:
            rec.is_nurture_eligible = bool(
                rec.active
                and not rec.stage_id.is_won
                and rec.lead_type != "inquiry"
                and (rec.phone or rec.email_from)
                and rec.partner_id
                and rec.partner_id.has_consent("email", "marketing")
            )

    @api.depends("partner_id", "interaction_id", "stage_id", "active", "decline_date")
    def _compute_is_convertible(self):
        for rec in self:
            interaction = rec.interaction_id
            has_service_path = (
                interaction
                and interaction.session_path
                in ("session_now", "callback", "onsite_queue", "session_scheduled")
            )
            rec.is_convertible = bool(
                rec.active
                and rec.partner_id
                and has_service_path
                and not rec.decline_date
                and not rec.stage_id.is_won
            )

    # ── Lead creation from interaction ──────────────────────────────
    @api.model
    def _get_caller_relationship(self, partner):
        """Map partner.customer_segment to lead caller_relationship."""
        mapping = {
            "new": "first_time_lead",
            "returning": "returning_no_plan",
            "subscriber": "active_subscriber",
            "vip": "active_subscriber",
        }
        return mapping.get(partner.customer_segment, "first_time_lead") if partner else "first_time_lead"

    @api.model
    def _find_existing_active_lead(self, phone, driver):
        """Check for an existing active lead with the same phone and driver."""
        if not phone:
            return self.browse()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7:
            return self.browse()
        normalized = digits[-10:]
        candidates = self.search([
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
            ("phone", "like", normalized),
        ])
        if driver:
            candidates = candidates.filtered(
                lambda l: l.primary_driver_id.id == driver.id
            )
        return candidates[:1]

    def action_create_lead_from_interaction(self, interaction, lead_type=None):
        """Create a CRM lead from a classified interaction.

        Returns the created lead or an existing one if duplicate detected.
        """
        self.ensure_one() if self else None

        if interaction.state not in ("classified", "assigned", "completed"):
            raise UserError("Interaction must be classified before creating a lead.")

        # Determine lead_type from interaction if not provided
        if not lead_type:
            lead_type = self._determine_lead_type(interaction)

        if not lead_type:
            raise UserError(
                "Cannot determine lead type for this interaction. "
                "The interaction may not qualify for lead creation."
            )

        # Duplicate check
        existing = self._find_existing_active_lead(
            interaction.customer_phone,
            interaction.primary_driver_id,
        )
        if existing:
            # Attach interaction to existing lead instead of creating duplicate
            interaction.lead_id = existing
            existing.message_post(
                body="Additional interaction %s attached to this lead."
                % interaction.name,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
            return existing

        # Build lead values
        partner = interaction.partner_id
        driver = interaction.primary_driver_id
        name_parts = []
        if driver:
            name_parts.append(driver.name)
        if partner:
            name_parts.append(partner.name)
        elif interaction.customer_phone:
            name_parts.append(interaction.customer_phone)
        lead_name = " — ".join(name_parts) or interaction.name

        vals = {
            "name": lead_name,
            "type": "lead",
            "interaction_id": interaction.id,
            "partner_id": partner.id if partner else False,
            "phone": interaction.customer_phone or False,
            "email_from": (partner.email if partner else interaction.customer_email) or False,
            "lead_type": lead_type,
            "caller_relationship": self._get_caller_relationship(partner),
            "primary_driver_id": driver.id if driver else False,
            "callback_requested": lead_type == "callback_request",
            "user_id": interaction.agent_id.id if interaction.agent_id else False,
        }

        lead = self.create(vals)
        interaction.lead_id = lead
        return lead

    @api.model
    def _determine_lead_type(self, interaction):
        """Decide lead_type based on interaction session_path and driver."""
        sp = interaction.session_path
        if sp in ("session_now", "session_scheduled", "onsite_queue"):
            return "service_lead"
        if sp == "callback":
            return "callback_request"
        if sp == "no_session":
            driver = interaction.primary_driver_id
            if driver and driver.category == "billing":
                return None  # Billing inquiries stay as interaction-only
            partner = interaction.partner_id
            if (
                partner
                and partner.customer_segment in ("returning", "subscriber", "vip")
                and driver
                and driver.is_upsell_opportunity
            ):
                return "renewal"
            return None  # Agent may manually promote
        return None  # not_applicable or missing

    # ── Nurture promotion ───────────────────────────────────────────
    def action_promote_to_nurture(self):
        for rec in self:
            if rec.stage_id.is_won or not rec.active:
                raise UserError("Cannot promote a won or archived lead to nurture.")
            if not (rec.phone or rec.email_from):
                raise UserError("Lead must have a phone or email to be nurture-eligible.")
            rec.lead_type = "nurture"

    # ── Decline ─────────────────────────────────────────────────────
    def action_mark_declined(self):
        for rec in self:
            if rec.stage_id.is_won:
                raise UserError("Cannot decline a won lead.")
            rec.write({
                "decline_date": fields.Date.context_today(rec),
            })
