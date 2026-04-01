/** @odoo-module **/

/**
 * Declare the Thread.is_voice_channel field used by ons_discuss_voice.
 */
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {boolean} */
        this.is_voice_channel = false;
    },
});
