# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ReportQueueDaily(models.Model):
    _name = "ons.report.queue.daily"
    _description = "Queue Daily Performance Report"
    _order = "report_date desc, queue_name"
    _rec_name = "display_name"

    _date_queue_unique = models.UniqueIndex(
        "(report_date, queue_name)",
        "Only one report row per queue per day.",
    )

    # ── Dimensions ──────────────────────────────────────────────
    report_date = fields.Date(required=True, index=True)
    queue_name = fields.Char(string="Queue", required=True, index=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ── Call KPIs ───────────────────────────────────────────────
    total_calls = fields.Integer(string="Total Calls")
    answered_calls = fields.Integer(string="Answered")
    missed_calls = fields.Integer(string="Missed")
    avg_talk_duration = fields.Integer(string="Avg Talk (s)")
    avg_wait_duration = fields.Integer(string="Avg Wait (s)")

    # ── Case KPIs ───────────────────────────────────────────────
    cases_created = fields.Integer(string="Cases Created")

    @api.depends("queue_name", "report_date")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.report_date:
                parts.append(str(rec.report_date))
            if rec.queue_name:
                parts.append(rec.queue_name)
            rec.display_name = " — ".join(parts) if parts else "Report"

    # ── Computation Engine ──────────────────────────────────────

    @api.model
    def _cron_recompute_daily(self):
        """Recompute yesterday's queue metrics (called from agent daily cron)."""
        yesterday = fields.Date.context_today(self) - timedelta(days=1)
        self.recompute_range(yesterday, yesterday)

    @api.model
    def recompute_range(self, date_from, date_to):
        """Recompute queue daily reports for a date range."""
        _logger.info("Recomputing queue daily reports: %s → %s", date_from, date_to)

        existing = self.search([
            ("report_date", ">=", date_from),
            ("report_date", "<=", date_to),
        ])
        if existing:
            existing.unlink()

        cr = self.env.cr

        # Collect distinct queues with activity
        cr.execute("""
            SELECT DISTINCT queue_name, call_start::date
            FROM ons_call_log
            WHERE queue_name IS NOT NULL AND queue_name != ''
              AND call_start::date >= %s AND call_start::date <= %s
        """, (date_from, date_to))
        queue_dates = cr.fetchall()

        vals_list = []
        for (queue_name, report_date) in queue_dates:
            vals = self._compute_queue_day(queue_name, report_date)
            vals_list.append(vals)

        if vals_list:
            self.create(vals_list)
            _logger.info("Created %d queue daily reports", len(vals_list))

    @api.model
    def _compute_queue_day(self, queue_name, report_date):
        """Compute KPIs for one queue on one day."""
        cr = self.env.cr
        vals = {
            "report_date": report_date,
            "queue_name": queue_name,
        }

        cr.execute("""
            SELECT
                COUNT(*) AS total_calls,
                COUNT(*) FILTER (WHERE disposition = 'answered') AS answered,
                COUNT(*) FILTER (WHERE disposition = 'missed') AS missed,
                COALESCE(AVG(talk_duration) FILTER (WHERE disposition = 'answered'), 0)::int AS avg_talk,
                COALESCE(AVG(wait_duration), 0)::int AS avg_wait
            FROM ons_call_log
            WHERE queue_name = %s AND call_start::date = %s
        """, (queue_name, report_date))
        row = cr.fetchone()
        vals["total_calls"] = row[0]
        vals["answered_calls"] = row[1]
        vals["missed_calls"] = row[2]
        vals["avg_talk_duration"] = row[3]
        vals["avg_wait_duration"] = row[4]

        # Cases created from interactions that came through this queue
        # call_log.queue_name is raw string, interaction.queue_name is selection key
        # Join via call_log_id link instead
        cr.execute("""
            SELECT COUNT(DISTINCT c.id)
            FROM ons_case c
            JOIN ons_interaction i ON i.id = c.source_interaction_id
            JOIN ons_call_log cl ON cl.id = i.call_log_id
            WHERE cl.queue_name = %s AND c.create_date::date = %s
        """, (queue_name, report_date))
        vals["cases_created"] = cr.fetchone()[0]

        return vals
