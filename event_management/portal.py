import frappe  # type: ignore[reportMissingImports]
from frappe import _  # type: ignore[reportMissingImports]
from frappe.model.workflow import apply_workflow, get_transitions  # type: ignore[reportMissingImports]
from frappe.utils import flt, getdate  # type: ignore[reportMissingImports]

PORTAL_ROLES = ("Registration Staff", "Event Manager", "System Manager")


def get_count(doctype, filters=None):
    """Return the count of records accessible to the current user."""

    result = frappe.get_list(
        doctype,
        filters=filters or {},
        fields=["count(name) as total"],
        limit_page_length=1
    )

    return result[0].total if result else 0


def require_portal_user(roles=PORTAL_ROLES):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to access the EventPro portal."), frappe.PermissionError)

    if not set(roles).intersection(frappe.get_roles()):
        frappe.throw(_("You do not have permission to access this page."), frappe.PermissionError)


def set_portal_context(context, active_page, roles=PORTAL_ROLES):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/event-login"
        raise frappe.Redirect
    require_portal_user(roles)
    user_roles = frappe.get_roles()
    context.no_cache = 1
    context.user_name = frappe.utils.get_fullname(frappe.session.user)
    context.user_email = frappe.session.user
    context.user_role = next(
        (role for role in ("System Manager", "Event Manager", "Registration Staff") if role in user_roles),
        "",
    )
    context.account_url = "/my-account"
    context.dashboard_url = (
        "/registration-dashboard"
        if "Registration Staff" in user_roles and "Event Manager" not in user_roles
        else "/manager-dashboard"
        if "Event Manager" in user_roles
        else "/app"
    )
    context.active_page = active_page
    context.can_create_registrations = (
        "Registration Staff" in user_roles
        and "Event Manager" not in user_roles
        and frappe.has_permission("Event Registration", "create")
    )

    links = [
        ("Overview", context.dashboard_url, "▦", True),
        ("Registrations", "/registrations", "▤", frappe.has_permission("Event Registration", "read")),
        (
            "New Registration",
            "/new-registration",
            "+",
            context.can_create_registrations,
        ),
        ("Participants", "/participants", "♙", frappe.has_permission("Participant", "read")),
        ("Events", "/events", "◈", frappe.has_permission("Event Details", "read")),
    ]

    if "Event Manager" in user_roles or "System Manager" in user_roles:
        links.extend(
            [
                ("Payments", "/payments", "$", frappe.has_permission("Event Payment", "read")),
                ("Ticket Types", "/ticket-types", "◇", frappe.has_permission("Ticket Type", "read")),
            ]
        )

    context.portal_links = [
        {"label": label, "url": url, "icon": icon, "active": active_page == url, "visible": visible}
        for label, url, icon, visible in links
    ]
    if "Event Manager" in user_roles or "System Manager" in user_roles:
        context.portal_links.append(
            {
                "label": "Submitted Payments",
                "url": "/submitted-payments",
                "icon": "$",
                "active": active_page == "/submitted-payments",
                "visible": frappe.has_permission("Event Payment", "read"),
            }
        )
    context.account_active = active_page == context.account_url
def _require_permission(doctype, permission_type):
    if not frappe.has_permission(doctype, permission_type):
        frappe.throw(
            _("You do not have {0} permission for {1}.").format(permission_type, doctype),
            frappe.PermissionError,
        )


def _require_registration_staff(permission_type):
    roles = frappe.get_roles()
    if "Registration Staff" not in roles or "Event Manager" in roles:
        frappe.throw(_("Only Registration Staff can create registrations."), frappe.PermissionError)
    _require_permission("Event Registration", permission_type)


def _require_registration_write():
    require_portal_user()
    _require_permission("Event Registration", "write")


def _parse_payload(payload):
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Invalid form data."))
    return payload


def _set_allowed_fields(doc, payload, allowed_fields):
    payload = _parse_payload(payload)
    if not all(isinstance(fieldname, str) for fieldname in payload):
        frappe.throw(_("Invalid form field."))
    unknown_fields = set(payload).difference(allowed_fields)
    if unknown_fields:
        frappe.throw(_("Unsupported form fields: {0}.").format(", ".join(sorted(unknown_fields))))
    for fieldname, value in payload.items():
        doc.set(fieldname, value)


