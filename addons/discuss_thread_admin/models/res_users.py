# -*- coding: utf-8 -*-
from odoo import fields, models

WORK_STATUS_PRESETS = [
    ("meeting", "📅", "In a meeting"),
    ("commuting", "🚗", "Commuting"),
    ("sick", "🤒", "Out sick"),
    ("vacation", "🌴", "Vacationing"),
    ("remote", "🏠", "Working remotely"),
]


class ResUsers(models.Model):
    _inherit = "res.users"

    work_status_emoji = fields.Char("Work Status Emoji", default="")
    work_status_text = fields.Char("Work Status Text", default="")

    def write(self, vals):
        # Prevent manual IM status changes — status is based on real presence only.
        # Users cannot pretend to be offline/away/busy while actually online.
        vals.pop("manual_im_status", None)
        return super().write(vals)

    def _init_store_data(self, store):
        super()._init_store_data(store)
        # Enable GIF picker if GIPHY key is configured
        get_param = self.env["ir.config_parameter"].sudo().get_param
        giphy_key = get_param("discuss.giphy_api_key")
        if giphy_key:
            store.add_global_values(hasGifPickerFeature=True)
        # Send work status presets and current user's work status
        store.add_global_values(
            workStatusPresets=[
                {"key": key, "emoji": emoji, "text": text}
                for key, emoji, text in WORK_STATUS_PRESETS
            ],
            selfWorkStatus={
                "emoji": self.work_status_emoji or "",
                "text": self.work_status_text or "",
            },
        )
        # Send sidebar category configuration
        channels_label = get_param("discuss_thread_admin.channels_label") or ""
        chats_label = get_param("discuss_thread_admin.chats_label") or ""
        hide_lfh = get_param("discuss_thread_admin.hide_looking_for_help", "False") == "True"
        store.add_global_values(
            discussCategoryConfig={
                "channelsLabel": channels_label,
                "chatsLabel": chats_label,
                "hideLookingForHelp": hide_lfh,
            },
        )
