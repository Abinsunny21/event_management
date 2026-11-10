import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/my-account")
    user = frappe.get_doc("User", frappe.session.user)
    context.account_profile = {
        "full_name": user.full_name or context.user_name,
        "email": user.email or context.user_email,
        "phone": user.phone,
        "mobile_no": user.mobile_no,
        "user_type": user.user_type,
        "last_login": user.last_login,
        "time_zone": user.time_zone,
        "language": user.language,
    }
    context.page_title = "My Account"
