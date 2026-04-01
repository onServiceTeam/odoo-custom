/** @odoo-module **/

/**
 * Register admin channel management actions:
 * - "Kick Member" action in thread actions (admin-only)
 * - "Channel Info" action for admins to see channel details
 */
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { ACTION_TAGS } from "@mail/core/common/action";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

class KickMemberDialog extends Component {
    static components = { Dialog };
    static props = ["thread", "close"];
    static template = xml`
        <Dialog size="'md'" title="'Remove Member'" footer="false" bodyClass="'p-3'">
            <div class="mb-3 text-muted">
                Select a member to remove from <strong t-esc="props.thread.displayName"/>
            </div>
            <div class="list-group">
                <t t-foreach="members" t-as="member" t-key="member.id">
                    <button class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                            t-on-click="() => this.kickMember(member)">
                        <span t-esc="member.persona and member.persona.name ? member.persona.name : '(Guest)'"/>
                        <i class="fa fa-user-times text-danger"/>
                    </button>
                </t>
                <div t-if="!members.length" class="list-group-item text-muted text-center">
                    No members to remove.
                </div>
            </div>
        </Dialog>
    `;

    get members() {
        // Filter out the current admin from the kick list
        const self = this.props.thread.store?.self;
        return (this.props.thread.channel_member_ids || []).filter(
            (m) => m.persona && !m.persona.eq?.(self)
        );
    }

    async kickMember(member) {
        const persona = member.persona;
        if (!persona) return;
        const partnerId = persona.id;
        const memberName = persona.name || "(Guest)";

        try {
            await rpc("/discuss/channel/admin/kick_member", {
                channel_id: this.props.thread.id,
                partner_id: partnerId,
            });
            this.props.thread.store.env.services.notification.add(
                _t('%(member_name)s has been removed.', { member_name: memberName }),
                { type: "info" }
            );
            this.props.close();
        } catch {
            this.props.thread.store.env.services.notification.add(
                _t("Failed to remove member."),
                { type: "danger" }
            );
        }
    }
}

registerThreadAction("admin-kick-member", {
    condition: ({ store, thread }) =>
        store.self.main_user_id?.is_admin &&
        thread?.model === "discuss.channel" &&
        thread.channel_type !== "chat",
    icon: "fa fa-fw fa-user-times",
    name: _t("Remove Member"),
    open: ({ store, thread }) => {
        store.env.services.dialog?.add(KickMemberDialog, { thread });
    },
    sequence: 35,
    sequenceGroup: 30,
    tags: ACTION_TAGS.DANGER,
});
