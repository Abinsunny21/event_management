# Copyright (c) 2026, EventPro Solutions and contributors
# For license information, please see license.txt

import frappe  # type: ignore[reportMissingImports]
from frappe.model.document import Document  # type: ignore[reportMissingImports]
from frappe.utils import getdate,flt  # type: ignore[reportMissingImports]

class EventRegistration(Document):

    def validate(self):
        self.validate_duplicate_registration()
        self.validate_event_capacity()
        self.validate_registration_period()
        self.validate_ticket_amount_and_discount()

    def validate_duplicate_registration(self):

        existing_registration = frappe.db.exists(
            "Event Registration",
            {
                "event": self.event,
                "participant": self.participant,
                "name": ["!=", self.name]
            }
        )

        if existing_registration:
            frappe.throw(
                "This participant is already registered for this event."
            )

    def validate_event_capacity(self):

        if not self.event:
            return

        if self.workflow_state == "Rejected":
            return

        maximum_participants = frappe.db.get_value(
            "Event Details",
            self.event,
            "maximum_participants"
        )

        if not maximum_participants:
            return

        existing_registrations = frappe.db.count(
            "Event Registration",
            filters={
                "event": self.event,
               "workflow_state": ["in", [
               "Draft", "Pending Approval", "Approved"
         ]],
                "docstatus": ["!=", 2],
                "name": ["!=", self.name]
            }
        )

        if existing_registrations >= maximum_participants:
            frappe.throw(
                "This event has reached its maximum participant capacity."
            )
    def validate_registration_period(self):

        if not self.event or not self.registration_date:
            return

        event_dates = frappe.db.get_value(
            "Event Details",
            self.event,
            ["registration_start_date", "registration_end_date"],
            as_dict=True
        )

        if not event_dates:
            frappe.throw("Selected event does not exist.")

        if not event_dates.registration_start_date:
            frappe.throw("Registration Start Date is not configured for this event.")

        if not event_dates.registration_end_date:
            frappe.throw("Registration End Date is not configured for this event.")

        registration_date = getdate(self.registration_date)
        start_date = getdate(event_dates.registration_start_date)
        end_date = getdate(event_dates.registration_end_date)

        if registration_date < start_date:
            frappe.throw(
                "Registration date cannot be earlier than the event registration start date."
            )

        if registration_date > end_date:
            frappe.throw(
                "Registration date cannot be later than the event registration end date."
            )

    def validate_ticket_amount_and_discount(self):

        if not self.ticket_type:
            frappe.throw("Please select a Ticket Type.")

        ticket_details = frappe.db.get_value(
            "Ticket Type",
            self.ticket_type,
            ["ticket_price", "is_active"],
            as_dict=True
        )

        if not ticket_details:
            frappe.throw("Selected Ticket Type does not exist.")

        if not ticket_details.is_active:
            frappe.throw("This Ticket Type is currently inactive.")

        ticket_amount = flt(ticket_details.ticket_price)
        discount = flt(self.discount)

        if discount < 0:
            frappe.throw("Discount cannot be negative.")

        if discount > ticket_amount:
            frappe.throw("Discount cannot exceed Ticket Amount.")

        self.ticket_amount = ticket_amount
        self.total_amount = flt(ticket_amount - discount)