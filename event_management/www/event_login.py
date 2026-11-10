import frappe  # type: ignore[reportMissingImports]


def get_context(context):
    context.no_cache = 1

    if frappe.session.user == "Guest":
        return context

    user_roles = frappe.get_roles(frappe.session.user)
    if "System Manager" in user_roles:
        frappe.local.flags.redirect_location = "/app"
    elif "Event Manager" in user_roles:
        frappe.local.flags.redirect_location = "/manager-dashboard"
    elif "Registration Staff" in user_roles:
        frappe.local.flags.redirect_location = "/registration-dashboard"
    else:
        frappe.local.flags.redirect_location = "/me"
    raise frappe.Redirect
