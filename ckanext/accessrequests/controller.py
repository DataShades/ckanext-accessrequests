from ckan.common import c, response, request, g
from ckan.controllers.user import UserController
import binascii
import ckan.authz as authz
import ckan.model as model
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.logic as logic
import logging
import os
import random
from pylons import config
from ckan.logic.validators import (object_id_validators, user_id_exists)
from plugin import check_access_account_requests
import sqlalchemy
import ckan.lib.captcha as captcha

#from model import UserTitle

log = logging.getLogger(__name__)

abort = base.abort
render = base.render
_ = base._

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
CaptchaError = captcha.CaptchaError
CaptchaError.error_dict = {}
CaptchaError.error_summary = {}

def get_orgs_and_roles(context):
    '''Return a list of orgs and roles
    '''
    organizations = logic.get_action('organization_list')({}, {})
    organization = []
    for org in organizations:
      organization.append(logic.get_action('organization_show')({},{'id': org,
                                                                    'include_extras': False,
                                                                    'include_users': False,
                                                                    'include_groups': False,
                                                                    'include_tags': False,
                                                                    'include_followers': False
                                                                     }))
    roles = logic.get_action('member_roles_list')(context, {'group_type': 'organization'})
    return organization, roles

def assign_user_to_org(user_id, user_org, user_role, context):
    org = model.Session.query(model.Member).\
                             filter(model.Member.table_id==user_id).\
                             first()
    if org and org.group.id != user_org:
        logic.get_action('organization_member_delete')(context, {"id": org.group.id, "username": user_id})
    org = logic.get_action('organization_member_create')(context, {
                                                    "id": user_org,
                                                    "username": user_id,
                                                    "role": user_role})
    group_new = model.Group.get(org['group_id'])
    return group_new.title if org else None

def all_account_requests():
    '''Return a list of all pending user accounts
    '''
    # TODO: stop this returning invited users also
    return model.Session.query(model.User, model.Member).\
                                 outerjoin(model.Member, model.Member.table_id == model.User.id).\
                                 filter(model.User.state=='pending').\
                                 all()

def not_approved():
    '''Return a True if user not approved
    '''
    approved_users = model.Session.query(model.Activity).filter(model.Activity.activity_type=='approve new user').all()
    approved_users_id = []
    for user in approved_users:
        approved_users_id.append(user.object_id)
    return approved_users_id


