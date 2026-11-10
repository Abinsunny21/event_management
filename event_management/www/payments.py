import frappe

from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/payments")
    context.payments = frappe.get_list(
        "Event Payment",
        fields=[
            "name", "registration", "payment_date", "payment_mode", "amount",
            "transaction_reference", "docstatus", "creation",
        ],
        order_by="creation desc",
        limit_page_length=100,
    )
    roles = frappe.get_roles()
    context.can_create_payment = (
        ("Event Manager" in roles or "System Manager" in roles)
        and frappe.has_permission("Event Payment", "create")
    )
    context.can_manage_payments = "Event Manager" in roles or "System Manager" in roles
    context.can_edit_payments = (
        context.can_manage_payments and frappe.has_permission("Event Payment", "write")
    )
    context.can_submit_payments = (
        context.can_manage_payments and frappe.has_permission("Event Payment", "submit")
    )
    context.can_cancel_payments = (
        context.can_manage_payments and frappe.has_permission("Event Payment", "cancel")
    )
    name = frappe.form_dict.get("name")
    context.selected_payment = None
    if name:
        if not isinstance(name, str) or len(name) > 140:
            frappe.throw("A valid payment ID is required.")
        context.selected_payment = frappe.get_doc("Event Payment", name)
        context.selected_payment.check_permission("read")
    context.can_edit_payment = (
        context.selected_payment
        and context.can_manage_payments
        and context.selected_payment.docstatus == 0
        and frappe.has_permission("Event Payment", "write", doc=context.selected_payment)
    )
    context.registrations = frappe.get_list(
        "Event Registration",
        fields=["name", "total_amount", "payment_status"],
        order_by="creation desc",
        limit_page_length=500,
    )
    context.page_title = "Event Payments"
