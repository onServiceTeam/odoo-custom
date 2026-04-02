# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ContactConsent(models.Model):
    _name = "ons.contact.consent"
    _description = "Contact Consent Record"
    _inherit = ["mail.thread"]
    _order = "create_date desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
        index=True,
        ondelete="cascade",
    )
    channel = fields.Selection(
        [
            ("email", "Email"),
            ("sms", "SMS"),
            ("phone", "Phone"),
            ("any", "Any"),
        ],
        required=True,
        tracking=True,
    )
    scope = fields.Selection(
        [
            ("marketing", "Marketing"),
            ("operational", "Operational"),
            ("callback", "Callback"),
            ("renewal", "Renewal"),
            ("service_terms", "Service Terms"),
        ],
        required=True,
        tracking=True,
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("opted_in", "Opted In"),
            ("double_opted_in", "Double Opted In"),
            ("opted_out", "Opted Out"),
            ("revoked", "Revoked"),
        ],
        required=True,
        default="pending",
        tracking=True,
        index=True,
    )
    capture_source = fields.Selection(
        [
            ("web_form", "Web Form"),
            ("phone_call", "Phone Call"),
            ("email_reply", "Email Reply"),
            ("sms_reply", "SMS Reply"),
            ("manual", "Manual"),
        ],
        required=True,
        tracking=True,
    )
    captured_by_id = fields.Many2one(
        "res.users",
        string="Captured By",
        default=lambda self: self.env.user,
    )
    interaction_id = fields.Many2one(
        "ons.interaction",
        string="Source Interaction",
    )

    # ── Timestamps (write-once) ─────────────────────────────────────
    opted_in_at = fields.Datetime(readonly=True, copy=False)
    confirmed_at = fields.Datetime(readonly=True, copy=False)
    opted_out_at = fields.Datetime(readonly=True, copy=False)
    revoked_at = fields.Datetime(readonly=True, copy=False)

    evidence = fields.Text()
    active = fields.Boolean(default=True)

    display_name = fields.Char(compute="_compute_display_name", store=True)

    _partner_channel_scope_unique = models.UniqueIndex(
        "(partner_id, channel, scope) WHERE active = true",
        "Only one active consent per partner, channel, and scope.",
    )

    @api.depends("channel", "scope", "status")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.get_selection_label('channel', rec.channel)} / {rec.get_selection_label('scope', rec.scope)} — {rec.get_selection_label('status', rec.status)}"

    def get_selection_label(self, field_name, value):
        """Return the label for a selection field value."""
        if not value:
            return ""
        return dict(self._fields[field_name].selection).get(value, value)

    # ── State transitions ───────────────────────────────────────────
    def action_opt_in(self):
        for rec in self:
            if rec.status != "pending":
                raise UserError("Can only opt-in from Pending status.")
            rec.write({
                "status": "opted_in",
                "opted_in_at": fields.Datetime.now(),
            })
            rec.message_post(
                body="Consent status changed to Opted In.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def action_confirm(self):
        for rec in self:
            if rec.status != "opted_in":
                raise UserError("Can only confirm from Opted In status.")
            rec.write({
                "status": "double_opted_in",
                "confirmed_at": fields.Datetime.now(),
            })
            rec.message_post(
                body="Consent status changed to Double Opted In.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def action_opt_out(self):
        for rec in self:
            if rec.status in ("opted_out", "revoked"):
                raise UserError("Consent is already terminal. Create a new record to re-consent.")
            rec.write({
                "status": "opted_out",
                "opted_out_at": fields.Datetime.now(),
            })
            rec.message_post(
                body="Consent status changed to Opted Out.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def action_revoke(self):
        self.env.user._is_admin() or self._check_group("ons_ops_core.group_ops_admin")
        for rec in self:
            if rec.status == "revoked":
                raise UserError("Consent is already revoked.")
            rec.write({
                "status": "revoked",
                "revoked_at": fields.Datetime.now(),
                "active": False,
            })
            rec.message_post(
                body="Consent REVOKED by administrator.",
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def _check_group(self, group_xmlid):
        if not self.env.user.has_group(group_xmlid):
            raise UserError("Only administrators can revoke consent.")

    def write(self, vals):
        # Enforce write-once on timestamp fields
        timestamp_fields = ("opted_in_at", "confirmed_at", "opted_out_at", "revoked_at")
        for field in timestamp_fields:
            if field in vals and vals[field]:
                for rec in self:
                    if rec[field]:
                        raise UserError(f"The field '{field}' is write-once and already set.")
        return super().write(vals)
