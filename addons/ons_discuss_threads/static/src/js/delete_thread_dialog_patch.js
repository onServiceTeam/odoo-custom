/** @odoo-module **/

/**
 * Patch DeleteThreadDialog to check admin-only settings and show
 * appropriate error messages when non-admins try to delete.
 */
import { patch } from "@web/core/utils/patch";
import { DeleteThreadDialog } from "@mail/discuss/core/common/delete_thread_dialog";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(DeleteThreadDialog.prototype, {
    async onConfirmation() {
        try {
            // Check if admin-only delete is enabled and user is not admin
            const settings = await rpc("/discuss/channel/sub_channel/thread_settings");
            if (settings.admin_only_delete && !settings.is_admin) {
                this.env.services.notification.add(
                    _t("Only administrators can delete threads."),
                    { type: "warning" }
                );
                this.props.close();
                return;
            }
        } catch {
            // If settings endpoint fails, fall through to original behavior
        }
        return super.onConfirmation();
    },
});
