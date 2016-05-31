from ckan.common import c, response, request
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

#from model import UserTitle

log = logging.getLogger(__name__)

abort = base.abort
render = base.render

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError


def all_account_requests():
    '''Return a list of all pending user accounts
    '''
    # TODO: stop this returning invited users also
    return model.Session.query(model.User).filter(model.User.state=='pending').all()

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
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        c.is_sysadmin = authz.is_sysadmin(c.user)
        c.form = render(self.new_user_form, extra_vars=vars)
        log.info('I got here!')
        return render('user/new.html')

    def _save_new_pending(self, context):
        params = request.params
        password = str(binascii.b2a_hex(os.urandom(15)))
        log.debug('password = %s' % password)
        data = dict(
            fullname = params['fullname'],
            name = params['name'],
            password1 = password,
            password2 = password,
            state = model.State.PENDING,
            email = params['email']
            )
        try:
            user_dict = logic.get_action('user_create')(context, data)
        except ValidationError, e:
            # return validation failures to the form
            errors = e.error_dict
            error_summary = e.error_summary
            return self.request_account(data, errors, error_summary)

        # TODO: turn into a template
        #msg = "New account's request:\nUsername: {name}\nEmail: {email}\nAgency: {agency}\nRole: {role}\nNotes: {notes}".format(**params)
        #mailer.mail_recipient('Admin', params['admin'], 'Account request', msg)

        # redirect to confirmation page/display success flash message
        h.redirect_to('/')


    def account_requests(self):
        ''' /ckan-admin/account_requests rendering
        '''
        accounts = [{
            'id':user.id,
            'name':user.display_name,
            'email': user.email,
        } for user in all_account_requests()]
        return render('admin/account_requests.html', {'accounts': accounts})


    def account_requests_management(self):
        ''' Approve or reject an account request
        '''
        action = request.params['action']
        user_id = request.params['id']
        user = model.User.get(user_id)

        context = {
            'model': model,
            'session': model.Session,
        } 

        if action == 'forbid':
            # remove user
            logic.get_action('user_delete')(context, {'id':user_id})

            # TODO: notify user

        elif action == 'approve':
            # Send invitation to complete registration
            try:
                mailer.send_invite(user)
            except Exception as e:
                log.error('Error emailing invite to user: %s', e)
                abort(500, _('Error: couldn''t email invite to user'))

        response.status = 200
