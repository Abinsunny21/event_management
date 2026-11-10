import frappe  # type: ignore
from frappe import _  # type: ignore


def get_context(context):
    context.no_cache = 1

    user = frappe.session.user

    # Redirect visitors who are not logged in.
    if user == "Guest":
        frappe.local.flags.redirect_location = "/event-login"
        raise frappe.Redirect

    user_roles = frappe.get_roles(user)

    # Allow only Event Manager.
    if "Event Manager" not in user_roles:
        frappe.throw(
            _("You do not have permission to access the Event Manager dashboard."),
            frappe.PermissionError
        )

    context.user_name = frappe.utils.get_fullname(user)
    context.user_email = user
    context.page_title = "Event Manager Dashboard"