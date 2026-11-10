import frappe
from frappe.model.workflow import get_transitions

from event_management.portal import _get_related_names, set_portal_context


def get_context(context):
    set_portal_context(context, "/registrations")
    name = frappe.form_dict.get("name")
    if not name or not isinstance(name, str) or len(name) > 140:
        frappe.throw("A valid registration ID is required.")

    doc = frappe.get_doc("Event Registration", name)
    doc.check_permission("read")
    context.registration = doc
    context.event_name = _get_related_names(
        [{"event": doc.event}], "event", "Event Details", "event_name"
    ).get(doc.event)
    context.participant_name = _get_related_names(
        [{"participant": doc.participant}], "participant", "Participant", "participant_name"
    ).get(doc.participant)
    context.transitions = get_transitions(doc)
    context.can_edit_registration = (
        doc.docstatus == 0
        and doc.workflow_state in ("Draft", "Rejected")
        and frappe.has_permission("Event Registration", "write", doc=doc)
    )
    manager_roles = {"Event Manager", "System Manager"}.intersection(frappe.get_roles())
    context.can_cancel_registration = (
        doc.docstatus == 1
        and bool(manager_roles)
        and frappe.has_permission("Event Registration", "cancel", doc=doc)
    )
    context.can_delete_registration = (
        doc.docstatus == 2
        and bool(manager_roles)
        and frappe.has_permission("Event Registration", "delete", doc=doc)
    )
    context.page_title = f"Registration {doc.name}"
