# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.discuss.channel import ChannelController


class ChannelControllerUI(ChannelController):

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
