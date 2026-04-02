# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class CustomerPlan(models.Model):
    _name = "ons.customer.plan"
    _description = "Customer Subscription Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "end_date asc, id desc"
    _rec_name = "display_name"

    # ── Core ────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Plan Product",
        required=True,
        tracking=True,
        domain="[('product_tmpl_id.ons_is_subscription', '=', True)]",
    )
    plan_code = fields.Char(
        related="product_id.product_tmpl_id.ons_product_code",
        store=True,
        index=True,
    )
    amount = fields.Float(digits=(10, 2), tracking=True)

    # ── Term ────────────────────────────────────────────────────────
    term_months = fields.Integer(
        related="product_id.product_tmpl_id.ons_subscription_months",
        store=True,
    )
    start_date = fields.Date(required=True, tracking=True)
    end_date = fields.Date(
        compute="_compute_end_date",
        store=True,
        index=True,
    )

    # ── State ───────────────────────────────────────────────────────
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expiring_soon", "Expiring Soon"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )

    # ── Computed ────────────────────────────────────────────────────
    days_until_expiry = fields.Integer(
        compute="_compute_expiry_fields",
        store=True,
    )
    is_expiring_soon = fields.Boolean(
        compute="_compute_expiry_fields",
        store=True,
        index=True,
    )
    is_renewable = fields.Boolean(
        compute="_compute_is_renewable",
        store=True,
    )

    # ── Links ───────────────────────────────────────────────────────
    source_case_id = fields.Many2one(
        "ons.case",
        string="Source Case",
        help="The case that sold this plan.",
    )
    source_invoice_id = fields.Many2one(
        "account.move",
        string="Source Invoice",
    )
    renewal_case_id = fields.Many2one(
        "ons.case",
        string="Renewal Case",
        help="The case that renewed this plan.",
    )
    stripe_subscription_id = fields.Char(
        string="Stripe Subscription ID",
        index=True,
        help="For migration/sync reference with Stripe.",
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ── Computed fields ─────────────────────────────────────────────
    @api.depends("start_date", "term_months")
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date and rec.term_months:
                rec.end_date = rec.start_date + relativedelta(months=rec.term_months)
            else:
                rec.end_date = False

    @api.depends("end_date", "state")
    def _compute_expiry_fields(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.end_date and rec.state in ("active", "expiring_soon"):
                rec.days_until_expiry = (rec.end_date - today).days
                rec.is_expiring_soon = 0 < rec.days_until_expiry <= 30
            else:
                rec.days_until_expiry = 0
                rec.is_expiring_soon = False

    @api.depends("state")
    def _compute_is_renewable(self):
        for rec in self:
            rec.is_renewable = rec.state not in ("cancelled", "draft")

    @api.depends("partner_id", "plan_code", "state")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.partner_id:
                parts.append(rec.partner_id.name or "")
            if rec.plan_code:
                parts.append(rec.plan_code)
            if rec.state:
                parts.append("(%s)" % rec.state)
            rec.display_name = " — ".join(parts) if parts else "New Plan"

    # ── Actions ─────────────────────────────────────────────────────
    def action_activate(self):
        """Activate a draft plan."""
        for rec in self:
            if rec.state != "draft":
                raise UserError("Only draft plans can be activated.")
            rec.state = "active"

    def action_cancel(self):
        """Cancel the plan."""
        for rec in self:
            if rec.state in ("expired", "cancelled"):
                raise UserError("Plan is already %s." % rec.state)
            rec.state = "cancelled"

    def action_mark_expiring(self):
        """Mark plan as expiring soon (called by cron or manually)."""
        for rec in self:
            if rec.state != "active":
                raise UserError("Only active plans can be marked expiring.")
            rec.state = "expiring_soon"

    def action_expire(self):
        """Mark plan as expired."""
        for rec in self:
            if rec.state not in ("active", "expiring_soon"):
                raise UserError("Only active or expiring plans can expire.")
            rec.state = "expired"

    @api.model
    def _cron_update_plan_states(self):
        """Scheduled action to auto-update plan states based on dates."""
        today = fields.Date.context_today(self)
        # Expire past-due plans
        expired = self.search([
            ("state", "in", ("active", "expiring_soon")),
            ("end_date", "<=", today),
        ])
        expired.write({"state": "expired"})
        # Mark expiring soon
        threshold = today + relativedelta(days=30)
        expiring = self.search([
            ("state", "=", "active"),
            ("end_date", ">", today),
            ("end_date", "<=", threshold),
        ])
        expiring.write({"state": "expiring_soon"})
