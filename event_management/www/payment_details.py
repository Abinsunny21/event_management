import frappe

from event_management.portal import get_submitted_payment_details, set_portal_context


def get_context(context):
    set_portal_context(context, "/submitted-payments", ("Event Manager", "System Manager"))
    name = frappe.form_dict.get("name")
    context.payment = get_submitted_payment_details(name)
    context.page_title = context.payment["name"]