# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPortalSecurity(TransactionCase):
    """Record rules and access control for portal users."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ── Partners ────────────────────────────────────────────
        cls.partner_a = cls.env["res.partner"].create({
            "name": "Portal Customer A",
            "email": "a@example.com",
            "phone": "5550001111",
            "customer_segment": "new",
        })
        cls.partner_b = cls.env["res.partner"].create({
            "name": "Portal Customer B",
            "email": "b@example.com",
            "phone": "5550002222",
            "customer_segment": "new",
        })

        # ── Portal users ────────────────────────────────────────
        portal_group = cls.env.ref("base.group_portal")
        cls.portal_user_a = cls.env["res.users"].with_context(
            no_reset_password=True,
        ).create({
            "name": "Portal A",
            "login": "portal_a_test",
            "email": "a@example.com",
            "password": "portal_a_test",
            "partner_id": cls.partner_a.id,
            "group_ids": [(6, 0, [portal_group.id])],
        })
        cls.portal_user_b = cls.env["res.users"].with_context(
            no_reset_password=True,
        ).create({
            "name": "Portal B",
            "login": "portal_b_test",
            "email": "b@example.com",
            "password": "portal_b_test",
            "partner_id": cls.partner_b.id,
            "group_ids": [(6, 0, [portal_group.id])],
        })

        # ── Shared test data (as admin) ─────────────────────────
        cls.driver = cls.env["ons.call.driver"].create({
            "name": "Portal Test Driver",
            "code": "PTL_DRV",
            "category": "boot_startup",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Portal Test Plan Product",
            "list_price": 99.00,
        })

        # Cases
        cls.case_a = cls.env["ons.case"].create({
            "partner_id": cls.partner_a.id,
            "primary_driver_id": cls.driver.id,
            "issue_description": "A's issue",
        })
        cls.case_b = cls.env["ons.case"].create({
            "partner_id": cls.partner_b.id,
            "primary_driver_id": cls.driver.id,
            "issue_description": "B's issue",
        })

        # Plans
        cls.plan_a = cls.env["ons.customer.plan"].create({
            "partner_id": cls.partner_a.id,
            "product_id": cls.product.id,
            "amount": 99.00,
            "start_date": "2025-01-01",
        })
        cls.plan_b = cls.env["ons.customer.plan"].create({
            "partner_id": cls.partner_b.id,
            "product_id": cls.product.id,
            "amount": 149.00,
            "start_date": "2025-01-01",
        })

        # Dispatch statuses
        cls.dispatch_status = cls.env["ons.dispatch.status"].search([], limit=1)
        if not cls.dispatch_status:
            cls.dispatch_status = cls.env["ons.dispatch.status"].create({
                "name": "Scheduled",
                "code": "scheduled",
            })

        # Dispatches
        cls.dispatch_a = cls.env["ons.dispatch"].create({
            "partner_id": cls.partner_a.id,
            "case_id": cls.case_a.id,
            "status_id": cls.dispatch_status.id,
            "title": "A dispatch",
        })
        cls.dispatch_b = cls.env["ons.dispatch"].create({
            "partner_id": cls.partner_b.id,
            "case_id": cls.case_b.id,
            "status_id": cls.dispatch_status.id,
            "title": "B dispatch",
        })

        # Consent
        cls.consent_a = cls.env["ons.contact.consent"].create({
            "partner_id": cls.partner_a.id,
            "channel": "email",
            "scope": "marketing",
            "status": "pending",
            "capture_source": "manual",
        })
        cls.consent_b = cls.env["ons.contact.consent"].create({
            "partner_id": cls.partner_b.id,
            "channel": "sms",
            "scope": "operational",
            "status": "pending",
            "capture_source": "manual",
        })

    # ═══════════════════════════════════════════════════════════════
    #  portal.mixin — access_url
    # ═══════════════════════════════════════════════════════════════

    def test_case_access_url(self):
        self.assertEqual(
            self.case_a.access_url,
            "/my/cases/%s" % self.case_a.id,
        )

    def test_plan_access_url(self):
        self.assertEqual(
            self.plan_a.access_url,
            "/my/plans/%s" % self.plan_a.id,
        )

    def test_dispatch_access_url(self):
        self.assertEqual(
            self.dispatch_a.access_url,
            "/my/dispatches/%s" % self.dispatch_a.id,
        )

    # ═══════════════════════════════════════════════════════════════
    #  Record rules — cases
    # ═══════════════════════════════════════════════════════════════

    def test_portal_user_a_reads_own_case(self):
        case = self.env["ons.case"].with_user(self.portal_user_a).browse(self.case_a.id)
        case.read(["name"])  # should not raise

    def test_portal_user_a_cannot_read_b_case(self):
        case = self.env["ons.case"].with_user(self.portal_user_a).browse(self.case_b.id)
        with self.assertRaises(AccessError):
            case.read(["name"])

    def test_portal_user_cannot_write_case(self):
        case = self.env["ons.case"].with_user(self.portal_user_a).browse(self.case_a.id)
        with self.assertRaises(AccessError):
            case.write({"issue_description": "hacked"})

    def test_portal_user_cannot_create_case(self):
        with self.assertRaises(AccessError):
            self.env["ons.case"].with_user(self.portal_user_a).create({
                "partner_id": self.partner_a.id,
                "primary_driver_id": self.driver.id,
            })

    # ═══════════════════════════════════════════════════════════════
    #  Record rules — plans
    # ═══════════════════════════════════════════════════════════════

    def test_portal_user_a_reads_own_plan(self):
        plan = self.env["ons.customer.plan"].with_user(self.portal_user_a).browse(self.plan_a.id)
        plan.read(["amount"])

    def test_portal_user_a_cannot_read_b_plan(self):
        plan = self.env["ons.customer.plan"].with_user(self.portal_user_a).browse(self.plan_b.id)
        with self.assertRaises(AccessError):
            plan.read(["amount"])

    def test_portal_user_cannot_write_plan(self):
        plan = self.env["ons.customer.plan"].with_user(self.portal_user_a).browse(self.plan_a.id)
        with self.assertRaises(AccessError):
            plan.write({"amount": 0.01})

    # ═══════════════════════════════════════════════════════════════
    #  Record rules — dispatches
    # ═══════════════════════════════════════════════════════════════

    def test_portal_user_a_reads_own_dispatch(self):
        disp = self.env["ons.dispatch"].with_user(self.portal_user_a).browse(self.dispatch_a.id)
        disp.read(["title"])

    def test_portal_user_a_cannot_read_b_dispatch(self):
        disp = self.env["ons.dispatch"].with_user(self.portal_user_a).browse(self.dispatch_b.id)
        with self.assertRaises(AccessError):
            disp.read(["title"])

    def test_portal_user_cannot_write_dispatch(self):
        disp = self.env["ons.dispatch"].with_user(self.portal_user_a).browse(self.dispatch_a.id)
        with self.assertRaises(AccessError):
            disp.write({"title": "hacked"})

    # ═══════════════════════════════════════════════════════════════
    #  Record rules — consent
    # ═══════════════════════════════════════════════════════════════

    def test_portal_user_a_reads_own_consent(self):
        cons = self.env["ons.contact.consent"].with_user(self.portal_user_a).browse(self.consent_a.id)
        cons.read(["status"])

    def test_portal_user_a_cannot_read_b_consent(self):
        cons = self.env["ons.contact.consent"].with_user(self.portal_user_a).browse(self.consent_b.id)
        with self.assertRaises(AccessError):
            cons.read(["status"])

    # ═══════════════════════════════════════════════════════════════
    #  Search boundary — no data leakage
    # ═══════════════════════════════════════════════════════════════

    def test_portal_search_cases_isolation(self):
        """Portal user A searching cases should only find A's cases."""
        cases = self.env["ons.case"].with_user(self.portal_user_a).search([])
        partner_ids = cases.mapped("partner_id.id")
        self.assertIn(self.partner_a.id, partner_ids)
        self.assertNotIn(self.partner_b.id, partner_ids)

    def test_portal_search_plans_isolation(self):
        plans = self.env["ons.customer.plan"].with_user(self.portal_user_a).search([])
        partner_ids = plans.mapped("partner_id.id")
        self.assertIn(self.partner_a.id, partner_ids)
        self.assertNotIn(self.partner_b.id, partner_ids)

    def test_portal_search_dispatches_isolation(self):
        dispatches = self.env["ons.dispatch"].with_user(self.portal_user_a).search([])
        partner_ids = dispatches.mapped("partner_id.id")
        self.assertIn(self.partner_a.id, partner_ids)
        self.assertNotIn(self.partner_b.id, partner_ids)

    def test_portal_search_consent_isolation(self):
        consents = self.env["ons.contact.consent"].with_user(self.portal_user_a).search([])
        partner_ids = consents.mapped("partner_id.id")
        self.assertIn(self.partner_a.id, partner_ids)
        self.assertNotIn(self.partner_b.id, partner_ids)

    # ═══════════════════════════════════════════════════════════════
    #  Consent toggle (sudo path)
    # ═══════════════════════════════════════════════════════════════

    def test_consent_opt_in_from_pending(self):
        """action_opt_in changes pending → opted_in."""
        self.assertEqual(self.consent_a.status, "pending")
        self.consent_a.action_opt_in()
        self.assertEqual(self.consent_a.status, "opted_in")

    def test_consent_opt_out(self):
        """action_opt_out changes opted_in → opted_out."""
        self.consent_b.action_opt_in()  # ensure opted_in
        self.consent_b.action_opt_out()
        self.assertEqual(self.consent_b.status, "opted_out")

    def test_consent_opt_in_after_opt_out_not_allowed(self):
        """Re-opt-in after opt-out requires a new consent record."""
        self.consent_a.action_opt_in()
        self.consent_a.action_opt_out()
        self.assertEqual(self.consent_a.status, "opted_out")
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self.consent_a.action_opt_in()

    # ═══════════════════════════════════════════════════════════════
    #  Case line visibility (indirect via case partner)
    # ═══════════════════════════════════════════════════════════════

    def test_portal_user_reads_own_case_lines(self):
        """Portal user can read case lines belonging to their case."""
        product = self.env["product.product"].create({
            "name": "Line Test Product",
            "list_price": 50.0,
        })
        line = self.env["ons.case.line"].create({
            "case_id": self.case_a.id,
            "product_id": product.id,
            "quantity": 1,
            "unit_price": 50.0,
        })
        line_portal = self.env["ons.case.line"].with_user(self.portal_user_a).browse(line.id)
        line_portal.read(["quantity"])  # should not raise

    def test_portal_user_cannot_read_other_case_lines(self):
        """Portal user cannot read case lines from another customer."""
        product = self.env["product.product"].create({
            "name": "Other Line Product",
            "list_price": 75.0,
        })
        line = self.env["ons.case.line"].create({
            "case_id": self.case_b.id,
            "product_id": product.id,
            "quantity": 2,
            "unit_price": 75.0,
        })
        line_portal = self.env["ons.case.line"].with_user(self.portal_user_a).browse(line.id)
        with self.assertRaises(AccessError):
            line_portal.read(["quantity"])
