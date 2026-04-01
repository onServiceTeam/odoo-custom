/** @odoo-module **/

/**
 * For admins: replace the stock "delete" (which merely empties the body and
 * leaves a "this message has been removed" ghost) with a true permanent
 * delete that unlinks the record from the database.
 *
 * Also hides the stock "delete" action for admins so there is only ONE
 * delete button visible.
 */
import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { ACTION_TAGS } from "@mail/core/common/action";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { toRaw } from "@odoo/owl";

// ── 1. Hide the stock "delete" for admins — they get permanent delete instead ──
const stockDelete = messageActionsRegistry.get("delete");
messageActionsRegistry.add("delete", {
    ...stockDelete,
    condition(params) {
        // If user is admin, hide stock delete — our permanent delete replaces it
        if (params.store.self.main_user_id?.is_admin) {
            return false;
        }
        return stockDelete.condition(params);
    },
}, { force: true });

// ── 2. Register "Delete" for admins — true permanent delete ─────────────────
messageActionsRegistry.add("admin-hard-delete", {
    condition: ({ message, store }) =>
        store.self.main_user_id?.is_admin &&
        message.message_type === "comment" &&
        !message.isBodyEmpty,
    icon: "fa fa-trash text-danger",
    name: _t("Delete"),
    onSelected: async ({ message: msg, owner, store }) => {
        const message = toRaw(msg);
        return new Promise((resolve) => {
            store.env.services.dialog.add(ConfirmationDialog, {
                title: _t("Delete Message"),
                body: _t("Permanently delete this message? This cannot be undone."),
                confirmLabel: _t("Delete"),
                confirm: async () => {
                    try {
                        await rpc("/discuss/channel/admin/hard_delete_message", {
                            message_id: message.id,
                        });
                        // Remove from the local store WITHOUT calling the server again.
                        // message.remove() would call /mail/message/update_content on
                        // an already-deleted record and throw an error.
                        if (message.thread) {
                            message.thread.messages = message.thread.messages.filter(
                                (m) => m.notEq(message)
                            );
                        }
                        message.delete();
                        store.env.services.notification.add(
                            _t("Message deleted."),
                            { type: "info" }
                        );
                        resolve(true);
                    } catch {
                        store.env.services.notification.add(
                            _t("Failed to delete message."),
                            { type: "danger" }
                        );
                        resolve(false);
                    }
                },
                cancel: () => resolve(false),
            });
        });
    },
    sequence: 120,
    tags: ACTION_TAGS.DANGER,
});
