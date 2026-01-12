from __future__ import annotations

from typing import Any
import ckan.plugins.toolkit as tk
from ckan.common import CKANConfig
import ckan.authz as authz
import ckan.lib.helpers as h
import ckan.plugins as plugins
import ckanext.accessrequests.views as views

from ckan import types, model


def user_delete(context: types.Context, data_dict: dict[str, Any] | None = None):
    """
    :param context:
    :return: True if user is sysadmin or admin in top level org
    """
    return check_access_account_requests(context)


def check_access_account_requests(
    context: types.Context, data_dict: dict[str, Any] | None = None
):
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
def request_reset(context: types.Context, data_dict: dict[str, Any] | None = None):
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


class AccessRequestsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()

    # IConfigurer

    def update_config(self, config: CKANConfig):
        tk.add_template_directory(config, "templates")
        tk.add_resource("fanstatic", "accessrequests")

    def get_auth_functions(self):
        return {
            "request_reset": request_reset,
            "check_access_account_requests": check_access_account_requests,
            "user_delete": user_delete,
        }
