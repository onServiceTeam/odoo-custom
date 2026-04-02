# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class SmsThread(models.Model):
    _name = "ons.sms.thread"
    _description = "SMS Conversation Thread"
    _order = "last_message_at desc, id desc"
    _rec_name = "display_name"

    phone_number = fields.Char(
        required=True,
        index=True,
        help="Normalized 10-digit phone number.",
    )
    partner_id = fields.Many2one("res.partner", string="Customer", index=True)
    case_id = fields.Many2one("ons.case", string="Linked Case", index=True, ondelete="set null")
    dispatch_id = fields.Many2one("ons.dispatch", string="Linked Dispatch", index=True, ondelete="set null")
    is_active = fields.Boolean(default=True, index=True)
    unread_count = fields.Integer(default=0)
    last_message_at = fields.Datetime()
    last_message_preview = fields.Char(string="Last Message")
    message_ids = fields.One2many("ons.sms.message", "thread_id", string="Messages")
    message_count = fields.Integer(compute="_compute_message_count")

    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    def _compute_display_name(self):
        for rec in self:
            partner_name = rec.partner_id.name if rec.partner_id else "Unknown"
            rec.display_name = "%s — %s" % (partner_name, rec.phone_number)

    @staticmethod
    def _normalize_phone(phone):
        """Strip to last 10 digits."""
        digits = re.sub(r"\D", "", phone or "")
        return digits[-10:] if len(digits) >= 10 else digits

    @api.model
    def find_or_create(self, phone_number, partner_id=False, case_id=False, dispatch_id=False):
        """Find existing thread by phone or create a new one."""
        normalized = self._normalize_phone(phone_number)
        thread = self.search([("phone_number", "=", normalized)], limit=1)
        if not thread:
            vals = {"phone_number": normalized}
            if partner_id:
                vals["partner_id"] = partner_id
            if case_id:
                vals["case_id"] = case_id
            if dispatch_id:
                vals["dispatch_id"] = dispatch_id
            thread = self.create(vals)
        else:
            # Update linkage if not yet set
            update = {}
            if partner_id and not thread.partner_id:
                update["partner_id"] = partner_id
            if case_id and not thread.case_id:
                update["case_id"] = case_id
            if dispatch_id and not thread.dispatch_id:
                update["dispatch_id"] = dispatch_id
            if update:
                thread.write(update)
        return thread

    @api.model
    def receive_message(self, phone_number, body, media_urls=None, external_sid=None):
        """Called by sidecar when an inbound SMS arrives."""
        normalized = self._normalize_phone(phone_number)

        # Try to find partner by phone
        partner = self.env["res.partner"].search(
            [("phone", "like", normalized[-10:])], limit=1
        )

        thread = self.find_or_create(normalized, partner_id=partner.id if partner else False)

        msg = self.env["ons.sms.message"].create({
            "thread_id": thread.id,
            "direction": "inbound",
            "from_number": normalized,
            "to_number": "",
            "body": body or "",
            "media_urls": media_urls or "",
            "external_sid": external_sid or "",
            "status": "received",
        })

        # Update thread
        thread.write({
            "unread_count": thread.unread_count + 1,
            "last_message_at": fields.Datetime.now(),
            "last_message_preview": (body or "")[:100],
        })

        # Post chatter summary on linked case/dispatch
        self._post_chatter_summary(thread, msg)
        return msg

    def _post_chatter_summary(self, thread, message):
        """Post a note to linked record chatter."""
        if not message.body:
            return
        direction = "from" if message.direction == "inbound" else "to"
        phone = message.from_number if message.direction == "inbound" else message.to_number
        body_preview = (message.body or "")[:200]
        note = "<p>📱 SMS %s %s<br/>%s</p>" % (direction, phone, body_preview)

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

    def action_link_to_case(self, case_id):
        """Manually link thread to a case."""
        self.write({"case_id": case_id})

    def action_link_to_dispatch(self, dispatch_id):
        """Manually link thread to a dispatch."""
        self.write({"dispatch_id": dispatch_id})

    def action_mark_read(self):
        """Mark all messages in thread as read."""
        self.write({"unread_count": 0})
        self.message_ids.filtered(lambda m: not m.is_read).write({"is_read": True})
