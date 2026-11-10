from event_management.portal import set_portal_context


def get_context(context):
    set_portal_context(context, "/manager-dashboard", ("Event Manager", "System Manager"))
    context.page_title = "Event Manager Dashboard"
