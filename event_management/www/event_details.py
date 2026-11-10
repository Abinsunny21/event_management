import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/events")
    name = frappe.form_dict.get("name")
    context.event = None
    context.is_new_event = not name
    roles = frappe.get_roles()
    manager = "Event Manager" in roles or "System Manager" in roles
    if name:
        if not isinstance(name, str) or len(name) > 140:
            frappe.throw("A valid event ID is required.")
        context.event = frappe.get_doc("Event Details", name)
        context.event.check_permission("read")
        context.can_edit_event = manager and frappe.has_permission(
            "Event Details", "write", doc=context.event
        )
        context.can_delete_event = manager and frappe.has_permission(
            "Event Details", "delete", doc=context.event
        )
    else:
        context.can_edit_event = manager and frappe.has_permission("Event Details", "create")
        context.can_delete_event = False
        if not context.can_edit_event:
            frappe.throw("You do not have permission to create events.", frappe.PermissionError)
    context.page_title = "New Event" if not name else f"Event {name}"
