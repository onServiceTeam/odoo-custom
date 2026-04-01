# -*- coding: utf-8 -*-
import logging
import socket

from odoo import http
from odoo.http import request
from werkzeug.exceptions import Forbidden

_logger = logging.getLogger(__name__)


class WebRTCHealthController(http.Controller):

    @http.route(
        "/ons_webrtc/health",
        methods=["POST"],
        type="jsonrpc",
        auth="user",
    )
    def health_check(self):
        """Admin-only health check for WebRTC infrastructure."""
        if not request.env.user.has_group("base.group_system"):
            raise Forbidden("Admin access required")

        get_param = request.env["ir.config_parameter"].sudo().get_param

        # Check SFU
        sfu_url = get_param("mail.sfu_server_url", "")
        sfu_ok = False
        if sfu_url:
            try:
                # Parse host:port from URL
                from urllib.parse import urlparse
                parsed = urlparse(sfu_url)
                host = parsed.hostname or "localhost"
                port = parsed.port or 8070
                sock = socket.create_connection((host, port), timeout=3)
                sock.close()
                sfu_ok = True
            except Exception as e:
                _logger.warning("SFU health check failed: %s", e)

        # Check ICE servers configured
        ice_servers = request.env["mail.ice.server"].sudo().search_count([])

        return {
            "sfu_url": sfu_url,
            "sfu_reachable": sfu_ok,
            "ice_server_count": ice_servers,
        }