def _get_permitted_doc(doctype, name, permission_type="read"):
    if not name or not isinstance(name, str) or len(name) > 140:
        frappe.throw(_("A valid record ID is required."))
    doc = frappe.get_doc(doctype, name)
    doc.check_permission(permission_type)
    return doc


def _get_related_names(records, fieldname, doctype, title_field):
    names = list({row.get(fieldname) for row in records if row.get(fieldname)})
    if not names:
        return {}
    rows = frappe.get_list(
        doctype,
        filters={"name": ["in", names]},
        fields=["name", title_field],
        limit_page_length=len(names),
    )
    return {row.name: row.get(title_field) for row in rows}


def _event_registration_counts(event_names):
    if not event_names:
        return {}
    rows = frappe.get_list(
        "Event Registration",
        filters={
            "event": ["in", event_names],
            "workflow_state": ["in", ["Draft", "Pending Approval", "Approved"]],
            "docstatus": ["!=", 2],
        },
        fields=["event", "count(name) as total"],
        group_by="event",
        limit_page_length=len(event_names),
    )
    return {row.event: row.total for row in rows}


def _is_registration_available(event, active_count, today):
    if event.event_status != "Open":
        return False
    if not event.registration_start_date or not event.registration_end_date:
        return False
    if not (getdate(event.registration_start_date) <= today <= getdate(event.registration_end_date)):
        return False
    return not event.maximum_participants or active_count < event.maximum_participants


def _validate_event_available_for_registration(event_name):
    event = frappe.get_doc("Event Details", event_name, for_update=True)
    event.check_permission("read")
    registered = _event_registration_counts([event.name]).get(event.name, 0)
    if not _is_registration_available(event, registered, getdate()):
        frappe.throw(_("This event is not currently accepting registrations."))
    return event


def _registration_rows(limit=100, filters=None):
    rows = frappe.get_list(
        "Event Registration",
        filters=filters or {},
        fields=[
            "name", "event", "participant", "registration_date", "ticket_type",
            "ticket_amount", "discount", "total_amount", "payment_status",
            "workflow_state", "docstatus", "creation", "owner",
        ],
        order_by="creation desc",
        limit_page_length=limit,
    )
    events = _get_related_names(rows, "event", "Event Details", "event_name")
    participants = _get_related_names(rows, "participant", "Participant", "participant_name")
    return [
        {
            "name": row.name,
            "event": events.get(row.event, row.event or ""),
            "event_id": row.event,
            "participant": participants.get(row.participant, row.participant or ""),
            "participant_id": row.participant,
            "registration_date": row.registration_date,
            "ticket_type": row.ticket_type,
            "ticket_amount": row.ticket_amount,
            "discount": row.discount,
            "total_amount": row.total_amount,
            "payment_status": row.payment_status or "Unpaid",
            "workflow_state": row.workflow_state or "Draft",
            "docstatus": row.docstatus,
            "creation": row.creation,
            "owner": row.owner,
        }
        for row in rows
    ]


