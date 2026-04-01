/** @odoo-module **/

/**
 * Configurable sidebar categories:
 * - Rename "Channels" and "Direct messages" via admin settings
 * - Hide "Looking for Help" category via admin setting
 * - Config loaded in store.discussCategoryConfig from Python _init_store_data
 */
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app_category_model";
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";
import { effect } from "@web/core/utils/reactive";

// Declare the config field on Store
patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {{ channelsLabel: string, chatsLabel: string, hideLookingForHelp: boolean }} */
        this.discussCategoryConfig = {
            channelsLabel: "",
            chatsLabel: "",
            hideLookingForHelp: false,
        };
    },

    onStarted() {
        super.onStarted(...arguments);
        // Reactively apply custom category labels when config is loaded
        effect(
            (config) => {
                if (!config) return;
                const discuss = this.discuss;
                if (!discuss) return;
                if (config.channelsLabel && discuss.channels) {
                    discuss.channels.name = config.channelsLabel;
                }
                if (config.chatsLabel && discuss.chats) {
                    discuss.chats.name = config.chatsLabel;
                }
            },
            [this.discussCategoryConfig]
        );
    },
});

// Hide "Looking for Help" when admin setting is enabled
patch(DiscussAppCategory.prototype, {
    get isVisible() {
        if (
            this.id === "im_livechat.category_need_help" &&
            this.store.discussCategoryConfig?.hideLookingForHelp
        ) {
            return false;
        }
        return super.isVisible;
    },
});
