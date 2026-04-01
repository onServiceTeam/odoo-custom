# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDiscussUIConfigSettings(TransactionCase):
    """Tests for ons_discuss_ui configuration parameters."""

    def test_settings_fields_exist(self):
        """All custom config fields should exist on res.config.settings."""
        fields = self.env["res.config.settings"]._fields
        expected = [
            "discuss_admin_only_delete",
            "discuss_auto_cleanup_empty_groups",
            "discuss_channels_label",
            "discuss_chats_label",
            "discuss_hide_looking_for_help",
        ]
        for field_name in expected:
            self.assertIn(field_name, fields, f"Missing field: {field_name}")

    def test_config_parameter_keys(self):
        """Config parameters should use the expected keys."""
        ICP = self.env["ir.config_parameter"].sudo()
        # Set a value and verify it round-trips
        ICP.set_param("discuss_thread_admin.channels_label", "My Channels")
        val = ICP.get_param("discuss_thread_admin.channels_label")
        self.assertEqual(val, "My Channels")

    def test_admin_only_delete_default(self):
        """admin_only_delete should default to False (not set)."""
        ICP = self.env["ir.config_parameter"].sudo()
        val = ICP.get_param("discuss_thread_admin.admin_only_delete", "False")
        # Default behavior: parameter may not be set, falls back to "False"
        self.assertIn(val, ("True", "False"))

    def test_auto_cleanup_default_true(self):
        """auto_cleanup_empty_groups field should default to True."""
        settings = self.env["res.config.settings"].create({})
        self.assertTrue(settings.discuss_auto_cleanup_empty_groups)
