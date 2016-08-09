import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from routes.mapper import SubMapper
import ckan.model as model
import ckan.logic as logic
from ckan.common import c, request, _
from ckan.lib.activity_streams import activity_stream_string_functions
get_action = logic.get_action
import ckan.lib.helpers as h
import ckan.authz as authz


def activity_stream_string_reject_new_user(context, activity):
    return _("{actor} rejected new user {user}")

def activity_stream_string_approve_new_user(context, activity):
    return _("{actor} approved new user {user}")

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
  user = context.get('user')
  orgs = model.Group.get_top_level_groups(type='organization')
  user_is_admin_in_top_org = None
  if orgs:
    for org in orgs:
        if authz.has_user_permission_for_group_or_org(org.id, user, 'admin'):
            user_is_admin_in_top_org = True
            break

  return {'success': True if user_is_admin_in_top_org or h.check_access('sysadmin') else False}

@toolkit.auth_allow_anonymous_access
def request_reset(context, data_dict=None):
    if request.method == 'POST':
        context = {'model': model,
                   'user': c.user}
        data_dict = {'id': request.params.get('user')}
        user_dict = get_action('user_show')(context, data_dict)
        if user_dict['state'] == 'pending':
            return {'success': False}
    return {'success': True}


class AccessRequestsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IAuthFunctions)


    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'accessrequests')
        activity_stream_string_functions['reject new user'] = activity_stream_string_reject_new_user
        activity_stream_string_functions['approve new user'] = activity_stream_string_approve_new_user

    def before_map(self, map):
        with SubMapper(map,
                       controller='ckanext.accessrequests.controller:AccessRequestsController') as m:
            m.connect('account_requests',
                      '/user/account_requests',
                      action='account_requests')
            m.connect('request_account',
                      '/user/register',
                      action='request_account')
            m.connect('account_requests_management',
                      '/user/account_requests_management',
                      action='account_requests_management')
        return map

    def after_map(self, map):
        return map

    def get_auth_functions(self):
        return {'request_reset': request_reset,
                'check_access_account_requests': check_access_account_requests,
                'user_delete': user_delete}
