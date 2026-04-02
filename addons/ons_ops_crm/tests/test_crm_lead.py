# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestLeadCreationFromInteraction(TransactionCase):
    """Tests for interaction → lead conversion logic."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver_tech = cls.env["ons.call.driver"].create({
            "name": "Test Tech Driver",
            "code": "TST_CRM_TECH",
            "category": "boot_startup",
        })
        cls.driver_billing = cls.env["ons.call.driver"].create({
            "name": "Test Billing Driver",
            "code": "TST_CRM_BILL",
            "category": "billing",
        })
        cls.driver_upsell = cls.env["ons.call.driver"].create({
            "name": "Test Upsell Driver",
            "code": "TST_CRM_UPSELL",
            "category": "performance",
            "is_upsell_opportunity": True,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "CRM Test Customer",
            "phone": "5551112222",
            "customer_segment": "returning",
        })

    def _create_interaction(self, **kw):
        vals = {
            "interaction_type": "phone",
            "customer_phone": "5551112222",
            "state": "classified",
            "primary_driver_id": self.driver_tech.id,
            "session_path": "session_now",
            "partner_id": self.partner.id,
        }
        vals.update(kw)
        return self.env["ons.interaction"].create(vals)

    def test_service_lead_created_from_session_now(self):
        """session_now interaction should create a service_lead."""
        interaction = self._create_interaction(session_path="session_now")
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertTrue(lead)
        self.assertEqual(lead.lead_type, "service_lead")
        self.assertEqual(lead.interaction_id, interaction)
        self.assertEqual(lead.partner_id, self.partner)
        self.assertEqual(lead.primary_driver_id, self.driver_tech)
        self.assertEqual(interaction.lead_id, lead)

    def test_callback_request_created(self):
        """callback session_path should create callback_request lead."""
        interaction = self._create_interaction(session_path="callback")
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertEqual(lead.lead_type, "callback_request")
        self.assertTrue(lead.callback_requested)

    def test_billing_no_session_no_lead(self):
        """Billing driver with no_session should not create a lead."""
        interaction = self._create_interaction(
            session_path="no_session",
            primary_driver_id=self.driver_billing.id,
        )
        Lead = self.env["crm.lead"]
        with self.assertRaises(UserError):
            Lead.action_create_lead_from_interaction(interaction)

    def test_not_applicable_no_lead(self):
        """not_applicable session_path should not create a lead."""
        interaction = self._create_interaction(session_path="not_applicable")
        Lead = self.env["crm.lead"]
        with self.assertRaises(UserError):
            Lead.action_create_lead_from_interaction(interaction)

    def test_unclassified_interaction_rejected(self):
        """new state interaction should be rejected for lead creation."""
        interaction = self._create_interaction(state="new")
        Lead = self.env["crm.lead"]
        with self.assertRaises(UserError):
            Lead.action_create_lead_from_interaction(interaction)

    def test_duplicate_prevention_same_phone_same_driver(self):
        """Same phone + same driver should attach to existing lead, not create duplicate."""
        interaction1 = self._create_interaction(session_path="session_now")
        Lead = self.env["crm.lead"]
        lead1 = Lead.action_create_lead_from_interaction(interaction1)

        interaction2 = self._create_interaction(session_path="session_now")
        lead2 = Lead.action_create_lead_from_interaction(interaction2)

        self.assertEqual(lead1, lead2, "Should reuse the same lead")
        self.assertEqual(interaction2.lead_id, lead1)

    def test_different_driver_creates_new_lead(self):
        """Same phone + different driver should create a new lead."""
        interaction1 = self._create_interaction(
            session_path="session_now",
            primary_driver_id=self.driver_tech.id,
        )
        Lead = self.env["crm.lead"]
        lead1 = Lead.action_create_lead_from_interaction(interaction1)

        interaction2 = self._create_interaction(
            session_path="session_now",
            primary_driver_id=self.driver_upsell.id,
        )
        lead2 = Lead.action_create_lead_from_interaction(interaction2)
        self.assertNotEqual(lead1, lead2, "Different drivers should create different leads")

    def test_renewal_lead_for_returning_subscriber_upsell(self):
        """Returning subscriber with upsell driver at no_session → renewal lead."""
        self.partner.customer_segment = "subscriber"
        interaction = self._create_interaction(
            session_path="no_session",
            primary_driver_id=self.driver_upsell.id,
        )
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertEqual(lead.lead_type, "renewal")

    def test_caller_relationship_mapping(self):
        """caller_relationship should map from partner.customer_segment."""
        Lead = self.env["crm.lead"]

        self.partner.customer_segment = "new"
        self.assertEqual(Lead._get_caller_relationship(self.partner), "first_time_lead")

        self.partner.customer_segment = "returning"
        self.assertEqual(Lead._get_caller_relationship(self.partner), "returning_no_plan")

        self.partner.customer_segment = "subscriber"
        self.assertEqual(Lead._get_caller_relationship(self.partner), "active_subscriber")

        self.partner.customer_segment = "vip"
        self.assertEqual(Lead._get_caller_relationship(self.partner), "active_subscriber")

        # No partner
        self.assertEqual(Lead._get_caller_relationship(self.env["res.partner"]), "first_time_lead")

    def test_scheduled_session_creates_service_lead(self):
        """session_scheduled should create service_lead."""
        interaction = self._create_interaction(session_path="session_scheduled")
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertEqual(lead.lead_type, "service_lead")

    def test_onsite_queue_creates_service_lead(self):
        """onsite_queue session_path should create service_lead."""
        interaction = self._create_interaction(session_path="onsite_queue")
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertEqual(lead.lead_type, "service_lead")


class TestLeadActions(TransactionCase):
    """Tests for lead business actions: promote, decline."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Lead Action Test",
            "phone": "5553334444",
        })

    def _create_lead(self, **kw):
        vals = {
            "name": "Test Lead",
            "type": "lead",
            "partner_id": self.partner.id,
            "phone": "5553334444",
        }
        vals.update(kw)
        return self.env["crm.lead"].create(vals)

    def test_promote_to_nurture(self):
        """action_promote_to_nurture should set lead_type to nurture."""
        lead = self._create_lead(lead_type="inquiry")
        lead.action_promote_to_nurture()
        self.assertEqual(lead.lead_type, "nurture")

    def test_promote_nurture_requires_contact(self):
        """Nurture promotion should fail without phone or email."""
        lead = self._create_lead(phone=False, email_from=False)
        with self.assertRaises(UserError):
            lead.action_promote_to_nurture()

    def test_mark_declined(self):
        """action_mark_declined should set decline_date."""
        lead = self._create_lead()
        self.assertFalse(lead.decline_date)
        lead.action_mark_declined()
        self.assertTrue(lead.decline_date)

    def test_is_convertible_computed(self):
        """is_convertible should be True when all conditions met."""
        driver = self.env["ons.call.driver"].create({
            "name": "Conv Test", "code": "TST_CONV", "category": "meta",
        })
        interaction = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "customer_phone": "5553334444",
            "state": "classified",
            "primary_driver_id": driver.id,
            "session_path": "session_now",
            "partner_id": self.partner.id,
        })
        lead = self._create_lead(interaction_id=interaction.id)
        self.assertTrue(lead.is_convertible)

    def test_is_convertible_false_without_partner(self):
        """is_convertible should be False without partner."""
        driver = self.env["ons.call.driver"].create({
            "name": "Conv Test NP", "code": "TST_CONV_NP", "category": "meta",
        })
        interaction = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "customer_phone": "5553334444",
            "state": "classified",
            "primary_driver_id": driver.id,
            "session_path": "session_now",
        })
        lead = self._create_lead(partner_id=False, interaction_id=interaction.id)
        self.assertFalse(lead.is_convertible)

    def test_lead_type_field_values(self):
        """lead_type selection should accept all defined values."""
        for lt in ("inquiry", "callback_request", "service_lead", "nurture", "renewal"):
            lead = self._create_lead(lead_type=lt)
            self.assertEqual(lead.lead_type, lt)


