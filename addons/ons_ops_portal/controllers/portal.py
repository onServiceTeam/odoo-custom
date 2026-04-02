# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class OnsPortal(CustomerPortal):

    # ── Home counters ───────────────────────────────────────────────

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.commercial_partner_id
        Case = request.env["ons.case"]
        Plan = request.env["ons.customer.plan"]
        Dispatch = request.env["ons.dispatch"]

        if "case_count" in counters:
            values["case_count"] = (
                Case.search_count(self._get_case_domain(partner))
                if Case.has_access("read")
                else 0
            )
        if "plan_count" in counters:
            values["plan_count"] = (
                Plan.search_count(self._get_plan_domain(partner))
                if Plan.has_access("read")
                else 0
            )
        if "dispatch_count" in counters:
            values["dispatch_count"] = (
                Dispatch.search_count(self._get_dispatch_domain(partner))
                if Dispatch.has_access("read")
                else 0
            )
        return values

    # ── Domain helpers ──────────────────────────────────────────────

    @staticmethod
    def _get_case_domain(partner):
        return [("partner_id", "child_of", [partner.id])]

    @staticmethod
    def _get_plan_domain(partner):
        return [("partner_id", "child_of", [partner.id])]

    @staticmethod
    def _get_dispatch_domain(partner):
        return [("partner_id", "child_of", [partner.id])]

    @staticmethod
    def _get_consent_domain(partner):
        return [("partner_id", "child_of", [partner.id])]

    # ═══════════════════════════════════════════════════════════════
    #  CASES
    # ═══════════════════════════════════════════════════════════════

    def _case_get_searchbar_sortings(self):
        return {
            "date": {"label": _("Newest"), "order": "create_date desc"},
            "name": {"label": _("Reference"), "order": "name asc"},
            "stage": {"label": _("Status"), "order": "stage_id asc"},
        }

    def _case_get_searchbar_filters(self):
        return {
            "all": {"label": _("All"), "domain": []},
            "open": {
                "label": _("Open"),
                "domain": [("is_closed", "=", False)],
            },
            "closed": {
                "label": _("Closed"),
                "domain": [("is_closed", "=", True)],
            },
        }

    @http.route(
        ["/my/cases", "/my/cases/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_cases(self, page=1, sortby=None, filterby=None, **kw):
        partner = request.env.user.commercial_partner_id
        Case = request.env["ons.case"]
        domain = self._get_case_domain(partner)

        searchbar_sortings = self._case_get_searchbar_sortings()
        sortby = sortby if sortby in searchbar_sortings else "date"

        searchbar_filters = self._case_get_searchbar_filters()
        filterby = filterby if filterby in searchbar_filters else "all"
        domain += searchbar_filters[filterby]["domain"]

        case_count = Case.search_count(domain)
        pager = portal_pager(
            url="/my/cases",
            total=case_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )
        cases = Case.search(
            domain,
            order=searchbar_sortings[sortby]["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "cases": cases,
                "page_name": "cases",
                "pager": pager,
                "default_url": "/my/cases",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
                "filterby": filterby,
            }
        )
        return request.render("ons_ops_portal.portal_my_cases", values)

    @http.route(
        ["/my/cases/<int:case_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_case_detail(self, case_id, access_token=None, **kw):
        try:
            case_sudo = self._document_check_access(
                "ons.case", case_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "case": case_sudo,
                "page_name": "case",
            }
        )
        return request.render("ons_ops_portal.portal_case_detail", values)

    # ═══════════════════════════════════════════════════════════════
    #  PLANS
    # ═══════════════════════════════════════════════════════════════

    def _plan_get_searchbar_sortings(self):
        return {
            "date": {"label": _("End Date"), "order": "end_date asc"},
            "state": {"label": _("Status"), "order": "state asc"},
            "name": {"label": _("Plan"), "order": "plan_code asc"},
        }

    def _plan_get_searchbar_filters(self):
        return {
            "all": {"label": _("All"), "domain": []},
            "active": {
                "label": _("Active"),
                "domain": [("state", "=", "active")],
            },
            "expiring": {
                "label": _("Expiring Soon"),
                "domain": [("state", "=", "expiring_soon")],
            },
        }

    @http.route(
        ["/my/plans", "/my/plans/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_plans(self, page=1, sortby=None, filterby=None, **kw):
        partner = request.env.user.commercial_partner_id
        Plan = request.env["ons.customer.plan"]
        domain = self._get_plan_domain(partner)

        searchbar_sortings = self._plan_get_searchbar_sortings()
        sortby = sortby if sortby in searchbar_sortings else "date"

        searchbar_filters = self._plan_get_searchbar_filters()
        filterby = filterby if filterby in searchbar_filters else "all"
        domain += searchbar_filters[filterby]["domain"]

        plan_count = Plan.search_count(domain)
        pager = portal_pager(
            url="/my/plans",
            total=plan_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )
        plans = Plan.search(
            domain,
            order=searchbar_sortings[sortby]["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "plans": plans,
                "page_name": "plans",
                "pager": pager,
                "default_url": "/my/plans",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
                "filterby": filterby,
            }
        )
        return request.render("ons_ops_portal.portal_my_plans", values)

    @http.route(
        ["/my/plans/<int:plan_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_plan_detail(self, plan_id, access_token=None, **kw):
        try:
            plan_sudo = self._document_check_access(
                "ons.customer.plan", plan_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "plan": plan_sudo,
                "page_name": "plan",
            }
        )
        return request.render("ons_ops_portal.portal_plan_detail", values)

    # ═══════════════════════════════════════════════════════════════
    #  DISPATCHES
    # ═══════════════════════════════════════════════════════════════

    def _dispatch_get_searchbar_sortings(self):
        return {
            "date": {
                "label": _("Scheduled Date"),
                "order": "scheduled_start desc",
            },
            "status": {"label": _("Status"), "order": "status_id asc"},
            "name": {"label": _("Reference"), "order": "name asc"},
        }

    def _dispatch_get_searchbar_filters(self):
        return {
            "all": {"label": _("All"), "domain": []},
            "upcoming": {
                "label": _("Upcoming"),
                "domain": [("is_terminal", "=", False)],
            },
            "completed": {
                "label": _("Completed"),
                "domain": [("is_terminal", "=", True)],
            },
        }

    @http.route(
        ["/my/dispatches", "/my/dispatches/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_dispatches(self, page=1, sortby=None, filterby=None, **kw):
        partner = request.env.user.commercial_partner_id
        Dispatch = request.env["ons.dispatch"]
        domain = self._get_dispatch_domain(partner)

        searchbar_sortings = self._dispatch_get_searchbar_sortings()
        sortby = sortby if sortby in searchbar_sortings else "date"

        searchbar_filters = self._dispatch_get_searchbar_filters()
        filterby = filterby if filterby in searchbar_filters else "all"
        domain += searchbar_filters[filterby]["domain"]

        dispatch_count = Dispatch.search_count(domain)
        pager = portal_pager(
            url="/my/dispatches",
            total=dispatch_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )
        dispatches = Dispatch.search(
            domain,
            order=searchbar_sortings[sortby]["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "dispatches": dispatches,
                "page_name": "dispatches",
                "pager": pager,
                "default_url": "/my/dispatches",
                "searchbar_sortings": searchbar_sortings,
                "sortby": sortby,
                "searchbar_filters": OrderedDict(sorted(searchbar_filters.items())),
                "filterby": filterby,
            }
        )
        return request.render("ons_ops_portal.portal_my_dispatches", values)

    @http.route(
        ["/my/dispatches/<int:dispatch_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_dispatch_detail(self, dispatch_id, access_token=None, **kw):
        try:
            dispatch_sudo = self._document_check_access(
                "ons.dispatch", dispatch_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "dispatch": dispatch_sudo,
                "page_name": "dispatch",
            }
        )
        return request.render("ons_ops_portal.portal_dispatch_detail", values)

    # ═══════════════════════════════════════════════════════════════
    #  CONSENT
    # ═══════════════════════════════════════════════════════════════

    @http.route(
        ["/my/consent"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_consent(self, **kw):
        partner = request.env.user.commercial_partner_id
        consents = request.env["ons.contact.consent"].search(
            self._get_consent_domain(partner)
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "consents": consents,
                "page_name": "consent",
            }
        )
        return request.render("ons_ops_portal.portal_my_consent", values)

    @http.route(
        ["/my/consent/toggle"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def portal_consent_toggle(self, consent_id=None, action=None, **kw):
        """Toggle opt-in / opt-out for a specific consent record."""
        partner = request.env.user.commercial_partner_id
        if not consent_id or not action:
            return request.redirect("/my/consent")

        try:
            consent_id = int(consent_id)
        except (ValueError, TypeError):
            return request.redirect("/my/consent")

        consent = request.env["ons.contact.consent"].search(
            [("id", "=", consent_id), ("partner_id", "child_of", [partner.id])],
            limit=1,
        )
        if not consent:
            return request.redirect("/my/consent")

        if action == "opt_in" and consent.status == "pending":
            consent.sudo().action_opt_in()
        elif action == "opt_out" and consent.status in (
            "opted_in",
            "double_opted_in",
        ):
            consent.sudo().action_opt_out()

        return request.redirect("/my/consent")
