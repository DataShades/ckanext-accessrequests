# -*- coding: utf-8 -*-
import binascii
import logging
import os

import ckantoolkit as tk
import sqlalchemy

import ckan.authz as authz
import ckan.lib.captcha as captcha
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.logic.schema as schema
import ckan.model as model

from ckanext.activity.logic.validators import object_id_validators
from ckanext.activity.model.activity import Activity

log = logging.getLogger(__name__)

_ = tk._
c = tk.c
request = tk.request
render = tk.render
config = tk.config

role_labels = {
    "editor": "Standard Editor",
    "member": "Standard Member",
    "admin": "Request to be Admin",
    "creator": "Creator",
}


def request_account(data=None, errors=None, error_summary=None):
    """GET to display a form for requesting a user account or POST the
    form data to submit the request.
    """
    params = request.form if tk.check_ckan_version("2.9") else request.params
    context = {
        "model": model,
        "session": model.Session,
        "user": c.user or c.author,
        "auth_user_obj": c.userobj,
        "schema": schema.user_new_form_schema(),
        "save": "save" in params,
    }
    if context["save"] and not data:
        return _save_new_pending(context)

    if c.user and not data:
        # Don't offer the registration form if already logged in
        return render("user/logout_first.html")

    data = data or {}
    errors = errors or {}
    error_summary = error_summary or {}
    organization, roles = _get_orgs_and_roles(context)
    vars = {
        "data": data,
        "errors": errors,
        "error_summary": error_summary,
        "organization": organization,
        "roles": roles,
        "allow_no_org": tk.asbool(
            config.get("ckanext.accessrequests.allow_no_org", True)
        ),
    }

    c.is_sysadmin = authz.is_sysadmin(c.user)
    c.form = render("user/new_user_form.html", extra_vars=vars)

    return render(
        "user/new.html",
        extra_vars={
            "form": c.form,
        },
    )


def _save_new_pending(context):
    errors = {}
    error_summary = {}
    params = request.form if tk.check_ckan_version("2.9") else request.params
    password = str(binascii.b2a_hex(os.urandom(15)))
    data = dict(
        fullname=params["fullname"],
        name=params["name"],
        password1=password,
        password2=password,
        state=model.State.PENDING,
        email=params["email"],
        organization_request=params["organization-for-request"],
        reason_to_access=params["reason-to-access"],
        role=params["role"],
    )

    try:
        captcha.check_recaptcha(request)
        user_dict = tk.get_action("user_create")(dict(context, ignore_auth=True), data)
        if params["organization-for-request"]:
            organization = model.Group.get(data["organization_request"])
            sys_admin = (
                model.Session.query(model.User)
                .filter(
                    sqlalchemy.and_(
                        model.User.sysadmin == True,  # noqa
                        model.User.state == "active",
                    )
                )
                .first()
                .name
            )
            tk.get_action("organization_member_create")(
                {"user": sys_admin},
                {
                    "id": organization.id,
                    "username": user_dict["name"],
                    "role": data["role"] if data["role"] else "member",
                },
            )
            role = data["role"].title() if data["role"] else "Member"
        else:
            organization = None
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
            config.get("ckanext.accessrequests.approver_email")
        )
        for admin_email in list_admin_emails:
            try:
                mailer.mail_recipient("Admin", admin_email, "Account request", msg)
            except mailer.MailerException as e:
                h.flash_error(f"Email error: {e}")
        h.flash_success(
            "Your request for access to the {0} has been submitted.".format(
                config.get("ckan.site_title")
            )
        )
    except tk.ValidationError as e:
        # return validation failures to the form
        if e.error_dict:
            errors = e.error_dict
            error_summary = e.error_summary
        return request_account(data, errors, error_summary)
    except captcha.CaptchaError:
        errors["Captcha"] = [_("Bad Captcha. Please try again.")]
        error_summary["Captcha"] = "Bad Captcha. Please try again."
        return request_account(data, errors, error_summary)

    return h.redirect_to("/")


