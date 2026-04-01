# -*- coding: utf-8 -*-
from markupsafe import Markup
from werkzeug.exceptions import Forbidden, NotFound

from odoo import _
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.discuss.channel import ChannelController


class ChannelControllerInherit(ChannelController):

    # ── Thread (sub-channel) deletion with admin controls ──────────────

    @http.route(
        "/discuss/channel/sub_channel/delete",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def discuss_delete_sub_channel(self, sub_channel_id):
        channel = request.env["discuss.channel"].search_fetch(
            [("id", "=", sub_channel_id)]
        )
        if not channel or not channel.parent_channel_id:
            raise NotFound()

        is_admin = request.env.user.has_group("base.group_system")
        is_creator = channel.create_uid == request.env.user
        admin_only = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("discuss_thread_admin.admin_only_delete", "False")
            == "True"
        )

        if admin_only:
            if not is_admin:
                raise NotFound()
        else:
            if not is_creator and not is_admin:
                raise NotFound()

        body = (
            Markup(
                '<div class="o_mail_notification" data-oe-type="thread_deletion">'
                "%s</div>"
            )
            % channel.name
        )
        channel.parent_channel_id.message_post(
            body=body, subtype_xmlid="mail.mt_comment"
        )
        channel.sudo().unlink()

    @http.route(
        "/discuss/channel/sub_channel/thread_settings",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def discuss_thread_settings(self):
        admin_only = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("discuss_thread_admin.admin_only_delete", "False")
            == "True"
        )
        is_admin = request.env.user.has_group("base.group_system")
        return {
            "admin_only_delete": admin_only,
            "is_admin": is_admin,
        }

    # ── Admin kick member from channel ─────────────────────────────────

    @http.route(
        "/discuss/channel/admin/kick_member",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def admin_kick_member(self, channel_id, partner_id):
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        channel_id = int(channel_id)
        partner_id = int(partner_id)

        channel = request.env["discuss.channel"].sudo().browse(channel_id)
        if not channel.exists():
            raise NotFound()

        partner = request.env["res.partner"].sudo().browse(partner_id)
        if not partner.exists():
            raise NotFound()

        member = request.env["discuss.channel.member"].sudo().search(
            [("channel_id", "=", channel_id), ("partner_id", "=", partner_id)],
            limit=1,
        )
        if not member:
            return {"status": "not_found", "message": "Member not in channel"}

        member_name = partner.name
        # Directly unlink the member to avoid triggering auto-cleanup from _action_unfollow
        member.unlink()

        # Post admin notification
        body = Markup(
            '<div class="o_mail_notification">'
            "%s was removed by an administrator</div>"
        ) % member_name
        channel.sudo().message_post(
            body=body,
            subtype_xmlid="mail.mt_comment",
            author_id=request.env.user.partner_id.id,
        )
        return {"status": "ok", "message": f"{member_name} removed"}

    # ── Admin hard-delete a message (permanent removal) ────────────────

    @http.route(
        "/discuss/channel/admin/hard_delete_message",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def admin_hard_delete_message(self, message_id):
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        message_id = int(message_id)
        message = request.env["mail.message"].sudo().browse(message_id)
        if not message.exists():
            raise NotFound()

        # Only allow deleting discuss messages (not system notifications etc.)
        if message.message_type not in ("comment", "email"):
            return {"status": "error", "message": "Cannot delete system messages"}

        # mail.message.unlink() already sends bus notifications to affected partners
        message.unlink()
        return {"status": "ok"}

    # ── Admin channel info (member list, message count) ────────────────

    @http.route(
        "/discuss/channel/admin/channel_info",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def admin_channel_info(self, channel_id):
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        channel_id = int(channel_id)
        channel = request.env["discuss.channel"].sudo().browse(channel_id)
        if not channel.exists():
            raise NotFound()

        members = []
        for member in channel.channel_member_ids:
            partner = member.partner_id
            members.append({
                "id": member.id,
                "partner_id": partner.id,
                "name": partner.name or "(Guest)",
                "email": partner.email or "",
                "last_seen_dt": str(member.last_seen_dt) if member.last_seen_dt else None,
            })

        msg_count = request.env["mail.message"].sudo().search_count(
            [("model", "=", "discuss.channel"), ("res_id", "=", channel_id)]
        )

        return {
            "id": channel.id,
            "name": channel.name or "(Unnamed)",
            "channel_type": channel.channel_type,
            "member_count": channel.member_count,
            "message_count": msg_count,
            "members": members,
            "create_date": str(channel.create_date),
        }

    # ── Pre-leave check (for last-member warning) ──────────────────────

    @http.route(
        "/discuss/channel/admin/pre_leave_check",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def pre_leave_check(self, channel_id):
        channel_id = int(channel_id)
        channel = request.env["discuss.channel"].sudo().browse(channel_id)
        if not channel.exists():
            return {"can_leave": True, "warning": None}

        member_count = channel.member_count
        is_admin = request.env.user.has_group("base.group_system")
        auto_cleanup = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("discuss_thread_admin.auto_cleanup_empty_groups", "True")
            == "True"
        )

        warning = None
        if member_count <= 1 and auto_cleanup and channel.channel_type == "group":
            warning = "last_member_auto_delete"
        elif member_count <= 1 and channel.channel_type == "group":
            warning = "last_member"
        elif is_admin and member_count > 1:
            # Admin leaving but others remain — just informational
            warning = None

        return {
            "can_leave": True,
            "warning": warning,
            "member_count": member_count,
            "auto_cleanup": auto_cleanup,
            "channel_type": channel.channel_type,
        }

    # ── Set work status (Slack-style) ──────────────────────────────────

    @http.route(
        "/discuss/set_work_status",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def set_work_status(self, emoji="", text=""):
        """Set the current user's work status emoji + text."""
        request.env.user.sudo().write({
            "work_status_emoji": (emoji or "")[:4],
            "work_status_text": (text or "")[:100],
        })
        return {"status": "ok"}

    # ── Toggle voice channel flag (admin only) ─────────────────────────

    @http.route(
        "/discuss/channel/admin/set_voice_channel",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def set_voice_channel(self, channel_id, is_voice_channel):
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        channel_id = int(channel_id)
        channel = request.env["discuss.channel"].sudo().browse(channel_id)
        if not channel.exists():
            raise NotFound()

        channel.is_voice_channel = bool(is_voice_channel)
        return {"status": "ok", "is_voice_channel": channel.is_voice_channel}

    # ── Reorder channels (drag-and-drop, admin only) ───────────────────

    @http.route(
        "/discuss/channel/admin/reorder",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def reorder_channels(self, channel_ids):
        """Set channel sequences based on the order of channel_ids list."""
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        Channel = request.env["discuss.channel"].sudo()
        for idx, cid in enumerate(channel_ids):
            cid = int(cid)
            channel = Channel.browse(cid)
            if channel.exists():
                channel.sequence = idx * 10
        return {"status": "ok"}

    # ── Customer Intake (creates thread under agent's channel) ─────────

    @http.route(
        "/discuss/intake/create",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def create_intake(self, customer_name, phone="", subject="",
                      description="", channel_id=None, agent_id=None):
        """Create a customer intake record which auto-creates a thread."""
        vals = {
            "name": str(customer_name)[:200],
            "phone": str(phone)[:20] if phone else "",
            "subject": str(subject)[:200] if subject else "",
            "description": str(description)[:2000] if description else "",
        }
        if channel_id:
            vals["channel_id"] = int(channel_id)
        if agent_id:
            vals["agent_id"] = int(agent_id)

        intake = request.env["discuss.intake"].create(vals)

        result = {
            "status": "ok",
            "intake_id": intake.id,
            "thread_id": intake.thread_id.id if intake.thread_id else None,
            "thread_name": intake.thread_id.name if intake.thread_id else None,
            "channel_id": intake.channel_id.id if intake.channel_id else None,
        }
        return result
