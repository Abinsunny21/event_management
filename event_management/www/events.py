import frappe
from frappe.utils import getdate

from event_management.portal import _event_registration_counts, _is_registration_available, set_portal_context


def get_context(context):
    set_portal_context(context, "/events")
    context.events = frappe.get_list(
        "Event Details",
        fields=[
            "name", "event_name", "event_category", "start_date", "end_date",
            "registration_start_date", "registration_end_date", "registration_fee",
            "maximum_participants", "event_status", "event_duration",
        ],
        order_by="start_date asc",
        limit_page_length=200,
    )
    counts = _event_registration_counts([row.name for row in context.events])
    today = getdate()
    for row in context.events:
        row.registration_available = _is_registration_available(row, counts.get(row.name, 0), today)
    roles = frappe.get_roles()
    context.can_manage_events = (
        ("Event Manager" in roles or "System Manager" in roles)
        and frappe.has_permission("Event Details", "write")
    )
    context.can_create_event = (
        ("Event Manager" in roles or "System Manager" in roles)
        and frappe.has_permission("Event Details", "create")
    )
    context.page_title = "Events"
