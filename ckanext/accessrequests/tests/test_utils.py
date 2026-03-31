from types import SimpleNamespace
from unittest import mock

import pytest

from ckan.tests import factories

import ckanext.accessrequests.utils as utils


@pytest.mark.ckan_config("ckan.plugins", "accessrequests")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestAccountRequestsManagement:
    def _run_account_requests_management(self, monkeypatch, action):
        requested_user = factories.User.model()
        moderator = factories.Sysadmin.model()

        monkeypatch.setattr(
            utils.tk,
            "request",
            SimpleNamespace(
                form={
                    "action": action,
                    "id": requested_user.id,
                    "name": requested_user.name,
                    "org": "",
                    "role": "member",
                }
            ),
        )
        monkeypatch.setattr(utils.tk, "current_user", moderator)
        monkeypatch.setattr(utils.tk, "render", lambda template: template)
        monkeypatch.setattr(utils.tk, "aslist", lambda value: [])
        monkeypatch.setattr(
            utils,
            "_assign_user_to_org",
            lambda user_id, user_org, user_role: (None, None),
        )

        def get_action(name):
            actions = {
                "activity_create": lambda *args, **kwargs: None,
                "organization_show": lambda *args, **kwargs: None,
                "organization_list_for_user": lambda *args, **kwargs: [],
                "organization_member_delete": lambda *args, **kwargs: None,
                "user_delete": lambda *args, **kwargs: None,
            }
            return actions[name]

        monkeypatch.setattr(utils.tk, "get_action", get_action)

        send_invite = mock.Mock()
        mail_recipient = mock.Mock()
        monkeypatch.setattr(utils.mailer, "send_invite", send_invite)
        monkeypatch.setattr(utils.mailer, "mail_recipient", mail_recipient)

        utils.account_requests_management()

        return requested_user, moderator, send_invite, mail_recipient

    @pytest.mark.parametrize("action", ["approve", "forbid"])
    def test_notifies_requested_user_not_moderator(self, monkeypatch, action):
        requested_user, moderator, send_invite, mail_recipient = (
            self._run_account_requests_management(monkeypatch, action)
        )

        if action == "approve":
            assert send_invite.called
            assert send_invite.call_args[0][0].id == requested_user.id
            assert not mail_recipient.called
        else:
            assert not send_invite.called
            assert mail_recipient.called
            assert mail_recipient.call_args[0][0] == requested_user.display_name
            assert mail_recipient.call_args[0][1] == (requested_user.email or "")
            assert mail_recipient.call_args[0][2] == "Account request"
            assert moderator.fullname in mail_recipient.call_args[0][3]
