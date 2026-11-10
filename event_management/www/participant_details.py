import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/participants")
    name = frappe.form_dict.get("name")
    context.participant = None
    context.is_new_participant = not name
    if name:
        if not isinstance(name, str) or len(name) > 140:
            frappe.throw("A valid participant ID is required.")
        context.participant = frappe.get_doc("Participant", name)
        context.participant.check_permission("read")
        context.can_edit_participant = frappe.has_permission(
            "Participant", "write", doc=context.participant
        )
    else:
        context.can_edit_participant = (
            "Registration Staff" in frappe.get_roles()
            and "Event Manager" not in frappe.get_roles()
            and frappe.has_permission("Participant", "create")
        )
        if not context.can_edit_participant:
            frappe.throw("You do not have permission to create participants.", frappe.PermissionError)
    context.page_title = "New Participant" if not name else f"Participant {name}"
