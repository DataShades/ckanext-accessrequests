import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from routes.mapper import SubMapper
import ckan.model as model
import ckan.logic as logic
from ckan.common import c, request, _
from ckan.lib.activity_streams import activity_stream_string_functions
get_action = logic.get_action

def activity_stream_string_reject_new_user(context, activity):
    return _("{actor} reject new user {user}")

def activity_stream_string_approve_new_user(context, activity):
    return _("{actor} approve new user {user}")

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
                      '/admin/account_requests',
                      action='account_requests')
            m.connect('request_account',
                      '/user/register',
                      action='request_account')
            m.connect('account_requests_management',
                      '/admin/account_requests_management',
                      action='account_requests_management')
        return map

    def after_map(self, map):
        return map

    def get_auth_functions(self):
        return {'request_reset': request_reset}