def _get_orgs_and_roles(context):
    """Return a list of orgs and roles"""
    organizations = tk.get_action("organization_list")({}, {})
    organization = []
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
    roles = tk.get_action("member_roles_list")(context, {"group_type": "organization"})
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
    approved_users_id = []
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
    from ckanext.accessrequests.plugin import check_access_account_requests

    context = {
        "model": model,
        "user": c.user,
        "auth_user_obj": c.userobj,
    }
    organization, roles = _get_orgs_and_roles(context)
    has_access = check_access_account_requests(context)
    if not has_access["success"]:
        return tk.abort(
            401,
            _(
                "Need to be system administrator or admin "
                "in top-level org to administer"
            ),
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
    return render(
        "user/account_requests.html",
        {
            "accounts": accounts,
            "organization": organization,
            "roles": roles,
            "allow_no_org": tk.asbool(
                config.get("ckanext.accessrequests.allow_no_org", True)
            ),
        },
    )


def _assign_user_to_org(user_id, user_org, user_role, context):
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
            context, {"id": org.group.id, "username": user_id}
        )
    org = tk.get_action("organization_member_create")(
        context, {"id": user_org, "username": user_id, "role": org_role}
    )
    org_new = model.Group.get(org["group_id"])
    return (org_new.title, org_role.title() if user_org else None)


def account_requests_management():
    """Approve or reject an account request"""
    params = request.form if tk.check_ckan_version("2.9") else request.params
    action = params["action"]
    user_id = params["id"]
    user_name = params["name"]
    user = model.User.get(user_id)

    context = {
        "model": model,
        "user": c.user,
        "session": model.Session,
    }
    activity_create_context = {
        "model": model,
        "user": user_name,
        "defer_commit": True,
        "ignore_auth": True,
        "session": model.Session,
    }
    activity_dict = {"user_id": c.userobj.id, "object_id": user_id}
    list_admin_emails = tk.aslist(config.get("ckanext.accessrequests.approver_email"))
    if action == "forbid":
        object_id_validators["reject new user"] = "user_id_exists"
        activity_dict["activity_type"] = "reject new user"
        tk.get_action("activity_create")(activity_create_context, activity_dict)
        org = tk.get_action("organization_list_for_user")(
            {"user": user_name}, {"permission": "read"}
        )
        if org:
            tk.get_action("organization_member_delete")(
                context, {"id": org[0]["id"], "username": user_name}
            )
        tk.get_action("user_delete")(context, {"id": user_id})
        msg = (
            "Your account request for {0} has been rejected by {1}"
            "\n\nFor further clarification "
            "as to why your request has been "
            "rejected please contact the NSW Flood Data Portal ({2})"
        )
        try:
            mailer.mail_recipient(
                user.fullname,
                user.email,
                "Account request",
                msg.format(
                    config.get("ckan.site_title"),
                    c.userobj.fullname,
                    c.userobj.email,
                ),
            )
        except Exception as e:
            log.error("Error emailing invite to user: %s", e)

        msg = ("User account request for {0} " "has been rejected by {1}").format(
            user.fullname or user_name, c.userobj.fullname
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
        tk.get_action("activity_create")(activity_create_context, activity_dict)
        org_display_name, org_role = _assign_user_to_org(
            user_id, user_org, user_role, context
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
            c.userobj.fullname,
        )

        for admin_email in list_admin_emails:
            try:
                mailer.mail_recipient(
                    "Admin", admin_email, "Account request feedback", msg
                )
            except mailer.MailerException as e:
                h.flash_error(f"Email error: {e}")
        try:
            org_dict = tk.get_action("organization_show")(context, {"id": user_org})
        except tk.ObjectNotFound:
            org_dict = None

        user.name = user.name
        try:
            mailer.send_invite(user, org_dict, user_role)
        except Exception as e:
            log.error("Error emailing invite to user: %s", e)


    return render("user/account_requests_management.html")
