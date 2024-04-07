# -*- coding: utf-8 -*-

import json

import ckantoolkit as tk
from six import string_types

import ckan.authz as authz
import ckan.lib.helpers as h
import ckan.model as model
import ckan.plugins as plugins

if tk.check_ckan_version("2.9"):
    from ckanext.accessrequests.plugin.flask_plugin import MixinPlugin
else:
    from ckanext.accessrequests.plugin.pylons_plugin import MixinPlugin


def user_delete(context, data_dict=None):
    """
    :param context:
    :return: True if user is sysadmin or admin in top level org
    """
    return check_access_account_requests(context)


def check_access_account_requests(context, data_dict=None):
    """
    :param context:
    :return: True if user is sysadmin or admin in top level org
    """
    user = context.get("user")
    orgs = model.Group.get_top_level_groups(type="organization")
    user_is_admin_in_top_org = None
    if orgs:
        for org in orgs:
            if authz.has_user_permission_for_group_or_org(org.id, user, "admin"):
                user_is_admin_in_top_org = True
                break

    return {
        "success": True
        if user_is_admin_in_top_org or h.check_access("sysadmin")
        else False
    }


@tk.auth_allow_anonymous_access
def request_reset(context, data_dict=None):
    if tk.request.method == "POST":
        context = {"model": model, "ignore_auth": True}
        data_dict = {"id": tk.request.form.get("user")}
        try:
            user_dict = tk.get_action("user_show")(context, data_dict)
        except tk.ObjectNotFound:
            return {"success": True}
        if user_dict["state"] == "pending":
            return {"success": False}
    return {"success": True}


class AccessRequestsPlugin(MixinPlugin, plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "../templates")
        tk.add_resource("../fanstatic", "accessrequests")
        if tk.check_ckan_version(min_version="2.9.0"):
            mappings = config_.get("ckan.legacy_route_mappings", {})
            if isinstance(mappings, string_types):
                mappings = json.loads(mappings)

            bp_routes = []
            mappings.update(
                {
                    "account_requests": "accessrequests.account_requests",
                    "request_account": "accessrequests.request_account",
                    "account_requests_management": "accessrequests.account_requests_management",
                }
            )
            # https://github.com/ckan/ckan/pull/4521
            config_["ckan.legacy_route_mappings"] = json.dumps(mappings)

    def get_auth_functions(self):
        return {
            "request_reset": request_reset,
            "check_access_account_requests": check_access_account_requests,
            "user_delete": user_delete,
        }
