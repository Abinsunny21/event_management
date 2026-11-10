# Copyright (c) 2026, EventPro Solutions and contributors
# For license information, please see license.txt

import frappe  # type: ignore[reportMissingImports]
from frappe.model.document import Document  # type: ignore[reportMissingImports]
from frappe.utils import getdate  # type: ignore[reportMissingImports]


class EventDetails(Document):

    def validate(self):
        self.validate_event_dates()

    def validate_event_dates(self):

        if not self.start_date or not self.end_date:
            return

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date)

        if end_date < start_date:
            frappe.throw(
                "Event End Date cannot be earlier than Start Date."
            )