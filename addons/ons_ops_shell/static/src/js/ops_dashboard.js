/** @odoo-module **/

/**
 * Operations Center Dashboard — client action component.
 *
 * Renders KPI cards with live counts from the ORM and quick-action
 * buttons linking to key areas.  Future ons_ops_* modules can extend
 * this dashboard by patching the class or adding to the
 * "ons_ops_dashboard_items" registry (not yet implemented — will be
 * added when the first business module needs it).
 *
 * Registered under the action tag "ons_ops_shell.dashboard" which
 * matches the ir.actions.client record in ops_dashboard_action.xml.
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
            customerCount: 0,
            leadCount: 0,
            activityCount: 0,
            loaded: false,
        });

        onWillStart(async () => {
            await this._loadKpis();
        });
    }

    // ── KPI loading ──────────────────────────────────────────────

    async _loadKpis() {
        try {
            const [customerCount, leadCount, activityCount] = await Promise.all([
                this.orm.searchCount("res.partner", [
                    ["customer_rank", ">", 0],
                ]),
                this.orm.searchCount("crm.lead", []),
                this.orm.searchCount("mail.activity", [
                    ["user_id", "=", this.user.userId],
                ]),
            ]);
            Object.assign(this.state, {
                customerCount,
                leadCount,
                activityCount,
                loaded: true,
            });
        } catch {
            // Graceful degradation — cards show 0 if a model is inaccessible
            this.state.loaded = true;
        }
    }

    // ── Quick Action handlers ────────────────────────────────────

    openContacts() {
        this.action.doAction("contacts.action_contacts");
    }

    openPipeline() {
        this.action.doAction("crm.crm_lead_action_pipeline");
    }

    openDiscuss() {
        this.action.doAction("mail.action_discuss");
    }

    openActivities() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Activities",
            res_model: "mail.activity",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["user_id", "=", this.user.userId]],
        });
    }
}

registry.category("actions").add("ons_ops_shell.dashboard", OpsDashboard);