class TestLostReasons(TransactionCase):
    """Tests for custom lost reason seed data."""

    def test_custom_lost_reasons_loaded(self):
        """All 7 custom lost reasons should be loaded."""
        xmlids = [
            "ons_ops_crm.lost_reason_customer_declined",
            "ons_ops_crm.lost_reason_too_expensive",
            "ons_ops_crm.lost_reason_competitor",
            "ons_ops_crm.lost_reason_self_resolved",
            "ons_ops_crm.lost_reason_no_response",
            "ons_ops_crm.lost_reason_not_serviceable",
            "ons_ops_crm.lost_reason_duplicate",
        ]
        for xmlid in xmlids:
            reason = self.env.ref(xmlid, raise_if_not_found=False)
            self.assertTrue(reason, f"Lost reason {xmlid} not found")


class TestCrmViews(TransactionCase):
    """Tests for CRM views and menus."""

    def test_pipeline_action_exists(self):
        """The ops pipeline action should be loadable."""
        action = self.env.ref(
            "ons_ops_crm.action_ops_pipeline",
            raise_if_not_found=False,
        )
        self.assertTrue(action, "Pipeline action not found")
        self.assertEqual(action.res_model, "crm.lead")

    def test_consent_action_exists(self):
        """The consent list action should be loadable."""
        action = self.env.ref(
            "ons_ops_crm.action_consent_list",
            raise_if_not_found=False,
        )
        self.assertTrue(action, "Consent action not found")
        self.assertEqual(action.res_model, "ons.contact.consent")
