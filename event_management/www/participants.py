import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/participants")
    context.participants = frappe.get_list(
        "Participant",
        fields=["name", "participant_name", "email", "phone", "company", "modified"],
        order_by="modified desc",
        limit_page_length=100,
    )
    context.can_create_participant = (
        "Registration Staff" in frappe.get_roles()
        and "Event Manager" not in frappe.get_roles()
        and frappe.has_permission("Participant", "create")
    )
    context.page_title = "Participants"
