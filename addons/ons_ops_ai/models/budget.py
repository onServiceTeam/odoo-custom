from odoo import api, fields, models
from odoo.exceptions import UserError


class AiBudget(models.Model):
    _name = 'ons.ai.budget'
    _description = 'AI Budget Enforcement'

    name = fields.Char(default='AI Budget', required=True)
    daily_limit = fields.Float(string='Daily Budget ($)', default=50.0, digits=(10, 2))
    monthly_limit = fields.Float(string='Monthly Budget ($)', default=1000.0, digits=(10, 2))
    alert_threshold_pct = fields.Integer(
        string='Alert Threshold (%)', default=80,
        help='Percentage of budget at which to show warnings',
    )

    daily_spent = fields.Float(
        string='Spent Today ($)', compute='_compute_spent',
        digits=(10, 6),
    )
    monthly_spent = fields.Float(
        string='Spent This Month ($)', compute='_compute_spent',
        digits=(10, 6),
    )
    daily_pct = fields.Float(
        string='Daily Usage %', compute='_compute_spent',
    )
    monthly_pct = fields.Float(
        string='Monthly Usage %', compute='_compute_spent',
    )
    is_over_daily = fields.Boolean(compute='_compute_spent')
    is_over_monthly = fields.Boolean(compute='_compute_spent')
    is_alert_daily = fields.Boolean(compute='_compute_spent')
    is_alert_monthly = fields.Boolean(compute='_compute_spent')

    @api.depends('daily_limit', 'monthly_limit', 'alert_threshold_pct')
    def _compute_spent(self):
        Run = self.env['ons.ai.run']
        today = fields.Date.today()
        month_start = today.replace(day=1)
        for rec in self:
            daily = Run.sudo().search([
                ('success', '=', True),
                ('create_date', '>=', fields.Datetime.to_string(today)),
            ])
            monthly = Run.sudo().search([
                ('success', '=', True),
                ('create_date', '>=', fields.Datetime.to_string(month_start)),
            ])
            rec.daily_spent = sum(daily.mapped('total_cost'))
            rec.monthly_spent = sum(monthly.mapped('total_cost'))
            rec.daily_pct = (
                (rec.daily_spent / rec.daily_limit * 100)
                if rec.daily_limit else 0
            )
            rec.monthly_pct = (
                (rec.monthly_spent / rec.monthly_limit * 100)
                if rec.monthly_limit else 0
            )
            rec.is_over_daily = rec.daily_pct >= 100
            rec.is_over_monthly = rec.monthly_pct >= 100
            rec.is_alert_daily = rec.daily_pct >= rec.alert_threshold_pct
            rec.is_alert_monthly = rec.monthly_pct >= rec.alert_threshold_pct

    @api.model
    def check_budget(self):
        """Check budget before an AI call. Raises UserError if over limit.

        Called by the sidecar or Odoo actions before invoking AI.
        """
        budget = self.search([], limit=1)
        if not budget:
            return True
        budget._compute_spent()
        if budget.is_over_daily:
            raise UserError(
                f'AI daily budget exceeded: ${budget.daily_spent:.2f} '
                f'of ${budget.daily_limit:.2f} limit.'
            )
        if budget.is_over_monthly:
            raise UserError(
                f'AI monthly budget exceeded: ${budget.monthly_spent:.2f} '
                f'of ${budget.monthly_limit:.2f} limit.'
            )
        return True
