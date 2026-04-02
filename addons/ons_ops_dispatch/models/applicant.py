# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class DispatchApplicant(models.Model):
    _name = "ons.dispatch.applicant"
    _description = "Dispatch Applicant / Worker Offer"
    _order = "applied_at desc, id desc"

    dispatch_id = fields.Many2one(
        "ons.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # ── External IDs ────────────────────────────────────────────────
    wm_applicant_id = fields.Char(string="WM Applicant ID")
    wm_worker_id = fields.Char(string="WM Worker ID")
    wm_offer_id = fields.Char(string="WM Offer ID", help="Used for accept/decline API calls.")

    # ── Worker info ─────────────────────────────────────────────────
    worker_name = fields.Char(required=True)
    worker_email = fields.Char()
    worker_phone = fields.Char()
    worker_rating = fields.Float(digits=(3, 1))

    # ── Pricing ─────────────────────────────────────────────────────
    proposed_rate = fields.Float(string="Proposed Rate")
    counter_offer_rate = fields.Float(string="Counter Offer")

    # ── Notes ───────────────────────────────────────────────────────
    worker_notes = fields.Text()
    our_notes = fields.Text(string="Internal Notes")

    # ── Status ──────────────────────────────────────────────────────
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("withdrawn", "Withdrawn"),
        ],
        default="pending",
        required=True,
        index=True,
    )

    # ── Timestamps ──────────────────────────────────────────────────
    applied_at = fields.Datetime(default=fields.Datetime.now)
    reviewed_at = fields.Datetime()
    reviewed_by = fields.Many2one("res.users")
    accepted_at = fields.Datetime()
    rejected_at = fields.Datetime()
    rejection_reason = fields.Text()

    # ── Unique per dispatch + external ID ───────────────────────────
    _applicant_unique = models.UniqueIndex(
        "(dispatch_id, wm_applicant_id) WHERE wm_applicant_id IS NOT NULL",
        "Each applicant can only apply once per dispatch.",
    )

    # ── Actions ─────────────────────────────────────────────────────
    def action_accept(self):
        self.ensure_one()
        if self.status != "pending":
            raise UserError("Only pending applicants can be accepted.")

        # Only one accepted applicant per dispatch
        existing = self.dispatch_id.applicant_ids.filtered(lambda a: a.status == "accepted")
        if existing:
            raise UserError("Dispatch already has an accepted applicant: %s" % existing[0].worker_name)

        self.write({
            "status": "accepted",
            "accepted_at": fields.Datetime.now(),
            "reviewed_at": fields.Datetime.now(),
            "reviewed_by": self.env.uid,
        })

        # Update dispatch
        self.dispatch_id.write({
            "assigned_worker_name": self.worker_name,
            "assigned_worker_id": self.wm_worker_id or "",
        })
        self.dispatch_id.action_change_status("assigned")
        self.dispatch_id._log_activity("applicant_accepted", "Accepted applicant: %s" % self.worker_name)

    def action_reject(self, reason=None):
        self.ensure_one()
        if self.status != "pending":
            raise UserError("Only pending applicants can be rejected.")

        self.write({
            "status": "rejected",
            "rejected_at": fields.Datetime.now(),
            "reviewed_at": fields.Datetime.now(),
            "reviewed_by": self.env.uid,
            "rejection_reason": reason or "",
        })
        self.dispatch_id._log_activity("applicant_rejected", "Rejected applicant: %s" % self.worker_name)
