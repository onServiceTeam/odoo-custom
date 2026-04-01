/** @odoo-module **/

/**
 * Declare custom Store and Thread fields used by the discuss_thread_admin module.
 * Following the stock pattern from mail/discuss/gif_picker/common/store_service_patch.js
 */
import { Store } from "@mail/core/common/store_service";
import { Thread } from "@mail/core/common/thread_model";
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

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean} */
        this.is_voice_channel = false;
        /** @type {number} */
        this.sequence = 10;
    },
});
