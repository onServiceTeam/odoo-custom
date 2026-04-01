/** @odoo-module **/

/**
 * Declare the Thread.sequence field used by ons_discuss_threads.
 */
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {number} */
        this.sequence = 10;
    },
});
