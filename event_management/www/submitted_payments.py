from event_management.portal import get_submitted_payments, set_portal_context


def get_context(context):
    set_portal_context(context, "/submitted-payments", ("Event Manager", "System Manager"))
    context.payments = get_submitted_payments()
    context.page_title = "Submitted Payments"