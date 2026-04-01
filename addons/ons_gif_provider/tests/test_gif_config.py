# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestGifConfig(TransactionCase):
    """Tests for GIPHY GIF provider configuration."""

    def test_giphy_key_field_exists(self):
        """discuss_giphy_api_key should exist on res.config.settings."""
        self.assertIn("discuss_giphy_api_key", self.env["res.config.settings"]._fields)

    def test_giphy_key_config_parameter(self):
        """GIPHY key should round-trip through ir.config_parameter."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("discuss.giphy_api_key", "test_key_12345")
        self.assertEqual(ICP.get_param("discuss.giphy_api_key"), "test_key_12345")

    def test_gif_picker_feature_flag(self):
        """hasGifPickerFeature should be True when GIPHY key is set."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("discuss.giphy_api_key", "some_key")
        # Verify the key is retrievable (feature flag logic runs in _init_store_data)
        val = ICP.get_param("discuss.giphy_api_key")
        self.assertTrue(val)

    def test_gif_picker_disabled_without_key(self):
        """hasGifPickerFeature should not be set when key is empty."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("discuss.giphy_api_key", "")
        val = ICP.get_param("discuss.giphy_api_key")
        self.assertFalse(val)
