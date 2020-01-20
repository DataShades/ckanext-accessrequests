# -*- coding: utf-8 -*-

from ckan.controllers.user import UserController

import ckanext.accessrequests.utils as utils


class AccessRequestsController(UserController):
    def request_account(self, data=None, errors=None, error_summary=None):
        """GET to display a form for requesting a user account or POST the
           form data to submit the request.
        """
        return utils.request_account(data, errors, error_summary)

    def account_requests(self):
        """ /ckan-admin/account_requests rendering
        """
        return utils.account_requests()

    def account_requests_management(self):
        """ Approve or reject an account request
        """
        return utils.account_requests_management()
