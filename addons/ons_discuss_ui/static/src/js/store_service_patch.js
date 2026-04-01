/** @odoo-module **/

/**
 * Declare custom Store fields used by ons_discuss_ui.
 */
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {{ emoji: string, text: string }} */
        this.selfWorkStatus = { emoji: "", text: "" };
        /** @type {Array<{ key: string, emoji: string, text: string }>} */
        this.workStatusPresets = [];
    },
});
