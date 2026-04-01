# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestOpsShell(TransactionCase):
    """Verify the Operations Shell menus and actions."""

    def test_dashboard_action_exists(self):
        """The dashboard client action should be loadable by xmlid."""
        action = self.env.ref(
            "ons_ops_shell.action_ops_dashboard",
            raise_if_not_found=False,
        )
        self.assertTrue(action, "Dashboard action not found")
        self.assertEqual(action.tag, "ons_ops_shell.dashboard")

    def test_root_menu_exists(self):
        """The top-level Operations menu should be loadable."""
        menu = self.env.ref(
            "ons_ops_shell.menu_ops_root",
            raise_if_not_found=False,
        )
        self.assertTrue(menu, "Root menu not found")
        self.assertEqual(menu.name, "Operations")

    def test_root_menu_links_to_dashboard(self):
        """Root menu action should point to the dashboard client action."""
        menu = self.env.ref("ons_ops_shell.menu_ops_root")
        action = self.env.ref("ons_ops_shell.action_ops_dashboard")
        # The menu stores action as "ir.actions.client,<id>"
        self.assertIn(str(action.id), str(menu.action))

    def test_section_menus_exist(self):
        """All section parent menus should be loadable."""
        sections = [
            "ons_ops_shell.menu_ops_intake_section",
            "ons_ops_shell.menu_ops_comms_section",
            "ons_ops_shell.menu_ops_management_section",
            "ons_ops_shell.menu_ops_config_section",
        ]
        for xmlid in sections:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(menu, f"Section menu {xmlid} not found")

    def test_leaf_menus_have_actions(self):
        """Leaf menus (Customers, Pipeline, Discuss) should have actions."""
        leaves = [
            "ons_ops_shell.menu_ops_customers",
            "ons_ops_shell.menu_ops_pipeline",
            "ons_ops_shell.menu_ops_discuss",
        ]
        for xmlid in leaves:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(menu, f"Leaf menu {xmlid} not found")
            self.assertTrue(menu.action, f"Leaf menu {xmlid} has no action")

    def test_management_section_requires_manager(self):
        """Management section should only be visible to managers."""
        menu = self.env.ref("ons_ops_shell.menu_ops_management_section")
        manager_group = self.env.ref("ons_ops_core.group_ops_manager")
        self.assertIn(
            manager_group,
            menu.group_ids,
            "Management section should require manager group",
        )

    def test_config_section_requires_admin(self):
        """Configuration section should only be visible to ops admins."""
        menu = self.env.ref("ons_ops_shell.menu_ops_config_section")
        admin_group = self.env.ref("ons_ops_core.group_ops_admin")
        self.assertIn(
            admin_group,
            menu.group_ids,
            "Configuration section should require admin group",
        )

    def test_ops_root_requires_agent(self):
        """Root Operations menu should require at least Agent group."""
        menu = self.env.ref("ons_ops_shell.menu_ops_root")
        agent_group = self.env.ref("ons_ops_core.group_ops_agent")
        self.assertIn(
            agent_group,
            menu.group_ids,
            "Root menu should require agent group",
        )