@frappe.whitelist()
def get_registration_dashboard_data():
    """Fetch dashboard statistics and recent registrations."""

    require_portal_user(("Registration Staff", "System Manager"))

    # Dashboard statistics
    total_registrations = get_count("Event Registration")

    pending_registrations = get_count(
        "Event Registration",
        {"workflow_state": "Pending Approval"}
    )

    approved_registrations = get_count(
        "Event Registration",
        {"workflow_state": "Approved"}
    )

    total_participants = get_count("Participant")

    # Fetch the latest five registrations
    registrations = frappe.get_list(
        "Event Registration",
        fields=["name", "event", "participant", "payment_status", "workflow_state", "total_amount"],
        order_by="creation desc",
        limit_page_length=5,
    )

    # Fetch accessible event names
    event_names = list({
        row.event for row in registrations if row.event
    })

    events = {}

    if event_names:
        event_records = frappe.get_list(
            "Event Details",
            filters={"name": ["in", event_names]},
            fields=["name", "event_name"],
            limit_page_length=len(event_names)
        )

        events = {
            row.name: row.event_name
            for row in event_records
        }

    # Fetch accessible participant names
    participant_names = list({
        row.participant for row in registrations if row.participant
    })

    participants = {}

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

    # Prepare recent registration details
    recent_registrations = []

    for row in registrations:
        recent_registrations.append({
            "name": row.name,
            "participant": participants.get(row.participant, "N/A"),
            "event": events.get(row.event, "N/A"),
            "payment_status": row.payment_status or "N/A",
            "workflow_state": row.workflow_state or "Draft",
            "total_amount": row.total_amount or 0
        })

    return {
        "total_registrations": total_registrations,
        "pending_registrations": pending_registrations,
        "approved_registrations": approved_registrations,
        "total_participants": total_participants,
        "recent_registrations": recent_registrations
    }


@frappe.whitelist()
def get_manager_dashboard_data():
    require_portal_user(("Event Manager", "System Manager"))
    stats = {
        "total_events": get_count("Event Details"),
        "total_registrations": get_count("Event Registration"),
        "pending_approvals": get_count(
            "Event Registration", {"workflow_state": "Pending Approval", "docstatus": 0}
        ),
        "approved_registrations": get_count(
            "Event Registration", {"workflow_state": "Approved", "docstatus": 1}
        ),
        "rejected_registrations": get_count(
            "Event Registration", {"workflow_state": "Rejected", "docstatus": 0}
        ),
        "total_participants": get_count("Participant"),
        "payments": get_count("Event Payment", {"docstatus": 1}),
    }

    registrations = _registration_rows(6) if frappe.has_permission("Event Registration", "read") else []
    pending_registrations = (
        _registration_rows(6, {"workflow_state": "Pending Approval"})
        if frappe.has_permission("Event Registration", "read")
        else []
    )
    events = frappe.get_list(
        "Event Details",
        filters={"start_date": [">=", frappe.utils.today()], "event_status": ["in", ["Open", "Ongoing"]]},
        fields=["name", "event_name", "start_date", "end_date", "event_category"],
        order_by="start_date asc",
        limit_page_length=5,
    )
    payments = []
    if frappe.has_permission("Event Payment", "read"):
        payments = frappe.get_list(
            "Event Payment",
            filters={"docstatus": 1},
            fields=["name", "registration", "payment_date", "amount", "payment_mode", "docstatus"],
            order_by="creation desc",
            limit_page_length=5,
        )
    return {
        **stats,
        "recent_registrations": registrations,
        "pending_registrations": pending_registrations,
        "upcoming_events": events,
        "recent_payments": payments,
    }


@frappe.whitelist(methods=["GET"])
def get_registration_options(registration_name=None):
    if registration_name:
        _require_registration_write()
        registration = _get_permitted_doc("Event Registration", registration_name, "write")
        if registration.docstatus != 0 or registration.workflow_state not in ("Draft", "Rejected"):
            frappe.throw(_("Only draft or rejected registrations can be edited."))
    else:
        _require_registration_staff("create")
    today = getdate()
    event_filters = {} if registration_name else {
        "event_status": "Open",
        "registration_start_date": ["<=", today],
        "registration_end_date": [">=", today],
    }
    events = frappe.get_list(
        "Event Details",
        filters=event_filters,
        fields=[
            "name", "event_name", "event_category", "start_date", "end_date",
            "registration_start_date", "registration_end_date", "registration_fee",
            "event_status",
            "maximum_participants",
        ],
        order_by="start_date asc",
        limit_page_length=200,
    )
    if not registration_name:
        event_counts = _event_registration_counts([event.name for event in events])
        events = [
            event
            for event in events
            if _is_registration_available(event, event_counts.get(event.name, 0), today)
        ]
    participants = frappe.get_list(
        "Participant",
        fields=["name", "participant_name", "email"],
        order_by="participant_name asc",
        limit_page_length=500,
    )
    ticket_types = frappe.get_list(
        "Ticket Type",
        filters={"is_active": 1},
        fields=["name", "ticket_type_name", "ticket_price", "description"],
        order_by="ticket_type_name asc",
        limit_page_length=200,
    )
    return {"events": events, "participants": participants, "ticket_types": ticket_types}


