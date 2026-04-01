# -*- coding: utf-8 -*-
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.discuss.channel import ChannelController


class ChannelControllerVoice(ChannelController):

    @http.route(
        "/discuss/channel/admin/set_voice_channel",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def set_voice_channel(self, channel_id, is_voice_channel):
        """Toggle voice channel flag (admin only)."""
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        channel_id = int(channel_id)
        channel = request.env["discuss.channel"].sudo().browse(channel_id)
        if not channel.exists():
            raise NotFound()

        channel.is_voice_channel = bool(is_voice_channel)
        return {"status": "ok", "is_voice_channel": channel.is_voice_channel}
