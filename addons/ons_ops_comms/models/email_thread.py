# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EmailThread(models.Model):
    _name = "ons.email.thread"
    _description = "Email Conversation Thread"
    _order = "last_message_at desc, id desc"
    _rec_name = "subject"

    subject = fields.Char(required=True, index=True)
    partner_id = fields.Many2one("res.partner", string="Customer", index=True)
    case_id = fields.Many2one("ons.case", string="Linked Case", index=True, ondelete="set null")
    dispatch_id = fields.Many2one("ons.dispatch", string="Linked Dispatch", index=True, ondelete="set null")
    email_from = fields.Char(string="From", help="Originator email address.")
    external_thread_id = fields.Char(
        string="External Thread ID",
        index=True,
        help="RFC Message-ID chain for threading.",
    )
    is_active = fields.Boolean(default=True, index=True)
    unread_count = fields.Integer(default=0)
    last_message_at = fields.Datetime()
    message_ids = fields.One2many("ons.email.message", "thread_id", string="Messages")
    message_count = fields.Integer(compute="_compute_message_count")

    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    @api.model
    def find_or_create(self, subject, email_from, external_thread_id=None, partner_id=False):
        """Find thread by external_thread_id or create new."""
        thread = False
        if external_thread_id:
            thread = self.search([("external_thread_id", "=", external_thread_id)], limit=1)
        if not thread:
            vals = {
                "subject": subject or "(No Subject)",
                "email_from": email_from or "",
                "external_thread_id": external_thread_id or "",
            }
            if partner_id:
                vals["partner_id"] = partner_id
            thread = self.create(vals)
        return thread

    @api.model
    def receive_message(self, from_address, to_address, subject, body_text=None,
                        body_html=None, message_id=None, in_reply_to=None, cc=None):
        """Called by sidecar when an inbound email arrives."""
        # Resolve thread by in_reply_to chain
        ext_thread_id = in_reply_to or message_id

        # Try partner match by email
        partner = self.env["res.partner"].search(
            [("email", "=ilike", from_address)], limit=1
        ) if from_address else self.env["res.partner"]

        thread = self.find_or_create(
            subject=subject,
            email_from=from_address,
            external_thread_id=ext_thread_id,
            partner_id=partner.id if partner else False,
        )

        msg = self.env["ons.email.message"].create({
            "thread_id": thread.id,
            "direction": "inbound",
            "from_address": from_address or "",
            "to_address": to_address or "",
            "cc_addresses": cc or "",
            "subject": subject or "",
            "body_text": body_text or "",
            "body_html": body_html or "",
            "external_message_id": message_id or "",
            "in_reply_to": in_reply_to or "",
            "status": "received",
        })

        thread.write({
            "unread_count": thread.unread_count + 1,
            "last_message_at": fields.Datetime.now(),
        })

        # Post chatter summary
        self._post_chatter_summary(thread, msg)
        return msg

    def _post_chatter_summary(self, thread, message):
        """Post a note to linked record chatter."""
        if not (message.body_text or message.subject):
            return
        direction = "from" if message.direction == "inbound" else "to"
        addr = message.from_address if message.direction == "inbound" else message.to_address
        preview = (message.body_text or "")[:200]
        note = "<p>📧 Email %s %s<br/>Subject: %s<br/>%s</p>" % (
            direction, addr, message.subject or "", preview
        )

        records = []
        if thread.case_id:
            records.append(thread.case_id)
        if thread.dispatch_id:
            records.append(thread.dispatch_id)
        for record in records:
            if hasattr(record, "message_post"):
                record.message_post(
                    body=note,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

    def action_mark_read(self):
        self.write({"unread_count": 0})
        self.message_ids.filtered(lambda m: not m.is_read).write({"is_read": True})
