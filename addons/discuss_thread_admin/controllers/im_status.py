# -*- coding: utf-8 -*-
"""Override the manual IM status controller to prevent status hiding.

Users cannot manually set their status to away/busy/offline — presence
is determined by real activity only ("keep it real").
"""
from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.im_status import ImStatusController


class ImStatusControllerInherit(ImStatusController):

    @http.route("/mail/set_manual_im_status", methods=["POST"], type="jsonrpc", auth="user")
    def set_manual_im_status(self, status):
        # No-op — manual IM status changes are disabled.
        # Status is determined by real presence only.
        return {}
