/** @odoo-module **/

/**
 * Operations Center Dashboard — client action component.
 *
 * Renders KPI cards with live counts from the ORM, status indicators,
 * and quick-action buttons linking to key areas. Matches the legacy
 * SmartOpsDashboard layout with operations-specific metrics.
 */
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class OpsDashboard extends Component {
    static template = "ons_ops_shell.OpsDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = user;

        this.state = useState({
            userName: user.name || "",
            // Core KPIs
            openInteractions: 0,
            openCases: 0,
            callbacksPending: 0,
            activityCount: 0,
            customerCount: 0,
            // Status
            staleCases: 0,
            needsAttention: 0,
            todayInteractions: 0,
            // Clock
            etTime: "",
            loaded: false,
        });

        onWillStart(async () => {
            await this._loadKpis();
            this._startClock();
        });
    }

    // ── KPI loading ──────────────────────────────────────────────

    async _loadKpis() {
        try {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const todayStr = today.toISOString().split("T")[0] + " 00:00:00";

            const results = await Promise.allSettled([
                this.orm.searchCount("ons.interaction", [
                    ["state", "in", ["new", "classified", "assigned"]],
                ]),
                this.orm.searchCount("ons.case", [
                    ["is_closed", "=", false],
                ]),
                this.orm.searchCount("ons.interaction", [
                    ["callback_requested", "=", true],
                    ["state", "!=", "completed"],
                ]),
                this.orm.searchCount("mail.activity", [
                    ["user_id", "=", this.user.userId],
                ]),
                this.orm.searchCount("res.partner", [
                    ["customer_rank", ">", 0],
                ]),
                this.orm.searchCount("ons.case", [
                    ["is_stale", "=", true],
                    ["is_closed", "=", false],
                ]),
                this.orm.searchCount("ons.case", [
                    ["needs_attention", "=", true],
                ]),
                this.orm.searchCount("ons.interaction", [
                    ["create_date", ">=", todayStr],
                ]),
            ]);

            const val = (i) => results[i]?.status === "fulfilled" ? results[i].value : 0;

            Object.assign(this.state, {
                openInteractions: val(0),
                openCases: val(1),
                callbacksPending: val(2),
                activityCount: val(3),
                customerCount: val(4),
                staleCases: val(5),
                needsAttention: val(6),
                todayInteractions: val(7),
                loaded: true,
            });
        } catch {
            this.state.loaded = true;
        }
    }

    _startClock() {
        this._updateClock();
        this._clockInterval = setInterval(() => this._updateClock(), 60000);
    }

    _updateClock() {
        try {
            const now = new Date();
            this.state.etTime = now.toLocaleTimeString("en-US", {
                timeZone: "America/New_York",
                hour: "2-digit",
                minute: "2-digit",
                hour12: true,
            });
        } catch {
            this.state.etTime = "";
        }
    }

    // ── Quick Action handlers ────────────────────────────────────

    openInteractions() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Interactions",
            res_model: "ons.interaction",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["new", "classified", "assigned"]]],
        });
    }

    openCases() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Open Cases",
            res_model: "ons.case",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["is_closed", "=", false]],
        });
    }

    openCallbacks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Callbacks",
            res_model: "ons.interaction",
            views: [[false, "list"], [false, "form"]],
            domain: [["callback_requested", "=", true], ["state", "!=", "completed"]],
        });
    }

    openActivities() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Activities",
            res_model: "mail.activity",
            views: [[false, "list"], [false, "form"]],
            domain: [["user_id", "=", this.user.userId]],
        });
    }

    openCustomers() {
        this.action.doAction("contacts.action_contacts");
    }

    openNeedsAttention() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Cases Needing Attention",
            res_model: "ons.case",
            views: [[false, "list"], [false, "form"]],
            domain: [["needs_attention", "=", true]],
        });
    }

    newInteraction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Interaction",
            res_model: "ons.interaction",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openDiscuss() {
        this.action.doAction("mail.action_discuss");
    }

    openPipeline() {
        this.action.doAction("crm.crm_lead_action_pipeline");
    }
}

registry.category("actions").add("ons_ops_shell.dashboard", OpsDashboard);