@frappe.whitelist(methods=["GET"])
def get_portal_registrations():
    require_portal_user()
    _require_permission("Event Registration", "read")
    return {
        "registrations": _registration_rows(100),
        "total": get_count("Event Registration"),
        "pending": get_count("Event Registration", {"workflow_state": "Pending Approval"}),
        "approved": get_count("Event Registration", {"workflow_state": "Approved"}),
        "unpaid": get_count("Event Registration", {"payment_status": "Unpaid"}),
    }


def _payment_rows(docstatus=None, limit=100):
    filters = {"docstatus": docstatus} if docstatus is not None else {}
    rows = frappe.get_list(
        "Event Payment",
        filters=filters,
        fields=[
            "name", "registration", "payment_date", "payment_mode", "amount",
            "transaction_reference", "docstatus", "creation", "owner", "modified",
        ],
        order_by="payment_date desc, creation desc",
        limit_page_length=limit,
    )
    registrations = frappe.get_list(
        "Event Registration",
        filters={"name": ["in", list({row.registration for row in rows if row.registration})]},
        fields=["name", "event", "participant"],
        limit_page_length=len(rows),
    ) if rows else []
    events = _get_related_names(registrations, "event", "Event Details", "event_name")
    participants = _get_related_names(registrations, "participant", "Participant", "participant_name")
    registration_by_name = {row.name: row for row in registrations}
    return [
        {
            "name": row.name,
            "registration": row.registration,
            "participant": participants.get(
                registration_by_name[row.registration].participant,
                registration_by_name[row.registration].participant or "",
            ) if row.registration in registration_by_name else "",
            "event": events.get(
                registration_by_name[row.registration].event,
                registration_by_name[row.registration].event or "",
            ) if row.registration in registration_by_name else "",
            "payment_date": row.payment_date,
            "payment_mode": row.payment_mode,
            "amount": row.amount,
            "transaction_reference": row.transaction_reference,
            "docstatus": row.docstatus,
            "creation": row.creation,
            "owner": row.owner,
            "modified": row.modified,
        }
        for row in rows
    ]


@frappe.whitelist(methods=["GET"])
def get_portal_payments():
    require_portal_user(("Event Manager", "System Manager"))
    _require_permission("Event Payment", "read")
    return _payment_rows(docstatus=None)


@frappe.whitelist(methods=["GET"])
def get_submitted_payments():
    require_portal_user(("Event Manager", "System Manager"))
    _require_permission("Event Payment", "read")
    return _payment_rows(docstatus=1)


@frappe.whitelist(methods=["GET"])
def get_submitted_payment_details(name):
    require_portal_user(("Event Manager", "System Manager"))
    doc = _get_permitted_doc("Event Payment", name)
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted payments can be viewed here."))
    registration = _get_permitted_doc("Event Registration", doc.registration)
    participant_name = _get_related_names(
        [{"participant": registration.participant}], "participant", "Participant", "participant_name"
    ).get(registration.participant)
    event_name = _get_related_names(
        [{"event": registration.event}], "event", "Event Details", "event_name"
    ).get(registration.event)
    return {
        "name": doc.name,
        "registration": doc.registration,
        "participant": participant_name or registration.participant,
        "event": event_name or registration.event,
        "payment_date": doc.payment_date,
        "payment_mode": doc.payment_mode,
        "amount": doc.amount,
        "transaction_reference": doc.transaction_reference,
        "creation": doc.creation,
        "owner": doc.owner,
        "modified": doc.modified,
    }


