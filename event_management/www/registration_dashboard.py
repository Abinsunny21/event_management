from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/registration-dashboard", ("Registration Staff",))
    context.page_title = "Registration Staff Dashboard"