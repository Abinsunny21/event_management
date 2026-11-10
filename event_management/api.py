import frappe  # pyright: ignore[reportMissingImports]


@frappe.whitelist()
def get_available_events():

    try:
        events = frappe.get_list(
            "Event Details",
            filters={
                "event_status": "Open"
            },
            fields=[
                "name",
                "event_name",
                "event_category",
                "start_date",
                "end_date",
                "registration_fee",
                "maximum_participants",
                "event_status"
            ],
            order_by="start_date asc"
        )

        event_list = []

        for event in events:
            event_list.append({
                "event_id": event.name,
                "event_name": event.event_name,
                "event_category": event.event_category,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "registration_fee": event.registration_fee,
                "maximum_participants": event.maximum_participants,
                "event_status": event.event_status
            })

        return {
            "success": True,
            "message": "Available events retrieved successfully.",
            "data": event_list
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Available Events API Error"
        )

        return {
            "success": False,
            "message": "Unable to retrieve available events.",
            "data": []
        }
@frappe.whitelist()
def get_event_details(event_id=None):

    try:
        # Validate the input
        if not event_id:
            return {
                "success": False,
                "message": "Event ID is required.",
                "data": None
            }

        # Check whether the event exists
        if not frappe.db.exists("Event Details", event_id):
            return {
                "success": False,
                "message": f"Event '{event_id}' does not exist.",
                "data": None
            }

        # Fetch event details
        event = frappe.get_doc("Event Details", event_id)
        event.check_permission("read")

        return {
            "success": True,
            "message": "Event details retrieved successfully.",
            "data": {
                "event_id": event.name,
                "event_name": event.event_name,
                "event_category": event.event_category,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "registration_start_date": event.registration_start_date,
                "registration_end_date": event.registration_end_date,
                "registration_fee": event.registration_fee,
                "maximum_participants": event.maximum_participants,
                "event_status": event.event_status,
                "event_duration": event.event_duration
            }
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Event Details API Error"
        )

        return {
            "success": False,
            "message": "Unable to retrieve event details.",
            "data": None
        }


@frappe.whitelist()
def get_registered_participants(event_id=None):

    try:
        # Validate Event ID
        if not event_id:
            return {
                "success": False,
                "message": "Event ID is required.",
                "data": []
            }

        # Check whether the event exists
        if not frappe.db.exists("Event Details", event_id):
            return {
                "success": False,
                "message": f"Event '{event_id}' does not exist.",
                "data": []
            }

        # Get approved registrations for this event
        registrations = frappe.get_list(
            "Event Registration",
            filters={
                "event": event_id,
                "workflow_state": "Approved",
                "docstatus": 1
            },
            fields=[
                "name",
                "participant",
                "ticket_type",
                "registration_date",
                "total_amount",
                "payment_status"
            ],
            order_by="creation asc"
        )

        # Collect Participant IDs
        participant_ids = list({
            registration.participant
            for registration in registrations
            if registration.participant
        })

        # Fetch participant details
        participants = []

        if participant_ids:
            participants = frappe.get_list(
                "Participant",
                filters={
                    "name": ["in", participant_ids]
                },
                fields=[
                    "name",
                    "participant_name",
                    "email",
                    "phone",
                    "company"
                ]
            )

        # Create a lookup for participant details
        participant_map = {
            participant.name: participant
            for participant in participants
        }

        # Prepare the response
        participant_list = []

        for registration in registrations:

            participant = participant_map.get(
                registration.participant
            )

            if participant:
                participant_list.append({
                    "registration_id": registration.name,
                    "participant_id": participant.name,
                    "participant_name": participant.participant_name,
                    "email": participant.email,
                    "phone": participant.phone,
                    "company": participant.company,
                    "ticket_type": registration.ticket_type,
                    "registration_date": registration.registration_date,
                    "total_amount": registration.total_amount,
                    "payment_status": registration.payment_status
                })

        return {
            "success": True,
            "message": "Registered participants retrieved successfully.",
            "data": {
                "event_id": event_id,
                "total_participants": len(participant_list),
                "participants": participant_list
            }
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Get Registered Participants API Error"
        )

        return {
            "success": False,
            "message": "Unable to retrieve registered participants.",
            "data": []
        }