# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestSecurityGroups(TransactionCase):
    """Verify the onService Operations security group hierarchy."""

    def test_groups_exist(self):
        """All three operations groups should be loadable by xmlid."""
        Groups = self.env["res.groups"]
        for xmlid in [
            "ons_ops_core.group_ops_agent",
            "ons_ops_core.group_ops_manager",
            "ons_ops_core.group_ops_admin",
        ]:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(group, f"Group {xmlid} not found")
            self.assertIsInstance(group, type(Groups))

    def test_category_exists(self):
        """The onService Operations module category should exist."""
        cat = self.env.ref(
            "ons_ops_core.module_category_ons_operations",
            raise_if_not_found=False,
        )
        self.assertTrue(cat, "Module category not found")
        self.assertEqual(cat.name, "onService Operations")

    def test_privilege_exists(self):
        """The onService Operations privilege (Odoo 19 group selector) should exist."""
        priv = self.env.ref(
            "ons_ops_core.privilege_ons_operations",
            raise_if_not_found=False,
        )
        self.assertTrue(priv, "Privilege record not found")
        self.assertEqual(priv.name, "onService Operations")

    def test_manager_implies_agent(self):
        """Manager group must imply Agent group."""
        manager = self.env.ref("ons_ops_core.group_ops_manager")
        agent = self.env.ref("ons_ops_core.group_ops_agent")
        self.assertIn(agent, manager.implied_ids)

    def test_admin_implies_manager(self):
        """Admin group must imply Manager group."""
        admin = self.env.ref("ons_ops_core.group_ops_admin")
        manager = self.env.ref("ons_ops_core.group_ops_manager")
        self.assertIn(manager, admin.implied_ids)

    def test_agent_implies_internal_user(self):
        """Agent group must imply base.group_user (internal user)."""
        agent = self.env.ref("ons_ops_core.group_ops_agent")
        internal = self.env.ref("base.group_user")
        self.assertIn(internal, agent.implied_ids)

    def test_admin_user_has_all_groups(self):
        """A user with Admin group should transitively have Manager and Agent."""
        admin_group = self.env.ref("ons_ops_core.group_ops_admin")

        # Add the admin user to the ops admin group
        user = self.env.user
        admin_group.write({"user_ids": [(4, user.id)]})
        user.invalidate_recordset()

        self.assertTrue(
            user.has_group("ons_ops_core.group_ops_admin"),
            "User should have Admin group",
        )
        self.assertTrue(
            user.has_group("ons_ops_core.group_ops_manager"),
            "Admin user should transitively have Manager group",
        )
        self.assertTrue(
            user.has_group("ons_ops_core.group_ops_agent"),
            "Admin user should transitively have Agent group",
        )
