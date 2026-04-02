# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class ReportAgentDaily(models.Model):
    _name = "ons.report.agent.daily"
    _description = "Agent Daily Performance Report"
    _order = "report_date desc, agent_id"
    _rec_name = "display_name"

    _date_agent_unique = models.UniqueIndex(
        "(report_date, agent_id)",
        "Only one report row per agent per day.",
    )

    # ── Dimensions ──────────────────────────────────────────────
    report_date = fields.Date(required=True, index=True)
    agent_id = fields.Many2one(
        "res.users", string="Agent", required=True, index=True, ondelete="cascade",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ── Call KPIs ───────────────────────────────────────────────
    total_calls = fields.Integer(string="Total Calls")
    inbound_calls = fields.Integer(string="Inbound")
    outbound_calls = fields.Integer(string="Outbound")
    answered_calls = fields.Integer(string="Answered")
    missed_calls = fields.Integer(string="Missed")
    avg_talk_duration = fields.Integer(string="Avg Talk (s)")

    # ── Case KPIs ───────────────────────────────────────────────
    cases_created = fields.Integer(string="Cases Created")
    cases_won = fields.Integer(string="Cases Won")

    # ── Revenue KPIs ────────────────────────────────────────────
    revenue = fields.Float(string="Revenue", digits=(12, 2))

    # ── QA KPIs ─────────────────────────────────────────────────
    qa_eval_count = fields.Integer(string="QA Evaluations")
    qa_auto_fail_count = fields.Integer(string="QA Auto-Fails")
    qa_avg_score = fields.Float(string="QA Avg Score", digits=(5, 2))

    # ── Dispatch KPI ────────────────────────────────────────────
    dispatch_count = fields.Integer(string="Dispatches")

    # ── AI KPI ──────────────────────────────────────────────────
    ai_cost = fields.Float(string="AI Cost", digits=(10, 4))

    @api.depends("agent_id", "report_date")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.report_date:
                parts.append(str(rec.report_date))
            if rec.agent_id:
                parts.append(rec.agent_id.name or "")
            rec.display_name = " — ".join(parts) if parts else "Report"

    # ── Computation Engine ──────────────────────────────────────

    @api.model
    def _cron_recompute_daily(self):
        """Scheduled daily recompute for yesterday."""
        yesterday = fields.Date.context_today(self) - timedelta(days=1)
        self.recompute_range(yesterday, yesterday)

    @api.model
    def recompute_range(self, date_from, date_to):
        """Recompute agent daily reports for a date range."""
        _logger.info("Recomputing agent daily reports: %s → %s", date_from, date_to)

        # Delete existing records in range
        existing = self.search([
            ("report_date", ">=", date_from),
            ("report_date", "<=", date_to),
        ])
        if existing:
            existing.unlink()

        # Collect all agents that had any activity in the range
        agent_dates = self._collect_agent_dates(date_from, date_to)

        vals_list = []
        for (agent_id, report_date) in agent_dates:
            vals = self._compute_agent_day(agent_id, report_date)
            vals_list.append(vals)

        if vals_list:
            self.create(vals_list)
            _logger.info("Created %d agent daily reports", len(vals_list))

    @api.model
    def _collect_agent_dates(self, date_from, date_to):
        """Return set of (agent_id, date) tuples with any activity."""
        result = set()
        cr = self.env.cr

        # From call logs
        cr.execute("""
            SELECT DISTINCT agent_id, call_start::date
            FROM ons_call_log
            WHERE agent_id IS NOT NULL
              AND call_start::date >= %s AND call_start::date <= %s
        """, (date_from, date_to))
        for row in cr.fetchall():
            result.add((row[0], row[1]))

        # From cases (intake agent)
        cr.execute("""
            SELECT DISTINCT intake_agent_id, create_date::date
            FROM ons_case
            WHERE intake_agent_id IS NOT NULL
              AND create_date::date >= %s AND create_date::date <= %s
        """, (date_from, date_to))
        for row in cr.fetchall():
            result.add((row[0], row[1]))

        # From cases won (billing agent)
        cr.execute("""
            SELECT DISTINCT billing_agent_id, write_date::date
            FROM ons_case
            WHERE billing_agent_id IS NOT NULL
              AND is_won = TRUE
              AND payment_status = 'paid'
              AND write_date::date >= %s AND write_date::date <= %s
        """, (date_from, date_to))
        for row in cr.fetchall():
            result.add((row[0], row[1]))

        # From QA results (attribute to call date, not grading date)
        cr.execute("""
            SELECT DISTINCT r.agent_id, cl.call_start::date
            FROM ons_qa_result r
            JOIN ons_call_log cl ON cl.id = r.call_log_id
            WHERE r.agent_id IS NOT NULL
              AND r.state != 'draft'
              AND cl.call_start::date >= %s AND cl.call_start::date <= %s
        """, (date_from, date_to))
        for row in cr.fetchall():
            result.add((row[0], row[1]))

        return result

    @api.model
    def _compute_agent_day(self, agent_id, report_date):
        """Compute all KPIs for one agent on one day."""
        cr = self.env.cr
        vals = {
            "report_date": report_date,
            "agent_id": agent_id,
        }

        # ── Call KPIs ───────────────────────────────────────────
        cr.execute("""
            SELECT
                COUNT(*) AS total_calls,
                COUNT(*) FILTER (WHERE direction = 'inbound') AS inbound_calls,
                COUNT(*) FILTER (WHERE direction = 'outbound') AS outbound_calls,
                COUNT(*) FILTER (WHERE disposition = 'answered') AS answered_calls,
                COUNT(*) FILTER (WHERE disposition = 'missed') AS missed_calls,
                COALESCE(AVG(talk_duration) FILTER (WHERE disposition = 'answered'), 0)::int AS avg_talk
            FROM ons_call_log
            WHERE agent_id = %s AND call_start::date = %s
        """, (agent_id, report_date))
        row = cr.fetchone()
        vals["total_calls"] = row[0]
        vals["inbound_calls"] = row[1]
        vals["outbound_calls"] = row[2]
        vals["answered_calls"] = row[3]
        vals["missed_calls"] = row[4]
        vals["avg_talk_duration"] = row[5]

        # ── Case KPIs ──────────────────────────────────────────
        cr.execute("""
            SELECT COUNT(*)
            FROM ons_case
            WHERE intake_agent_id = %s AND create_date::date = %s
        """, (agent_id, report_date))
        vals["cases_created"] = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*)
            FROM ons_case
            WHERE intake_agent_id = %s AND is_won = TRUE AND write_date::date = %s
        """, (agent_id, report_date))
        vals["cases_won"] = cr.fetchone()[0]

        # ── Revenue ─────────────────────────────────────────────
        cr.execute("""
            SELECT COALESCE(SUM(amount_total), 0)
            FROM ons_case
            WHERE billing_agent_id = %s
              AND payment_status = 'paid'
              AND write_date::date = %s
        """, (agent_id, report_date))
        vals["revenue"] = cr.fetchone()[0]

        # ── QA KPIs (attributed to call date) ──────────────────
        cr.execute("""
            SELECT
                COUNT(*) AS eval_count,
                COUNT(*) FILTER (WHERE r.auto_fail = TRUE) AS auto_fails,
                COALESCE(AVG(r.effective_score), 0)::numeric(5,2) AS avg_score
            FROM ons_qa_result r
            JOIN ons_call_log cl ON cl.id = r.call_log_id
            WHERE r.agent_id = %s
              AND r.state != 'draft'
              AND cl.call_start::date = %s
        """, (agent_id, report_date))
        qa = cr.fetchone()
        vals["qa_eval_count"] = qa[0]
        vals["qa_auto_fail_count"] = qa[1]
        vals["qa_avg_score"] = float(qa[2])

        # ── Dispatch ────────────────────────────────────────────
        cr.execute("""
            SELECT COUNT(*)
            FROM ons_dispatch d
            JOIN ons_case c ON c.id = d.case_id
            WHERE c.intake_agent_id = %s AND d.create_date::date = %s
        """, (agent_id, report_date))
        vals["dispatch_count"] = cr.fetchone()[0]

        # ── AI cost ─────────────────────────────────────────────
        cr.execute("""
            SELECT COALESCE(SUM(total_cost), 0)
            FROM ons_ai_run
            WHERE user_id = %s AND create_date::date = %s
        """, (agent_id, report_date))
        vals["ai_cost"] = cr.fetchone()[0]

        return vals
