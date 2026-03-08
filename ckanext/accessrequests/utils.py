from __future__ import annotations

import binascii
import logging
import os
from typing import Any

import ckan.lib.captcha as captcha
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.logic.schema as schema
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan import types

from ckanext.activity.logic.validators import object_id_validators
from ckanext.activity.model.activity import Activity

log = logging.getLogger(__name__)


role_labels = {
    "editor": "Standard Editor",
    "member": "Standard Member",
    "admin": "Request to be Admin",
    "creator": "Creator",
}


def request_account(
    data: dict[str, Any] | None = None,
    errors: dict[str, Any] | None = None,
    error_summary: dict[str, Any] | None = None,
):
    """GET to display a form for requesting a user account or POST the
    form data to submit the request.
    """
    params = tk.request.form

    if "save" in params and not data:
        return _save_new_pending(params)

    if tk.current_user.is_authenticated and not data:
        # Don't offer the registration form if already logged in
        return tk.render("user/logout_first.html")

    data = data or {}
    errors = errors or {}
    error_summary = error_summary or {}
    organization, roles = _get_orgs_and_roles()
    vars = {
        "data": data,
        "errors": errors,
        "error_summary": error_summary,
        "organization": organization,
        "roles": roles,
        "allow_no_org": tk.asbool(
            tk.config.get("ckanext.accessrequests.allow_no_org", True)
        ),
    }

    return tk.render(
        "user/new.html",
        extra_vars={
            "form": tk.render("user/new_user_form.html", extra_vars=vars),
        },
    )


def _save_new_pending(params: dict[str, Any]) -> types.Response | str:
    errors = {}
    error_summary = {}
    password = str(binascii.b2a_hex(os.urandom(15)))
    data = {
        "fullname": params["fullname"],
        "name": params["name"],
        "password1": password,
        "password2": password,
        "state": model.State.PENDING,
        "email": params["email"],
        "organization_request": params["organization-for-request"],
        "reason_to_access": params["reason-to-access"],
        "role": params["role"],
    }

    try:
        captcha.check_recaptcha(tk.request)
        context = types.Context(
            {"schema": schema.user_new_form_schema(), "ignore_auth": True}
        )
        user_dict = tk.get_action("user_create")(context, data)
        if params["organization-for-request"]:
            organization = model.Group.get(data["organization_request"])
            sys_admin = tk.get_action("get_site_user")({"ignore_auth": True}, {})

            tk.get_action("organization_member_create")(
                {"user": sys_admin["name"]},
                {
                    "id": organization.id if organization else None,
                    "username": user_dict["name"],
                    "role": data["role"] if data["role"] else "member",
                },
            )
            role = data["role"].title() if data["role"] else "Member"
        else:
            organization = None
            role = None

        msg = (
            "A request for a new user account has been submitted:"
            "\nUsername: {}"
            "\nName: {}\nEmail: {}\nOrganisation: {}\nRole: {}"
            "\nReason for access: {}"
            "\nThis request can be approved or rejected at {}"
        ).format(
            data["name"],
            data["fullname"],
            data["email"],
            organization.display_name if organization else None,
            role if organization else None,
            data["reason_to_access"],
            h.url_for("accessrequests.account_requests", qualified=True),
        )
        list_admin_emails = tk.aslist(
            tk.config.get("ckanext.accessrequests.approver_email")
        )
        for admin_email in list_admin_emails:
            try:
                mailer.mail_recipient("Admin", admin_email, "Account request", msg)
            except mailer.MailerException as e:
                h.flash_error(f"Email error: {e}")
        h.flash_success(
            "Your request for access to the {0} has been submitted.".format(
                tk.config.get("ckan.site_title")
            )
        )
    except tk.ValidationError as e:
        # return validation failures to the form
        if e.error_dict:
            errors = e.error_dict
            error_summary = e.error_summary
        return request_account(data, errors, error_summary)
    except captcha.CaptchaError:
        errors["Captcha"] = [tk._("Bad Captcha. Please try again.")]
        error_summary["Captcha"] = "Bad Captcha. Please try again."
        return request_account(data, errors, error_summary)

    return h.redirect_to("/")


def _get_orgs_and_roles():
    """Return a list of orgs and roles"""
    organizations = tk.get_action("organization_list")({}, {})
    organization: list[dict[str, Any]] = []
    for org in organizations:
        organization.append(
            tk.get_action("organization_show")(
                {},
                {
                    "id": org,
                    "include_extras": False,
                    "include_users": False,
                    "include_groups": False,
                    "include_tags": False,
                    "include_followers": False,
                },
            )
        )
    roles = tk.get_action("member_roles_list")({}, {"group_type": "organization"})
    role_order = ("editor", "member", "admin", "")
    roles = sorted(
        [r for r in roles if r["value"] not in ("creator", "downloader")],
        key=lambda role: role_order.index(role["value"]),
    )
    roles.append({"text": "I'm not sure!", "value": ""})

    for role in roles:
        role["text"] = role_labels.get(role["value"], role["text"])

    return organization, roles


def _not_approved():
    """Return a True if user not approved"""
    approved_users = _approved_users()
    approved_users_id: list[str] = []
    for user in approved_users:
        approved_users_id.append(user.object_id)
    return approved_users_id