@frappe.whitelist(methods=["POST"])
def create_registration(event, participant, registration_date, ticket_type, discount=0):
    _require_registration_staff("create")
    _validate_event_available_for_registration(event)
    if not frappe.has_permission("Event Details", "read"):
        frappe.throw(_("You do not have permission to view events."), frappe.PermissionError)
    if not frappe.has_permission("Participant", "read"):
        frappe.throw(_("You do not have permission to view participants."), frappe.PermissionError)
    if not frappe.has_permission("Ticket Type", "read"):
        frappe.throw(_("You do not have permission to view ticket types."), frappe.PermissionError)

    doc = frappe.get_doc(
        {
            "doctype": "Event Registration",
            "event": event,
            "participant": participant,
            "registration_date": registration_date,
            "ticket_type": ticket_type,
            "discount": flt(discount),
            "payment_status": "Unpaid",
        }
    )
    doc.insert()
    return {"name": doc.name}


@frappe.whitelist(methods=["GET"])
def get_registration_details(name):
    require_portal_user()
    doc = _get_permitted_doc("Event Registration", name)
    event = _get_related_names([{"event": doc.event}], "event", "Event Details", "event_name").get(doc.event)
    participant = _get_related_names(
        [{"participant": doc.participant}], "participant", "Participant", "participant_name"
    ).get(doc.participant)
    return {
        "name": doc.name,
        "event": event or doc.event,
        "event_id": doc.event,
        "participant": participant or doc.participant,
        "participant_id": doc.participant,
        "registration_date": doc.registration_date,
        "ticket_type": doc.ticket_type,
        "ticket_amount": doc.ticket_amount,
        "discount": doc.discount,
        "total_amount": doc.total_amount,
        "payment_status": doc.payment_status or "Unpaid",
        "workflow_state": doc.workflow_state or "Draft",
        "docstatus": doc.docstatus,
        "creation": doc.creation,
        "owner": doc.owner,
        "modified": doc.modified,
        "transitions": get_transitions(doc),
        "can_edit": (
            doc.docstatus == 0
            and doc.workflow_state in ("Draft", "Rejected")
            and frappe.has_permission("Event Registration", "write", doc=doc)
        ),
        "can_cancel": (
            doc.docstatus == 1
            and bool({"Event Manager", "System Manager"}.intersection(frappe.get_roles()))
            and frappe.has_permission("Event Registration", "cancel", doc=doc)
        ),
        "can_delete": (
            doc.docstatus == 2
            and bool({"Event Manager", "System Manager"}.intersection(frappe.get_roles()))
            and frappe.has_permission("Event Registration", "delete", doc=doc)
        ),
    }


@frappe.whitelist(methods=["POST"])
def save_registration(name, fields):
    _require_registration_write()
    doc = _get_permitted_doc("Event Registration", name, "write")
    if doc.docstatus != 0 or doc.workflow_state not in ("Draft", "Rejected"):
        frappe.throw(_("Only draft or rejected registrations can be edited."))
    _set_allowed_fields(
        doc,
        fields,
        {"event", "participant", "registration_date", "ticket_type", "discount"},
    )
    doc.save()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def apply_registration_workflow(name, action):
    require_portal_user()
    doc = _get_permitted_doc("Event Registration", name)
    if action not in {transition.action for transition in get_transitions(doc)}:
        frappe.throw(_("That workflow action is not available for this registration."), frappe.PermissionError)
    updated = apply_workflow(
        {"doctype": "Event Registration", "name": doc.name},
        action,
    )
    return {"name": updated.name, "workflow_state": updated.workflow_state}


@frappe.whitelist(methods=["POST"])
def cancel_registration(name):
    require_portal_user(("Event Manager", "System Manager"))
    doc = _get_permitted_doc("Event Registration", name, "cancel")
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted registrations can be cancelled."))
    doc.cancel()
    return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def delete_registration(name):
    require_portal_user(("Event Manager", "System Manager"))
    doc = _get_permitted_doc("Event Registration", name, "delete")
    if doc.docstatus != 2:
        frappe.throw(_("Cancel a submitted registration before deleting it."))
    doc.delete()
    return {"name": name}


