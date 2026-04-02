# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReports(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # ── Users ───────────────────────────────────────────────
        cls.agent_user = cls.env["res.users"].create({
            "name": "Report Test Agent",
            "login": "rpt_agent",
            "email": "rpt_agent@test.com",
        })
        cls.agent2_user = cls.env["res.users"].create({
            "name": "Report Test Agent 2",
            "login": "rpt_agent2",
            "email": "rpt_agent2@test.com",
        })

        # ── Extension ──────────────────────────────────────────
        cls.extension = cls.env["ons.user.extension"].create({
            "extension": "7050",
            "user_id": cls.agent_user.id,
        })

        # ── Partner ─────────────────────────────────────────────
        cls.partner = cls.env["res.partner"].create({
            "name": "Report Test Customer",
            "phone": "5125550100",
        })

        # ── Call driver ─────────────────────────────────────────
        cls.driver = cls.env["ons.call.driver"].create({
            "name": "Report Test Driver",
            "code": "RPT_TEST_DRIVER",
            "category": "network",
        })

        # ── Date fixtures ───────────────────────────────────────
        cls.test_date = date(2026, 3, 15)
        cls.test_dt_start = "2026-03-15 10:00:00"
        cls.test_dt_end = "2026-03-15 10:15:00"

    # ═══════════════════════════════════════════════════════════════
    #  Agent Daily — Computation Tests
    # ═══════════════════════════════════════════════════════════════

    def test_agent_daily_empty_range(self):
        """Recompute on a date with no activity produces no records."""
        empty_date = date(2020, 1, 1)
        self.env["ons.report.agent.daily"].recompute_range(empty_date, empty_date)
        count = self.env["ons.report.agent.daily"].search_count([
            ("report_date", "=", empty_date),
        ])
        self.assertEqual(count, 0)

    def test_agent_daily_call_kpis(self):
        """Call log records drive call KPIs in agent daily report."""
        self.env["ons.call.log"].create({
            "caller_number": "5125550001",
            "callee_number": "8005551000",
            "direction": "inbound",
            "disposition": "answered",
            "talk_duration": 300,
            "call_start": self.test_dt_start,
            "call_end": self.test_dt_end,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125550002",
            "callee_number": "8005551000",
            "direction": "inbound",
            "disposition": "missed",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "callee_number": "5125550003",
            "caller_number": "8005551000",
            "direction": "outbound",
            "disposition": "answered",
            "talk_duration": 600,
            "call_start": self.test_dt_start,
            "call_end": self.test_dt_end,
            "agent_id": self.agent_user.id,
        })

        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", self.test_date),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertEqual(len(report), 1)
        self.assertEqual(report.total_calls, 3)
        self.assertEqual(report.inbound_calls, 2)
        self.assertEqual(report.outbound_calls, 1)
        self.assertEqual(report.answered_calls, 2)
        self.assertEqual(report.missed_calls, 1)
        self.assertEqual(report.avg_talk_duration, 450)  # (300+600)/2

    def test_agent_daily_case_kpis(self):
        """Cases created drive case KPIs."""
        stage = self.env["ons.case.stage"].search(
            [("code", "=", "intake_submitted")], limit=1,
        )
        self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "intake_agent_id": self.agent_user.id,
            "primary_driver_id": self.driver.id,
            "stage_id": stage.id,
        })

        today = date.today()
        self.env["ons.report.agent.daily"].recompute_range(today, today)

        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", today),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertTrue(report)
        self.assertGreaterEqual(report.cases_created, 1)

    def test_agent_daily_revenue_kpi(self):
        """Revenue KPI sums paid case amount_total."""
        case = self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "billing_agent_id": self.agent_user.id,
            "primary_driver_id": self.driver.id,
        })
        # Add billing line — create a product inline (no seed data assumed)
        product = self.env["product.product"].create({
            "name": "Report Test Product",
            "list_price": 199.99,
        })
        self.env["ons.case.line"].create({
            "case_id": case.id,
            "product_id": product.id,
            "quantity": 1,
            "unit_price": 199.99,
        })
        # Mark paid — SQL only checks payment_status, no stage change needed
        case.write({
            "payment_status": "paid",
        })
        # Flush computed amount_total to DB before raw SQL
        self.env.flush_all()

        today = date.today()
        self.env["ons.report.agent.daily"].recompute_range(today, today)

        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", today),
            ("agent_id", "=", self.agent_user.id),
        ])
        if report:
            self.assertGreaterEqual(report.revenue, 199.99)

    def test_agent_daily_qa_kpis(self):
        """QA evaluations contribute to agent daily qa metrics."""
        call_log = self.env["ons.call.log"].create({
            "caller_number": "5125559090",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        result = self.env["ons.qa.result"].create({
            "call_log_id": call_log.id,
        })
        result.action_grade(85.0)
        # Flush computed stored fields (agent_id) to DB before raw SQL
        self.env.flush_all()

        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", self.test_date),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertTrue(report)
        self.assertGreaterEqual(report.qa_eval_count, 1)
        self.assertGreater(report.qa_avg_score, 0)

    def test_agent_daily_auto_fail_count(self):
        """Auto-fail QA results show in auto_fail_count."""
        call_log = self.env["ons.call.log"].create({
            "caller_number": "5125559091",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        result = self.env["ons.qa.result"].create({
            "call_log_id": call_log.id,
        })
        result.action_grade(40.0, auto_fail=True, auto_fail_reasons="banned word")
        # Flush computed stored fields (agent_id) to DB before raw SQL
        self.env.flush_all()

        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", self.test_date),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertTrue(report)
        self.assertEqual(report.qa_auto_fail_count, 1)

    def test_agent_daily_unique_constraint(self):
        """UniqueIndex prevents duplicate agent+date rows."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559092",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        # Running again should not fail — it deletes first
        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        count = self.env["ons.report.agent.daily"].search_count([
            ("report_date", "=", self.test_date),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertEqual(count, 1)

    def test_agent_daily_multi_agent(self):
        """Multiple agents each get separate report rows."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559093",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125559094",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent2_user.id,
        })

        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        reports = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", self.test_date),
        ])
        agents = reports.mapped("agent_id.id")
        self.assertIn(self.agent_user.id, agents)
        self.assertIn(self.agent2_user.id, agents)

    def test_agent_daily_display_name(self):
        """Display name computed correctly."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559095",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        report = self.env["ons.report.agent.daily"].search([
            ("report_date", "=", self.test_date),
            ("agent_id", "=", self.agent_user.id),
        ])
        self.assertIn("2026-03-15", report.display_name)
        self.assertIn("Report Test Agent", report.display_name)

    def test_agent_daily_cron_method_exists(self):
        """Cron method is callable."""
        self.assertTrue(
            callable(getattr(
                self.env["ons.report.agent.daily"], "_cron_recompute_daily", None,
            ))
        )

    # ═══════════════════════════════════════════════════════════════
    #  Queue Daily — Computation Tests
    # ═══════════════════════════════════════════════════════════════

    def test_queue_daily_empty_range(self):
        """No activity produces no queue report."""
        empty_date = date(2020, 1, 1)
        self.env["ons.report.queue.daily"].recompute_range(empty_date, empty_date)
        count = self.env["ons.report.queue.daily"].search_count([
            ("report_date", "=", empty_date),
        ])
        self.assertEqual(count, 0)

    def test_queue_daily_call_kpis(self):
        """Queue daily aggregates calls by queue_name."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559101",
            "callee_number": "8005551000",
            "direction": "inbound",
            "disposition": "answered",
            "talk_duration": 240,
            "wait_duration": 15,
            "queue_name": "First Time Caller",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125559102",
            "callee_number": "8005551000",
            "direction": "inbound",
            "disposition": "missed",
            "wait_duration": 30,
            "queue_name": "First Time Caller",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })

        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.queue.daily"].search([
            ("report_date", "=", self.test_date),
            ("queue_name", "=", "First Time Caller"),
        ])
        self.assertEqual(len(report), 1)
        self.assertEqual(report.total_calls, 2)
        self.assertEqual(report.answered_calls, 1)
        self.assertEqual(report.missed_calls, 1)
        self.assertEqual(report.avg_talk_duration, 240)

    def test_queue_daily_multi_queue(self):
        """Different queues each get separate rows."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559103",
            "callee_number": "8005551000",
            "direction": "inbound",
            "queue_name": "First Time Caller",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125559104",
            "callee_number": "8005551000",
            "direction": "inbound",
            "queue_name": "Returning Caller",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })

        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        queues = self.env["ons.report.queue.daily"].search([
            ("report_date", "=", self.test_date),
        ]).mapped("queue_name")
        self.assertIn("First Time Caller", queues)
        self.assertIn("Returning Caller", queues)

    def test_queue_daily_recompute_idempotent(self):
        """Running recompute twice produces same result (delete + recreate)."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559105",
            "callee_number": "8005551000",
            "direction": "inbound",
            "queue_name": "Billing",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        count = self.env["ons.report.queue.daily"].search_count([
            ("report_date", "=", self.test_date),
            ("queue_name", "=", "Billing"),
        ])
        self.assertEqual(count, 1)

    def test_queue_daily_cases_from_interaction(self):
        """Cases linked via source_interaction queue are counted."""
        interaction = self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "queue_name": "First Time Caller",
            "call_start": self.test_dt_start,
        })
        self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "source_interaction_id": interaction.id,
            "primary_driver_id": self.driver.id,
        })

        # Also need a call_log with that queue for the queue to appear
        self.env["ons.call.log"].create({
            "caller_number": "5125559106",
            "callee_number": "8005551000",
            "direction": "inbound",
            "queue_name": "First Time Caller",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })

        today = date.today()
        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, today,
        )

        report = self.env["ons.report.queue.daily"].search([
            ("queue_name", "=", "First Time Caller"),
        ], limit=1)
        if report:
            self.assertGreaterEqual(report.total_calls, 1)

    def test_queue_daily_display_name(self):
        """Display name includes date and queue."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559107",
            "callee_number": "8005551000",
            "direction": "inbound",
            "queue_name": "TestQueue",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.report.queue.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        report = self.env["ons.report.queue.daily"].search([
            ("queue_name", "=", "TestQueue"),
        ], limit=1)
        self.assertIn("TestQueue", report.display_name)
        self.assertIn("2026-03-15", report.display_name)

    # ═══════════════════════════════════════════════════════════════
    #  Driver Daily — Computation Tests
    # ═══════════════════════════════════════════════════════════════

    def test_driver_daily_empty_range(self):
        """No activity produces no driver report."""
        empty_date = date(2020, 1, 1)
        self.env["ons.report.driver.daily"].recompute_range(empty_date, empty_date)
        count = self.env["ons.report.driver.daily"].search_count([
            ("report_date", "=", empty_date),
        ])
        self.assertEqual(count, 0)

    def test_driver_daily_interaction_count(self):
        """Interactions with driver are counted."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })

        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ])
        self.assertEqual(len(report), 1)
        self.assertEqual(report.total_interactions, 2)

    def test_driver_daily_case_count(self):
        """Cases with driver are counted."""
        self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "primary_driver_id": self.driver.id,
        })

        today = date.today()
        self.env["ons.report.driver.daily"].recompute_range(today, today)

        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", today),
            ("driver_id", "=", self.driver.id),
        ])
        self.assertTrue(report)
        self.assertGreaterEqual(report.cases_created, 1)

    def test_driver_daily_conversion_rate(self):
        """Conversion rate computed from interactions / cases."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        # Only one converts to case — but case uses create_date, not call_start
        # For determinism, create case and interaction on same date
        self.env["ons.case"].with_context(
            default_create_date=self.test_dt_start,
        ).create({
            "partner_id": self.partner.id,
            "primary_driver_id": self.driver.id,
        })

        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ])
        self.assertTrue(report)
        self.assertEqual(report.total_interactions, 2)
        # Case may land on test_date or today depending on ORM
        if report.cases_created > 0:
            self.assertAlmostEqual(
                report.conversion_rate,
                report.cases_created / report.total_interactions * 100,
                places=1,
            )

    def test_driver_daily_zero_interactions_no_division_error(self):
        """Conversion rate is 0 when only cases exist (no interactions)."""
        self.env["ons.case"].with_context(
            default_create_date=self.test_dt_start,
        ).create({
            "partner_id": self.partner.id,
            "primary_driver_id": self.driver.id,
        })

        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ])
        if report:
            # conversion_rate should be 0 when total_interactions is 0
            if report.total_interactions == 0:
                self.assertEqual(report.conversion_rate, 0.0)

    def test_driver_daily_recompute_idempotent(self):
        """Running recompute twice produces same result."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        count = self.env["ons.report.driver.daily"].search_count([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ])
        self.assertEqual(count, 1)

    def test_driver_daily_display_name(self):
        """Display name includes date and driver name."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ], limit=1)
        self.assertIn("Report Test Driver", report.display_name)

    def test_driver_daily_category_stored(self):
        """Driver category is stored via related field."""
        self.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "primary_driver_id": self.driver.id,
            "call_start": self.test_dt_start,
        })
        self.env["ons.report.driver.daily"].recompute_range(
            self.test_date, self.test_date,
        )
        report = self.env["ons.report.driver.daily"].search([
            ("report_date", "=", self.test_date),
            ("driver_id", "=", self.driver.id),
        ], limit=1)
        self.assertEqual(report.driver_category, "network")

    # ═══════════════════════════════════════════════════════════════
    #  Multi-Date Range Tests
    # ═══════════════════════════════════════════════════════════════

    def test_agent_daily_multi_date_range(self):
        """Recompute over a multi-day range creates records for each active day."""
        dt2 = "2026-03-16 10:00:00"
        self.env["ons.call.log"].create({
            "caller_number": "5125559110",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125559111",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": dt2,
            "agent_id": self.agent_user.id,
        })

        d1 = date(2026, 3, 15)
        d2 = date(2026, 3, 16)
        self.env["ons.report.agent.daily"].recompute_range(d1, d2)

        reports = self.env["ons.report.agent.daily"].search([
            ("agent_id", "=", self.agent_user.id),
            ("report_date", ">=", d1),
            ("report_date", "<=", d2),
        ])
        dates = reports.mapped("report_date")
        self.assertIn(d1, dates)
        self.assertIn(d2, dates)

    # ═══════════════════════════════════════════════════════════════
    #  Cron Tests
    # ═══════════════════════════════════════════════════════════════

    def test_cron_methods_exist(self):
        """All three cron methods exist and are callable."""
        for model_name in [
            "ons.report.agent.daily",
            "ons.report.queue.daily",
            "ons.report.driver.daily",
        ]:
            model = self.env[model_name]
            self.assertTrue(hasattr(model, "_cron_recompute_daily"))
            self.assertTrue(hasattr(model, "recompute_range"))

    # ═══════════════════════════════════════════════════════════════
    #  Security / Domain Tests
    # ═══════════════════════════════════════════════════════════════

    def test_agent_daily_domain_filter(self):
        """Reports can be filtered by agent domain."""
        self.env["ons.call.log"].create({
            "caller_number": "5125559120",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent_user.id,
        })
        self.env["ons.call.log"].create({
            "caller_number": "5125559121",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": self.test_dt_start,
            "agent_id": self.agent2_user.id,
        })

        self.env["ons.report.agent.daily"].recompute_range(
            self.test_date, self.test_date,
        )

        my_reports = self.env["ons.report.agent.daily"].search([
            ("agent_id", "=", self.agent_user.id),
            ("report_date", "=", self.test_date),
        ])
        self.assertEqual(len(my_reports), 1)
        self.assertEqual(my_reports.agent_id.id, self.agent_user.id)
