import frappe


def get_context(context):
    context.no_cache = 1
    frappe.local.login_manager.logout()
    frappe.db.commit()
    frappe.local.flags.redirect_location = "/event-login"
    raise frappe.Redirect
