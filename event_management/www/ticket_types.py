import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/ticket-types")
    context.ticket_types = frappe.get_list(
        "Ticket Type",
        fields=["name", "ticket_type_name", "ticket_price", "description", "is_active", "modified"],
        order_by="ticket_type_name asc",
        limit_page_length=200,
    )
    roles = frappe.get_roles()
    context.can_manage_ticket_types = (
        ("Event Manager" in roles or "System Manager" in roles)
        and frappe.has_permission("Ticket Type", "write")
    )
    context.can_create_ticket_type = (
        ("Event Manager" in roles or "System Manager" in roles)
        and frappe.has_permission("Ticket Type", "create")
    )
    name = frappe.form_dict.get("name")
    context.ticket_type = None
    context.show_ticket_type_form = not name and frappe.form_dict.get("new") == "1"
    if name:
        if not isinstance(name, str) or len(name) > 140:
            frappe.throw("A valid ticket type ID is required.")
        context.ticket_type = frappe.get_doc("Ticket Type", name)
        context.ticket_type.check_permission("read")
        context.can_edit_ticket_type = context.can_manage_ticket_types and frappe.has_permission(
            "Ticket Type", "write", doc=context.ticket_type
        )
    else:
        context.can_edit_ticket_type = context.can_create_ticket_type
    context.page_title = "Ticket Types"
