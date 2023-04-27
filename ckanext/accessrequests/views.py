# -*- coding: utf-8 -*-

from flask import Blueprint
from six import text_type

from ckan.views.user import PerformResetView
import ckan.logic as logic
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.lib.navl.dictization_functions as dictization_functions
from ckan.common import _, g, request
import ckan.lib.mailer as mailer
import ckan.model as model

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


class AccessRequestPerformResetView(PerformResetView):
    def post(self, id):
        context, user_dict = self._prepare(id)
        context[u'reset_password'] = True
        user_state = user_dict[u'state']
        try:
            new_password = self._get_form_password()
            user_dict[u'password'] = new_password
            username = request.form.get(u'name')
            if (username is not None and username != u''):
                user_dict[u'name'] = username
            user_dict[u'reset_key'] = g.reset_key

            ## EXTRA FOR CHECKING IF USER ALREADY APPROVED AND INVITED
            approved_users = [
                i for i in utils._approved_users() if user_dict['id'] == i.object_id
            ]

            if user_state == 'pending' and not approved_users:
                user_dict[u'state'] = user_state
                h.flash_error(_(u'You cannot update your password while your account is in process of approval.'))
                return h.redirect_to(u'home.index')
            else:
                user_dict[u'state'] = model.State.ACTIVE
                logic.get_action(u'user_update')(dict(context, ignore_auth=True), user_dict)
                mailer.create_reset_key(context[u'user_obj'])

                h.flash_success(_(u'Your password has been reset.'))
                return h.redirect_to(u'home.index')
        except logic.NotAuthorized:
            h.flash_error(_(u'Unauthorized to edit user %s') % id)
        except logic.NotFound:
            h.flash_error(_(u'User not found'))
        except dictization_functions.DataError:
            h.flash_error(_(u'Integrity Error'))
        except logic.ValidationError as e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError as e:
            h.flash_error(text_type(e))
        user_dict[u'state'] = user_state
        return base.render(u'user/perform_reset.html', {
            u'user_dict': user_dict
        })

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

accessrequests.add_url_rule(
    u'/user/reset/<id>', view_func=AccessRequestPerformResetView.as_view(str(u'perform_reset')))
