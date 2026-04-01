/** @odoo-module **/

/**
 * Discord-inspired UX enhancements for Odoo 19 Discuss:
 * - Unread message count shown in browser tab title
 * - Watches Store.menu.counter reactively
 */
import { patch } from "@web/core/utils/patch";
import { Store } from "@mail/core/common/store_service";
import { effect } from "@web/core/utils/reactive";

const _origTitle = document.title;

patch(Store.prototype, {
    onStarted() {
        super.onStarted(...arguments);
        // Reactively update browser tab title when unread counter changes
        effect(
            (menu) => {
                const count = menu?.counter || 0;
                document.title = count > 0 ? `(${count}) ${_origTitle}` : _origTitle;
            },
            [this.menu]
        );
    },
});