def _approved_users():
    approved_users = (
        model.Session.query(Activity)
        .filter(Activity.activity_type == "approve new user")
        .all()
    )
    return approved_users


def _all_account_requests():
    """Return a list of all pending user accounts"""
    # TODO: stop this returning invited users also
    return (
        model.Session.query(model.User, model.Member, model.Group.is_organization)
        .outerjoin(model.Member, model.Member.table_id == model.User.id)
        .outerjoin(model.Group, model.Member.group_id == model.Group.id)
        .filter(model.User.state == "pending")
        .all()
    )


def account_requests():
    organization, roles = _get_orgs_and_roles()
    try:
        tk.check_access("check_access_account_requests", {})
    except tk.NotAuthorized:
        return tk.abort(
            401,
            "Need to be system administrator or admin in top-level org to administer",
        )
    not_approved_users = _not_approved()
    accounts = [
        {
            "id": user.id,
            "name": user.display_name,
            "username": user.name,
            "email": user.email,
            "org": member,
            "is_org": is_org,
        }
        for user, member, is_org in _all_account_requests()
        if user.id not in not_approved_users
    ]
    return tk.render(
        "user/account_requests.html",
        {
            "accounts": accounts,
            "organization": organization,
            "roles": roles,
            "allow_no_org": tk.asbool(
                tk.config.get("ckanext.accessrequests.allow_no_org", True)
            ),
        },
    )


def _assign_user_to_org(user_id: str, user_org: str, user_role: str):
    if not user_org:
        return (None, None)
    org_role = user_role if user_role else "member"
    org = (
        model.Session.query(model.Member)
        .filter(model.Member.table_id == user_id)
        .first()
    )
    if org and org.group.id != user_org:
        tk.get_action("organization_member_delete")(
            {}, {"id": org.group.id, "username": user_id}
        )
    org = tk.get_action("organization_member_create")(
        {}, {"id": user_org, "username": user_id, "role": org_role}
    )
    org_new = model.Group.get(org["group_id"])
    return (org_new.title if org_new else None, org_role.title() if user_org else None)


def account_requests_management():
    """Approve or reject an account request"""
    params = tk.request.form
    action = params["action"]
    user_id = params["id"]
    user_name = params["name"]
    user = model.User.get(user_id)

    user = tk.current_user  # pyright: ignore[reportUnknownVariableType]

    if not isinstance(user, model.User):
        raise tk.NotAuthorized

    activity_dict = {"user_id": user.id, "object_id": user_id}
    list_admin_emails = tk.aslist(
        tk.config.get("ckanext.accessrequests.approver_email")
    )
    if action == "forbid":
        object_id_validators["reject new user"] = "user_id_exists"
        activity_dict["activity_type"] = "reject new user"
        tk.get_action("activity_create")(
            {"defer_commit": True, "ignore_auth": True}, activity_dict
        )
        org = tk.get_action("organization_list_for_user")(
            {"user": user_name}, {"permission": "read"}
        )
        if org:
            tk.get_action("organization_member_delete")(
                {}, {"id": org[0]["id"], "username": user_name}
            )
        tk.get_action("user_delete")({}, {"id": user_id})
        msg = (
            "Your account request for {0} has been rejected by {1}"
            "\n\nFor further clarification "
            "as to why your request has been "
            "rejected please contact the NSW Flood Data Portal ({2})"
        )
        try:
            mailer.mail_recipient(
                user.display_name,
                user.email or "",
                "Account request",
                msg.format(
                    tk.config.get("ckan.site_title"),
                    user.fullname,
                    user.email,
                ),
            )
        except Exception as e:
            log.error("Error emailing invite to user: %s", e)

        msg = ("User account request for {0} has been rejected by {1}").format(
            user.fullname or user_name, user.fullname
        )
        for admin_email in list_admin_emails:
            try:
                mailer.mail_recipient(
                    "Admin", admin_email, "Account request feedback", msg
                )
            except mailer.MailerException as e:
                h.flash_error(f"Email error: {e}")
    elif action == "approve":
        user_org = params["org"]
        user_role = params["role"]
        object_id_validators["approve new user"] = "user_id_exists"
        activity_dict["activity_type"] = "approve new user"
        tk.get_action("activity_create")(
            {"defer_commit": True, "ignore_auth": True}, activity_dict
        )
        org_display_name, org_role = _assign_user_to_org(
            user_id,
            user_org,
            user_role,
        )
        # Send invitation to complete registration
        msg = (
            "User account request for {0} "
            "(Organization : {1}, Role: {2}) "
            "has been approved by {3}"
        ).format(
            user.fullname or user_name,
            org_display_name,
            org_role,
            user.fullname,
        )

        for admin_email in list_admin_emails:
            try:
                mailer.mail_recipient(
                    "Admin", admin_email, "Account request feedback", msg
                )
            except mailer.MailerException as e:
                h.flash_error(f"Email error: {e}")
        try:
            org_dict = tk.get_action("organization_show")({}, {"id": user_org})
        except tk.ObjectNotFound:
            org_dict = None

        user.name = user.name
        try:
            mailer.send_invite(user, org_dict, user_role)
        except Exception as e:
            log.error("Error emailing invite to user: %s", e)

    return tk.render("user/account_requests_management.html")
