# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ReportDriverDaily(models.Model):
    _name = "ons.report.driver.daily"
    _description = "Driver Daily Performance Report"
    _order = "report_date desc, driver_id"
    _rec_name = "display_name"

    _date_driver_unique = models.UniqueIndex(
        "(report_date, driver_id)",
        "Only one report row per driver per day.",
    )

    # ── Dimensions ──────────────────────────────────────────────
    report_date = fields.Date(required=True, index=True)
    driver_id = fields.Many2one(
        "ons.call.driver", string="Call Driver", required=True, index=True,
        ondelete="cascade",
    )
    driver_category = fields.Selection(
        related="driver_id.category", store=True, string="Category",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ── Interaction KPIs ────────────────────────────────────────
    total_interactions = fields.Integer(string="Interactions")

    # ── Case KPIs ───────────────────────────────────────────────
    cases_created = fields.Integer(string="Cases Created")

    # ── Derived ─────────────────────────────────────────────────
    conversion_rate = fields.Float(
        string="Conversion %", digits=(5, 2),
        compute="_compute_conversion_rate", store=True,
    )

    @api.depends("total_interactions", "cases_created")
    def _compute_conversion_rate(self):
        for rec in self:
            if rec.total_interactions:
                rec.conversion_rate = (
                    rec.cases_created / rec.total_interactions * 100.0
                )
            else:
                rec.conversion_rate = 0.0

    @api.depends("driver_id", "report_date")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.report_date:
                parts.append(str(rec.report_date))
            if rec.driver_id:
                parts.append(rec.driver_id.name or "")
            rec.display_name = " — ".join(parts) if parts else "Report"

    # ── Computation Engine ──────────────────────────────────────

    @api.model
    def _cron_recompute_daily(self):
        """Recompute yesterday's driver metrics."""
        yesterday = fields.Date.context_today(self) - timedelta(days=1)
        self.recompute_range(yesterday, yesterday)

    @api.model
    def recompute_range(self, date_from, date_to):
        """Recompute driver daily reports for a date range."""
        _logger.info("Recomputing driver daily reports: %s → %s", date_from, date_to)

        existing = self.search([
            ("report_date", ">=", date_from),
            ("report_date", "<=", date_to),
        ])
        if existing:
            existing.unlink()

        cr = self.env.cr

        # Collect distinct driver+date pairs from interactions
        cr.execute("""
            SELECT DISTINCT primary_driver_id, call_start::date
            FROM ons_interaction
            WHERE primary_driver_id IS NOT NULL
              AND call_start::date >= %s AND call_start::date <= %s
        """, (date_from, date_to))
        driver_dates_from_interactions = set(cr.fetchall())

        # Also from cases
        cr.execute("""
            SELECT DISTINCT primary_driver_id, create_date::date
            FROM ons_case
            WHERE primary_driver_id IS NOT NULL
              AND create_date::date >= %s AND create_date::date <= %s
        """, (date_from, date_to))
        driver_dates_from_cases = set(cr.fetchall())

        all_driver_dates = driver_dates_from_interactions | driver_dates_from_cases

        vals_list = []
        for (driver_id, report_date) in all_driver_dates:
            vals = self._compute_driver_day(driver_id, report_date)
            vals_list.append(vals)

        if vals_list:
            self.create(vals_list)
            _logger.info("Created %d driver daily reports", len(vals_list))

    @api.model
    def _compute_driver_day(self, driver_id, report_date):
        """Compute KPIs for one driver on one day."""
        cr = self.env.cr
        vals = {
            "report_date": report_date,
            "driver_id": driver_id,
        }

        cr.execute("""
            SELECT COUNT(*)
            FROM ons_interaction
            WHERE primary_driver_id = %s AND call_start::date = %s
        """, (driver_id, report_date))
        vals["total_interactions"] = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*)
            FROM ons_case
            WHERE primary_driver_id = %s AND create_date::date = %s
        """, (driver_id, report_date))
        vals["cases_created"] = cr.fetchone()[0]

        return vals
