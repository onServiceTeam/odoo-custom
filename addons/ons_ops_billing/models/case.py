# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class Case(models.Model):
    _inherit = "ons.case"

    # ── Billing lines ───────────────────────────────────────────────
    case_line_ids = fields.One2many(
        "ons.case.line",
        "case_id",
        string="Billing Lines",
    )
    amount_total = fields.Float(
        compute="_compute_amount_total",
        store=True,
        digits=(10, 2),
    )

    # ── Invoice ─────────────────────────────────────────────────────
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        tracking=True,
        domain="[('move_type', '=', 'out_invoice')]",
    )
    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Invoice Payment",
    )

    # ── Payment tracking ────────────────────────────────────────────
    payment_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("invoice_sent", "Invoice Sent"),
            ("paid", "Paid"),
            ("partial", "Partial"),
            ("no_charge", "No Charge"),
            ("manual", "Manual Payment"),
            ("declined", "Declined"),
            ("refunded", "Refunded"),
            ("disputed", "Disputed"),
        ],
        default="pending",
        tracking=True,
        index=True,
    )
    payment_amount = fields.Float(digits=(10, 2), tracking=True)
    no_charge_reason = fields.Selection(
        [
            ("subscriber", "Subscriber — Covered Under Plan"),
            ("warranty", "Warranty — Service Guarantee"),
            ("goodwill", "Goodwill — Customer Satisfaction"),
            ("followup", "Follow-up — No Additional Charge"),
            ("other", "Other"),
        ],
    )
    manual_payment_method = fields.Selection(
        [
            ("check", "Check"),
            ("cash", "Cash"),
            ("wire", "Wire Transfer"),
            ("zelle", "Zelle"),
            ("venmo", "Venmo"),
            ("paypal", "PayPal"),
            ("other", "Other"),
        ],
    )
    manual_payment_reference = fields.Char()
    manual_payment_date = fields.Date()

    # ── Plan link ───────────────────────────────────────────────────
    plan_id = fields.Many2one(
        "ons.customer.plan",
        string="Customer Plan",
        tracking=True,
        help="The customer plan being serviced, if applicable.",
    )

    # ── Computed ────────────────────────────────────────────────────
    is_billable = fields.Boolean(
        compute="_compute_is_billable",
        store=True,
    )

    @api.depends("case_line_ids.subtotal")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.case_line_ids.mapped("subtotal"))

    @api.depends("case_line_ids", "is_closed", "is_won")
    def _compute_is_billable(self):
        for rec in self:
            has_lines = bool(rec.case_line_ids)
            # closed_lost is not billable
            rec.is_billable = has_lines and not (rec.is_closed and not rec.is_won)

    # ── Actions ─────────────────────────────────────────────────────
    def action_create_invoice(self):
        """Create a draft invoice from case billing lines."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError("This case already has an invoice: %s" % self.invoice_id.name)
        if not self.case_line_ids:
            raise UserError("Add at least one billing line before creating an invoice.")
        if not self.partner_id:
            raise UserError("A customer is required to create an invoice.")

        invoice_lines = []
        for line in self.case_line_ids:
            invoice_lines.append((0, 0, {
                "product_id": line.product_id.id,
                "name": line.description or line.product_id.name,
                "quantity": line.quantity,
                "price_unit": line.unit_price,
            }))

        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_origin": self.name,
            "invoice_line_ids": invoice_lines,
        })
        self.invoice_id = invoice
        self.payment_status = "invoice_sent"
        # Auto-attribute billing to the user who created the invoice
        if not self.billing_agent_id:
            self.billing_agent_id = self.env.uid
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_no_charge(self):
        """Mark case as no charge (subscriber/warranty/goodwill)."""
        self.ensure_one()
        if not self.no_charge_reason:
            raise UserError("Select a no-charge reason first.")
        self.payment_status = "no_charge"
        self.payment_amount = 0.0

    def action_record_manual_payment(self):
        """Record a manual payment (check, cash, Zelle, etc.)."""
        self.ensure_one()
        if not self.manual_payment_method:
            raise UserError("Select a manual payment method first.")
        if not self.payment_amount:
            raise UserError("Enter the payment amount.")
        self.payment_status = "manual"
        self.manual_payment_date = fields.Date.context_today(self)

    def action_mark_paid(self):
        """Mark the case as paid."""
        self.ensure_one()
        self.payment_status = "paid"

    def action_mark_declined(self):
        """Mark payment as declined."""
        self.ensure_one()
        self.payment_status = "declined"

    def action_view_invoice(self):
        """Open the linked invoice."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_plan(self):
        """Open the linked customer plan."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.customer.plan",
            "res_id": self.plan_id.id,
            "view_mode": "form",
            "target": "current",
        }
