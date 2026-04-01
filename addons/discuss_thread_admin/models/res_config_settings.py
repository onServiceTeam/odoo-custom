# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    discuss_thread_admin_only_delete = fields.Boolean(
        string="Only Admins Can Delete Threads",
        help=(
            "When enabled, only users in the Administration / Settings group can "
            "delete Discuss threads. Thread creators will NOT be able to delete "
            "or archive their own threads."
        ),
        config_parameter="discuss_thread_admin.admin_only_delete",
    )

    discuss_auto_cleanup_empty_groups = fields.Boolean(
        string="Auto-Cleanup Empty Group Chats",
        help=(
            "When enabled, group conversations are automatically deleted when "
            "the last member leaves. Prevents orphaned ghost channels."
        ),
        config_parameter="discuss_thread_admin.auto_cleanup_empty_groups",
        default=True,
    )

    discuss_giphy_api_key = fields.Char(
        string="GIPHY API Key",
        help="GIPHY API key for the GIF picker in Discuss. Get one free at developers.giphy.com.",
        config_parameter="discuss.giphy_api_key",
    )

    discuss_channels_label = fields.Char(
        string="Channels Category Label",
        help="Custom label for the 'Channels' sidebar category. Leave blank for default.",
        config_parameter="discuss_thread_admin.channels_label",
    )

    discuss_chats_label = fields.Char(
        string="Direct Messages Category Label",
        help="Custom label for the 'Direct messages' sidebar category. Leave blank for default.",
        config_parameter="discuss_thread_admin.chats_label",
    )

    discuss_hide_looking_for_help = fields.Boolean(
        string="Hide 'Looking for Help' Category",
        help="Hide the livechat 'Looking for help' category from the sidebar.",
        config_parameter="discuss_thread_admin.hide_looking_for_help",
    )
