/** @odoo-module **/

/**
 * Drag-and-drop channel reordering in the sidebar (admin only).
 * - Patches DiscussAppCategory.sortThreads() to sort by sequence field
 * - Patches DiscussSidebarCategories to enable drag-and-drop via useSortable
 */
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app_category_model";
import { DiscussSidebarCategories } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { patch } from "@web/core/utils/patch";
import { useSortable } from "@web/core/utils/sortable_owl";
import { useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

// ── 1. Sort channels by sequence instead of alphabetically ──────────────
patch(DiscussAppCategory.prototype, {
    sortThreads(t1, t2) {
        if (this.id === "channels") {
            const s1 = t1.sequence ?? 10;
            const s2 = t2.sequence ?? 10;
            if (s1 !== s2) return s1 - s2;
            // Fallback to alphabetical when sequences are equal
            return String.prototype.localeCompare.call(t1.name ?? "", t2.name ?? "");
        }
        return super.sortThreads(t1, t2);
    },
});

// ── 2. Enable drag-and-drop on the channel list ─────────────────────────
patch(DiscussSidebarCategories.prototype, {
    setup() {
        super.setup(...arguments);
        this.rootRef = useRef("root");
        this.notification = useService("notification");
        const isAdmin = this.store.self?.main_user_id?.is_admin;
        if (isAdmin) {
            useSortable({
                ref: this.rootRef,
                elements: ".o-mail-DiscussSidebarChannel-container",
                handle: ".o-mail-DiscussSidebarChannel-itemMain",
                cursor: "grabbing",
                clone: true,
                placeholderClasses: ["o-dragging"],
                onDrop: async ({ element, previous, next }) => {
                    await this._onChannelDrop(element, previous, next);
                },
            });
        }
    },

    async _onChannelDrop(element, previous, next) {
        // Extract channel IDs from the DOM order after drop
        if (!this.rootRef.el) return;
        const containers = this.rootRef.el.querySelectorAll(
            ".o-mail-DiscussSidebarChannel-container"
        );
        // Map DOM elements back to thread IDs
        // Each container holds a DiscussSidebarChannel whose thread can be identified
        // by the data-channel-id attribute we'll add via template patch
        const channelIds = [];
        for (const container of containers) {
            const idAttr = container.dataset.channelId;
            if (idAttr) {
                channelIds.push(parseInt(idAttr, 10));
            }
        }
        if (channelIds.length === 0) return;

        // Update local sequences immediately for instant feedback
        for (let i = 0; i < channelIds.length; i++) {
            const thread = this.store.Thread.get({ model: "discuss.channel", id: channelIds[i] });
            if (thread) {
                thread.sequence = i * 10;
            }
        }

        // Persist to server
        try {
            await rpc("/discuss/channel/admin/reorder", { channel_ids: channelIds });
        } catch {
            this.notification.add("Failed to save channel order.", { type: "danger" });
        }
    },
});
