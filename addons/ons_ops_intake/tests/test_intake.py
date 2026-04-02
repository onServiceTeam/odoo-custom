# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestCallDriver(TransactionCase):
    """Tests for ons.call.driver model."""

    def test_seed_data_loaded(self):
        """Seed call-driver records should exist after install."""
        driver = self.env.ref(
            "ons_ops_intake.driver_boot_bsod",
            raise_if_not_found=False,
        )
        self.assertTrue(driver, "BSOD driver not loaded from seed data")
        self.assertEqual(driver.code, "BOOT_BLUE_SCREEN")

    def test_code_unique_constraint(self):
        """Duplicate driver codes should be rejected."""
        self.env["ons.call.driver"].create({
            "name": "Test A",
            "code": "TEST_UNIQUE_1",
            "category": "meta",
        })
        with self.assertRaises(Exception):
            self.env["ons.call.driver"].create({
                "name": "Test B",
                "code": "TEST_UNIQUE_1",
                "category": "meta",
            })

    def test_display_name_computed(self):
        """display_name should show [CODE] Name format."""
        driver = self.env["ons.call.driver"].create({
            "name": "Widget Fail",
            "code": "TST_WIDGET",
            "category": "meta",
        })
        self.assertEqual(driver.display_name, "[TST_WIDGET] Widget Fail")

    def test_interaction_count(self):
        """interaction_count should reflect linked interactions."""
        driver = self.env.ref("ons_ops_intake.driver_boot_bsod")
        self.assertIsInstance(driver.interaction_count, int)

    def test_call_driver_action_exists(self):
        """The Call Drivers window action should be loadable."""
        action = self.env.ref(
            "ons_ops_intake.action_call_driver",
            raise_if_not_found=False,
        )
        self.assertTrue(action, "Call Drivers action not found")
        self.assertEqual(action.res_model, "ons.call.driver")


class TestInteraction(TransactionCase):
    """Tests for ons.interaction model."""

    def test_sequence_auto_generated(self):
        """New interactions should get an INT-… sequence reference."""
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "customer_phone": "5551234567",
        })
        self.assertTrue(rec.name.startswith("INT-"), f"Expected INT-… got {rec.name}")

    def test_state_transitions(self):
        """State transitions should follow new → classified → assigned → completed."""
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
        })
        self.assertEqual(rec.state, "new")

        rec.action_classify()
        self.assertEqual(rec.state, "classified")

        rec.action_assign()
        self.assertEqual(rec.state, "assigned")

        rec.action_complete()
        self.assertEqual(rec.state, "completed")

    def test_reset_to_new(self):
        """action_reset_to_new should revert any state to new."""
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
        })
        rec.action_classify()
        rec.action_reset_to_new()
        self.assertEqual(rec.state, "new")

    def test_duration_display(self):
        """duration_display should format seconds as Xm YYs."""
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "call_duration": 185,
        })
        self.assertEqual(rec.duration_display, "3m 05s")

    def test_resolve_customer_creates_partner(self):
        """action_resolve_customer should create a partner when none found."""
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "customer_phone": "9999990001",
            "customer_name": "Test Resolve",
        })
        self.assertFalse(rec.partner_id)
        rec.action_resolve_customer()
        self.assertTrue(rec.partner_id, "Partner should have been created")
        self.assertEqual(rec.partner_id.name, "Test Resolve")

    def test_resolve_customer_finds_existing(self):
        """action_resolve_customer should link existing partner by phone."""
        # Use a phone number unlikely to exist in the production DB
        unique_phone = "0009998871"
        partner = self.env["res.partner"].create({
            "name": "Existing Customer Resolve Test",
            "phone": unique_phone,
        })
        rec = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "customer_phone": unique_phone,
        })
        rec.action_resolve_customer()
        self.assertEqual(rec.partner_id, partner)

    def test_threecx_cdr_unique(self):
        """Duplicate threecx_cdr_id should be rejected."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "threecx_cdr_id": "CDR-UNIQUE-001",
        })
        with self.assertRaises(Exception):
            self.env["ons.interaction"].create({
                "interaction_type": "phone",
                "threecx_cdr_id": "CDR-UNIQUE-001",
            })

    def test_interaction_action_exists(self):
        """The Interactions window action should be loadable."""
        action = self.env.ref(
            "ons_ops_intake.action_interaction_list",
            raise_if_not_found=False,
        )
        self.assertTrue(action, "Interactions action not found")
        self.assertEqual(action.res_model, "ons.interaction")

    def test_menus_wired(self):
        """Interactions menu should be under Intake & CRM section."""
        menu = self.env.ref(
            "ons_ops_intake.menu_ops_interactions",
            raise_if_not_found=False,
        )
        self.assertTrue(menu, "Interactions menu not found")
        parent = self.env.ref("ons_ops_shell.menu_ops_intake_section")
        self.assertEqual(menu.parent_id, parent)


class TestPartnerExtensions(TransactionCase):
    """Tests for res.partner intake extensions."""

    def test_customer_segment_field(self):
        """customer_segment field should exist on res.partner."""
        partner = self.env["res.partner"].create({"name": "Segment Test"})
        partner.customer_segment = "subscriber"
        self.assertEqual(partner.customer_segment, "subscriber")

    def test_interaction_count_on_partner(self):
        """interaction_count should reflect linked interactions."""
        partner = self.env["res.partner"].create({"name": "Count Test"})
        self.assertEqual(partner.interaction_count, 0)
        self.env["ons.interaction"].create({
            "interaction_type": "email",
            "partner_id": partner.id,
        })
        partner.invalidate_recordset()
        self.assertEqual(partner.interaction_count, 1)


class TestCrmLeadExtension(TransactionCase):
    """Tests for crm.lead intake extension."""

    def test_interaction_id_field(self):
        """crm.lead should have an interaction_id field."""
        lead = self.env["crm.lead"].create({
            "name": "Test Lead",
        })
        self.assertFalse(lead.interaction_id)
