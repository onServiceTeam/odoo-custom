# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestWebRTCHealth(TransactionCase):
    """Tests for the WebRTC health check endpoint logic."""

    def test_ice_server_model_accessible(self):
        """mail.ice.server model should be accessible."""
        count = self.env["mail.ice.server"].sudo().search_count([])
        self.assertIsInstance(count, int)

    def test_sfu_config_parameter(self):
        """mail.sfu_server_url should be retrievable."""
        ICP = self.env["ir.config_parameter"].sudo()
        val = ICP.get_param("mail.sfu_server_url", "")
        self.assertIsInstance(val, str)
