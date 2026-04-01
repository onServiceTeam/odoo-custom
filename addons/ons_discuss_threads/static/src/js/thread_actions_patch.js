/** @odoo-module **/

/**
 * Override the "delete-thread" action condition to allow admins to delete
 * any thread, not just threads they created.
 */
import { threadActionsRegistry } from "@mail/core/common/thread_actions";

const originalDeleteThread = threadActionsRegistry.get("delete-thread");

threadActionsRegistry.add("delete-thread", {
    ...originalDeleteThread,
    condition({ owner, store, thread }) {
        if (!thread?.parent_channel_id || owner.isDiscussContent) {
            return false;
        }
        const isAdmin = store.self.main_user_id?.is_admin;
        // Fall back to original creator check if create_uid is available
        const isCreator = thread.create_uid && store.self.main_user_id?.eq(thread.create_uid);
        return isAdmin || isCreator;
    },
}, { force: true });
