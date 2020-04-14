# -*- coding: utf-8 -*-

from flask import Blueprint
import ckanext.accessrequests.utils as utils

accessrequests = Blueprint(u"accessrequests", __name__)


def get_blueprints():
    return [accessrequests]


def account_requests():
    return utils.account_requests()


def request_account(data=None, errors=None, error_summary=None):
    return utils.request_account(data, errors, error_summary)


def account_requests_management():
    return utils.account_requests_management()


accessrequests.add_url_rule(
    "/user/account_requests", view_func=account_requests
)
accessrequests.add_url_rule(
    "/user/register", view_func=request_account, methods=(u"POST", u"GET")
)
accessrequests.add_url_rule(
    "/user/account_requests_management",
    view_func=account_requests_management,
    methods=(u"POST", u"GET"),
)
