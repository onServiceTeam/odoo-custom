/** @odoo-module **/

/**
 * Replace the stock IM status dropdown (which allows hiding/faking status)
 * with a simple read-only status display + Slack-style work status setter.
 *
 * Users cannot change their online/offline status — it's based on real presence.
 * They CAN set a work status text + emoji (like Slack).
 */
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ImStatus } from "@mail/core/common/im_status";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

const WORK_STATUS_PRESETS = [
    { key: "meeting", emoji: "📅", text: "In a meeting" },
    { key: "commuting", emoji: "🚗", text: "Commuting" },
    { key: "sick", emoji: "🤒", text: "Out sick" },
    { key: "vacation", emoji: "🌴", text: "Vacationing" },
    { key: "remote", emoji: "🏠", text: "Working remotely" },
];

export class WorkStatusDropdown extends Component {
    static components = { Dropdown, DropdownItem, ImStatus };
    static props = [];
    static template = "ons_discuss_ui.WorkStatusDropdown";

    setup() {
        this.store = useService("mail.store");
        this.notification = useService("notification");
        this.presets = WORK_STATUS_PRESETS;
        this.state = useState({
            currentEmoji: this.store.selfWorkStatus?.emoji || "",
            currentText: this.store.selfWorkStatus?.text || "",
        });
    }

    get readableImStatus() {
        const status = this.store.self?.im_status || "offline";
        if (status.includes("online")) return _t("Online");
        if (status.includes("away")) return _t("Away");
        return _t("Offline");
    }

    get currentWorkStatus() {
        const { currentEmoji, currentText } = this.state;
        if (currentText) {
            return `${currentEmoji} ${currentText}`.trim();
        }
        return "";
    }

    async setWorkStatus(emoji, text) {
        this.state.currentEmoji = emoji;
        this.state.currentText = text;
        if (this.store.selfWorkStatus) {
            this.store.selfWorkStatus.emoji = emoji;
            this.store.selfWorkStatus.text = text;
        }
        await rpc("/discuss/set_work_status", { emoji, text });
    }

    async clearWorkStatus() {
        await this.setWorkStatus("", "");
    }
}

export function workStatusItem(env) {
    return {
        type: "component",
        contentComponent: WorkStatusDropdown,
        sequence: 45,
    };
}

// Override the stock IM status dropdown with our work status dropdown
registry.category("user_menuitems").add("im_status", workStatusItem, { force: true });
