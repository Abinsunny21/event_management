def get_context(context):
    import frappe

    frappe.local.flags.redirect_location = "/my-account"
    raise frappe.Redirect
