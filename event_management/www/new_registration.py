import frappe

from event_management.portal import set_portal_context


def get_context(context):
    if "Event Manager" in frappe.get_roles():
        frappe.throw("Event Managers cannot create Event Registrations.", frappe.PermissionError)
    set_portal_context(context, "/new-registration", ("Registration Staff",))
    context.page_title = "New Registration"
