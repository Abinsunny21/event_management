
import frappe  # pyright: ignore[reportMissingImports]

from event_management.portal import set_portal_context

def get_context(context):
    set_portal_context(context, "/registrations")
    context.registrations = get_registrations()


def get_registrations():
    """Fetch registrations while respecting Frappe permissions."""

    records = frappe.get_list(
        "Event Registration",
        fields=[
            "name",
            "event",
            "participant",
            "registration_date",
            "ticket_type",
            "total_amount",
            "payment_status",
            "workflow_state",
            "docstatus",
            "creation"
        ],
        order_by="creation desc",
        limit_page_length=50
    )

    event_names = list({row.event for row in records if row.event})
    participant_names = list({row.participant for row in records if row.participant})

    events = {}
    participants = {}

    if event_names:
        event_records = frappe.get_list(
            "Event Details",
            filters={"name": ["in", event_names]},
            fields=["name", "event_name"],
            limit_page_length=len(event_names)
        )
        events = {row.name: row.event_name for row in event_records}

    if participant_names:
        participant_records = frappe.get_list(
            "Participant",
            filters={"name": ["in", participant_names]},
            fields=["name", "participant_name"],
            limit_page_length=len(participant_names)
        )
        participants = {
            row.name: row.participant_name
            for row in participant_records
        }

    result = []

    for row in records:
        result.append({
            "name": row.name,
            "event": events.get(row.event, row.event or "N/A"),
            "participant": participants.get(
                row.participant,
                row.participant or "N/A"
            ),
            "registration_date": row.registration_date,
            "ticket_type": row.ticket_type or "N/A",
            "total_amount": row.total_amount or 0,
            "payment_status": row.payment_status or "Unpaid",
            "workflow_state": row.workflow_state or "Draft",
            "docstatus": row.docstatus
        })

    return result