@frappe.whitelist(methods=["POST"])
def save_participant(name=None, fields=None):
    require_portal_user()
    fields = _parse_payload(fields or {})
    if name:
        doc = _get_permitted_doc("Participant", name, "write")
        allowed_roles = ("Registration Staff", "Event Manager", "System Manager")
        if not set(allowed_roles).intersection(frappe.get_roles()):
            frappe.throw(_("You do not have permission to edit participants."), frappe.PermissionError)
    else:
        roles = frappe.get_roles()
        if "Registration Staff" not in roles or "Event Manager" in roles:
            frappe.throw(_("Only Registration Staff can create participants."), frappe.PermissionError)
        _require_permission("Participant", "create")
        doc = frappe.new_doc("Participant")
    _set_allowed_fields(doc, fields, {"participant_name", "email", "phone", "company"})
    if name:
        doc.save()
    else:
        doc.insert()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def save_event(name=None, fields=None):
    require_portal_user(("Event Manager", "System Manager"))
    fields = _parse_payload(fields or {})
    if name:
        doc = _get_permitted_doc("Event Details", name, "write")
    else:
        _require_permission("Event Details", "create")
        doc = frappe.new_doc("Event Details")
    _set_allowed_fields(
        doc,
        fields,
        {
            "event_name", "event_category", "start_date", "end_date",
            "registration_start_date", "registration_end_date", "registration_fee",
            "maximum_participants", "event_status",
        },
    )
    if doc.start_date and doc.end_date:
        doc.event_duration = (getdate(doc.end_date) - getdate(doc.start_date)).days + 1
    if name:
        doc.save()
    else:
        doc.insert()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def delete_event(name):
    require_portal_user(("Event Manager", "System Manager"))
    doc = _get_permitted_doc("Event Details", name, "delete")
    doc.delete()
    return {"name": name}


@frappe.whitelist(methods=["POST"])
def save_ticket_type(name=None, fields=None):
    require_portal_user(("Event Manager", "System Manager"))
    fields = _parse_payload(fields or {})
    if name:
        doc = _get_permitted_doc("Ticket Type", name, "write")
        ticket_type_name = fields.pop("ticket_type_name", doc.ticket_type_name)
        if ticket_type_name != doc.ticket_type_name:
            frappe.throw(_("Ticket type names cannot be changed after creation."))
        allowed_fields = {"ticket_price", "description", "is_active"}
    else:
        _require_permission("Ticket Type", "create")
        doc = frappe.new_doc("Ticket Type")
        allowed_fields = {"ticket_type_name", "ticket_price", "description", "is_active"}
    _set_allowed_fields(doc, fields, allowed_fields)
    if name:
        doc.save()
    else:
        doc.insert()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def create_payment(registration, payment_date, payment_mode, amount, transaction_reference=None):
    require_portal_user(("Event Manager", "System Manager"))
    _require_permission("Event Payment", "create")
    registration_doc = _get_permitted_doc("Event Registration", registration)
    doc = frappe.get_doc(
        {
            "doctype": "Event Payment",
            "registration": registration_doc.name,
            "payment_date": payment_date,
            "payment_mode": payment_mode,
            "amount": flt(amount),
            "transaction_reference": transaction_reference,
        }
    )
    doc.insert()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def save_payment(name, fields):
    require_portal_user(("Event Manager", "System Manager"))
    doc = _get_permitted_doc("Event Payment", name, "write")
    if doc.docstatus != 0:
        frappe.throw(_("Only draft payments can be edited."))
    _set_allowed_fields(
        doc,
        fields,
        {"registration", "payment_date", "payment_mode", "amount", "transaction_reference"},
    )
    _get_permitted_doc("Event Registration", doc.registration)
    doc.save()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def update_payment_status(name, action):
    require_portal_user(("Event Manager", "System Manager"))
    if action not in {"Submit", "Cancel"}:
        frappe.throw(_("Unsupported payment action."))
    doc = _get_permitted_doc("Event Payment", name, action.lower())
    if action == "Submit":
        doc.submit()
    elif action == "Cancel":
        doc.cancel()
    return {"name": doc.name, "docstatus": doc.docstatus}