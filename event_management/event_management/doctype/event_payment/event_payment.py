# Copyright (c) 2026, EventPro Solutions and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EventPayment(Document):

    def validate(self):
        self.validate_payment_amount()

    def validate_payment_amount(self):

        if not self.registration:
            frappe.throw("Please select a Registration.")

        if flt(self.amount) <= 0:
            frappe.throw("Payment Amount must be greater than zero.")

        registration_total = frappe.db.get_value(
            "Event Registration",
            self.registration,
            "total_amount"
        )

        if registration_total is None:
            frappe.throw("Selected Registration does not exist.")

        # Count only previously submitted payments.
        previous_payments = frappe.db.get_all(
            "Event Payment",
            filters={
                "registration": self.registration,
                "docstatus": 1,
                "name": ["!=", self.name]
            },
            fields=["amount"]
        )

        total_paid = sum(
            flt(payment.amount) for payment in previous_payments
        )

        outstanding_amount = flt(registration_total) - total_paid

        if flt(self.amount) > outstanding_amount:
            frappe.throw(
                f"Payment exceeds the outstanding amount of "
                f"₹{outstanding_amount:.2f}."
            )

    def on_submit(self):
        self.update_payment_status(self.registration)

    def on_cancel(self):
        self.update_payment_status(self.registration)

    def on_trash(self):
        self.update_payment_status(self.registration)

    def update_payment_status(self, registration_name):

        if not registration_name:
            return

        registration_total = frappe.db.get_value(
            "Event Registration",
            registration_name,
            "total_amount"
        )

        if registration_total is None:
            return

        # Only submitted payments are considered.
        payments = frappe.db.get_all(
            "Event Payment",
            filters={
                "registration": registration_name,
                "docstatus": 1
            },
            fields=["amount"]
        )

        total_paid = sum(
            flt(payment.amount) for payment in payments
        )

        registration_total = flt(registration_total)

        if total_paid <= 0:
            payment_status = "Unpaid"

        elif total_paid < registration_total:
            payment_status = "Partially Paid"

        else:
            payment_status = "Paid"

        frappe.db.set_value(
            "Event Registration",
            registration_name,
            "payment_status",
            payment_status
        )