/** @odoo-module **/

/**
 * Patch Thread.leaveChannel() to show a warning when the user is the
 * last member and auto-cleanup is enabled (the channel will be deleted).
 */
import { patch } from "@web/core/utils/patch";
import { Thread } from "@mail/core/common/thread_model";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(Thread.prototype, {
    async leaveChannel({ force = false } = {}) {
        if (!force && this.channel_type === "group") {
            let warning = null;
            try {
                const check = await rpc("/discuss/channel/admin/pre_leave_check", {
                    channel_id: this.id,
                });
                warning = check.warning;
            } catch {
                // RPC failed — fall through to stock behavior
            }
            if (warning === "last_member_auto_delete") {
                try {
                    await new Promise((resolve, reject) => {
                        this.store.env.services.dialog.add(ConfirmationDialog, {
                            body: _t(
                                "You are the last member of this group. Leaving will permanently delete this conversation and all its messages. Are you sure?"
                            ),
                            confirmLabel: _t("Leave and Delete"),
                            confirm: resolve,
                            cancel: reject,
                        });
                    });
                } catch {
                    return; // User cancelled
                }
                return super.leaveChannel({ force: true });
            } else if (warning === "last_member") {
                try {
                    await new Promise((resolve, reject) => {
                        this.store.env.services.dialog.add(ConfirmationDialog, {
                            body: _t(
                                "You are the last member of this group. The conversation will become empty. Are you sure you want to leave?"
                            ),
                            confirmLabel: _t("Leave Conversation"),
                            confirm: resolve,
                            cancel: reject,
                        });
                    });
                } catch {
                    return; // User cancelled
                }
                return super.leaveChannel({ force: true });
            }
        }
        return super.leaveChannel({ force });
    },
});
