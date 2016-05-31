import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from routes.mapper import SubMapper


class AccessRequestsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'accessrequests')

    def before_map(self, map):
        with SubMapper(map,
                       controller='ckanext.accessrequests.controller:AccessRequestsController') as m:
            m.connect('account_requests',
                      '/ckan-admin/account_requests',
                      action='account_requests')
            m.connect('request_account',
                      '/user/register',
                      action='request_account')
            m.connect('account_requests_management',
                      '/ckan-admin/account_requests_management',
                      action='account_requests_management')
        return map

    def after_map(self, map):
        return map