class AccessRequestsController(UserController):

    def request_account(self, data=None, errors=None, error_summary=None):
        '''GET to display a form for requesting a user account or POST the
           form data to submit the request.
        '''
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user or c.author,
            # why?
            #'user': model.Session.query(model.User).filter_by(sysadmin=True).first().name,
            'auth_user_obj': c.userobj,
            'schema': self._new_form_to_db_schema(),
            'save': 'save' in request.params
        }
        if context['save'] and not data:
            return self._save_new_pending(context)

        if c.user and not data:
            # Don't offer the registration form if already logged in
            return render('user/logout_first.html')

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        organization, roles = get_orgs_and_roles(context)
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'organization': organization, 'roles': roles}

        c.is_sysadmin = authz.is_sysadmin(c.user)
        c.form = render(self.new_user_form, extra_vars=vars)
        return render('user/new.html')

    def _save_new_pending(self, context):
        errors = {}
        error_summary = {}
        params = request.params
        password = str(binascii.b2a_hex(os.urandom(15)))
        data = dict(
            fullname = params['fullname'],
            name = params['name'],
            password1 = password,
            password2 = password,
            state = model.State.PENDING,
            email = params['email'],
            organization_request = params['organization-for-request'],
            reason_to_access = params['reason-to-access'],
            role = params['role']
            )
        organization = model.Group.get(data['organization_request'])
        sys_admin = model.Session.query(model.User).filter(sqlalchemy.and_(model.User.sysadmin == True, model.User.state == 'active')).first().name
        try:
            captcha.check_recaptcha(request)
            user_dict = logic.get_action('user_create')(context, data)
            org_member = logic.get_action('organization_member_create')({"user": sys_admin}, {
                                                                        "id": organization.id,
                                                                        "username": user_dict['name'],
                                                                        "role": data['role']})
            msg = "A request for a new user account has been submitted:\nUsername: " + data['name'] + "\nName: " + data['fullname'] + "\nEmail: " + data['email'] + "\nOrganisation: " + organization.display_name + "\nReason for access: " + data['reason_to_access'] + "\n\nThis request can be approved or rejected at " + g.site_url + h.url_for(controller='ckanext.accessrequests.controller:AccessRequestsController', action='account_requests')
            mailer.mail_recipient('Admin', config.get('ckanext.accessrequests.approver_email'), 'Account request', msg)
            h.flash_success('Your request for access to the {0} has been submitted.'.format(config.get('ckan.site_title')))
        except (ValidationError,CaptchaError), e:
            # return validation failures to the form
            if e.error_dict:
                errors = e.error_dict
                error_summary = e.error_summary
            errors['Captcha'] = [_(u'Bad Captcha. Please try again.')]
            error_summary['Captcha'] = 'Bad Captcha. Please try again.'
            return self.request_account(data, errors, error_summary)

        # TODO: turn into a template
        # msg = "New account's request:\nUsername: {name}\nEmail: {email}\nAgency: {agency}\nRole: {role}\nNotes: {notes}".format(**params)

        # redirect to confirmation page/display success flash message
        h.redirect_to('/')

    def account_requests(self):
        ''' /ckan-admin/account_requests rendering
        '''
        context = {
            'model': model,
            'user': c.user,
            'auth_user_obj': c.userobj,
        }
        organization, roles = get_orgs_and_roles(context)
        has_access = check_access_account_requests(context)
        if not has_access['success']:
            base.abort(401, _('Need to be system administrator or admin in top-level org to administer'))
        not_approved_users = not_approved()
        accounts = [{
            'id': user.id,
            'name': user.display_name,
            'username': user.name,
            'email': user.email,
            'org': member,
        } for user, member in all_account_requests() if user.id not in not_approved_users]
        return render('user/account_requests.html', {'accounts': accounts, 'organization': organization, 'roles': roles})

    def account_requests_management(self):
        ''' Approve or reject an account request
        '''
        action = request.params['action']
        user_id = request.params['id']
        user_name = request.params['name']
        user = model.User.get(user_id)

        context = {
            'model': model,
            'user': c.user,
            'session': model.Session,
        }
        activity_create_context = {
            'model': model,
            'user': user_name,
            'defer_commit': True,
            'ignore_auth': True,
            'session': model.Session
        }
        activity_dict = {
            'user_id': c.userobj.id,
            'object_id': user_id
        }
        if action == 'forbid':
            object_id_validators['reject new user'] = user_id_exists
            activity_dict['activity_type'] = 'reject new user'
            logic.get_action('activity_create')(activity_create_context, activity_dict)
            org = logic.get_action('organization_list_for_user')({'user': user_name}, {"permission": "read"})
            if org:
                logic.get_action('organization_member_delete')(context, {"id": org[0]['id'], "username": user_name})
            logic.get_action('user_delete')(context, {'id':user_id})
            msg = "Your account request for {0} has been rejected by {1}\n\nFor further clarification as to why your request has been rejected please contact the NSW Flood Data Portal ({2})".format(config.get('ckan.site_title'), c.userobj.fullname, config.get('ckanext.accessrequests.approver_email'))
            mailer.mail_recipient(user.fullname, user.email, 'Account request', msg)
            msg = "User account request for {0} has been rejected by {1}".format(user.fullname or user_name, c.userobj.fullname)
            mailer.mail_recipient('Admin', config.get('ckanext.accessrequests.approver_email'), 'Account request feedback', msg)
        elif action == 'approve':
            user_org = request.params['org']
            user_role = request.params['role']
            object_id_validators['approve new user'] = user_id_exists
            activity_dict['activity_type'] = 'approve new user'
            logic.get_action('activity_create')(activity_create_context, activity_dict)
            org_display_name = assign_user_to_org(user_id, user_org, user_role, context)
            # Send invitation to complete registration
            msg = "User account request for {0} (Organization : {1}, Role: {2}) has been approved by {3}".format(user.fullname, org_display_name, user_role.title(), c.userobj.fullname)
            mailer.mail_recipient('Admin', config.get('ckanext.accessrequests.approver_email'), 'Account request feedback', msg)
            try:
                mailer.send_invite(user)
            except Exception as e:
                log.error('Error emailing invite to user: %s', e)
                abort(500, _('Error: couldn''t email invite to user'))

        response.status = 200
        return render('user/account_requests_management.html')
