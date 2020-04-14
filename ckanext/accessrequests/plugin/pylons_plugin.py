# -*- coding: utf-8 -*-

from routes.mapper import SubMapper

import ckantoolkit as tk

import ckan.plugins as p
from ckan.lib.activity_streams import activity_stream_string_functions


def activity_stream_string_reject_new_user(context, activity):
    return tk._("{actor} rejected new user {user}")


def activity_stream_string_approve_new_user(context, activity):
    return tk._("{actor} approved new user {user}")


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        activity_stream_string_functions[
            "reject new user"
        ] = activity_stream_string_reject_new_user
        activity_stream_string_functions[
            "approve new user"
        ] = activity_stream_string_approve_new_user

    # IRoutes

    def before_map(self, map):
        with SubMapper(
            map,
            controller="ckanext.accessrequests.controller:AccessRequestsController",
        ) as m:
            m.connect(
                "account_requests",
                "/user/account_requests",
                action="account_requests",
            )
            m.connect(
                "request_account", "/user/register", action="request_account"
            )
            m.connect(
                "account_requests_management",
                "/user/account_requests_management",
                action="account_requests_management",
            )
        return map
