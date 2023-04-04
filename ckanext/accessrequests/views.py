# -*- coding: utf-8 -*-

from flask import Blueprint
from six import text_type

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, g, request
from ckan.views.user import PerformResetView

import ckanext.accessrequests.utils as utils

accessrequests = Blueprint("accessrequests", __name__)


def get_blueprints():
    return [accessrequests]


def account_requests():
    return utils.account_requests()


def request_account(data=None, errors=None, error_summary=None):
    return utils.request_account(data, errors, error_summary)


def account_requests_management():
    return utils.account_requests_management()


class AccessRequestPerformResetView(PerformResetView):
    def post(self, id):
        context, user_dict = self._prepare(id)
        context["reset_password"] = True
        user_state = user_dict["state"]
        try:
            new_password = self._get_form_password()
            user_dict["password"] = new_password
            username = request.form.get("name")
            if username is not None and username != "":
                user_dict["name"] = username
            user_dict["reset_key"] = g.reset_key

            ## EXTRA FOR CHECKING IF USER ALREADY APPROVED AND INVITED
            approved_users = [
                i for i in utils._approved_users() if user_dict["id"] == i.object_id
            ]

            if user_state == "pending" and not approved_users:
                user_dict["state"] = user_state
                h.flash_error(
                    _(
                        "You cannot update your password while your account is in process of approval."
                    )
                )
                return h.redirect_to("home.index")
            else:
                user_dict["state"] = model.State.ACTIVE
                logic.get_action("user_update")(context, user_dict)
                mailer.create_reset_key(context["user_obj"])

                h.flash_success(_("Your password has been reset."))
                return h.redirect_to("home.index")
        except logic.NotAuthorized:
            h.flash_error(_("Unauthorized to edit user %s") % id)
        except logic.NotFound:
            h.flash_error(_("User not found"))
        except dictization_functions.DataError:
            h.flash_error(_("Integrity Error"))
        except logic.ValidationError as e:
            h.flash_error("%r" % e.error_dict)
        except ValueError as e:
            h.flash_error(text_type(e))
        user_dict["state"] = user_state
        return base.render("user/perform_reset.html", {"user_dict": user_dict})


accessrequests.add_url_rule("/user/account_requests", view_func=account_requests)
accessrequests.add_url_rule(
    "/user/register", view_func=request_account, methods=("POST", "GET")
)
accessrequests.add_url_rule(
    "/user/account_requests_management",
    view_func=account_requests_management,
    methods=("POST", "GET"),
)

accessrequests.add_url_rule(
    "/user/reset/<id>",
    view_func=AccessRequestPerformResetView.as_view(str("perform_reset")),
)
