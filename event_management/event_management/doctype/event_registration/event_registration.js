// Copyright (c) 2026, 	EventPro Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Event Registration', {

    refresh(frm) {
        if (frm.doc.event) {
            fetch_event_details(frm);
        }

        calculate_total_amount(frm);
    },

    event(frm) {
        if (frm.doc.event) {
            fetch_event_details(frm);
        } else {
            frm.set_intro('');
        }
    },

    ticket_type(frm) {
        calculate_ticket_amount(frm);
    },

    ticket_amount(frm) {
        calculate_total_amount(frm);
    },

    discount(frm) {
        calculate_total_amount(frm);
    },

    validate(frm) {
        let ticket_amount = frm.doc.ticket_amount || 0;
        let discount = frm.doc.discount || 0;

        if (discount < 0) {
            frappe.msgprint('Discount cannot be negative.');
            frappe.validated = false;
            return;
        }

        if (discount > ticket_amount) {
            frappe.msgprint('Discount cannot exceed Ticket Amount.');
            frappe.validated = false;
        }
    }
});


// Fetch selected Event information
function fetch_event_details(frm) {

    frappe.db.get_value(
        'Event Details',
        frm.doc.event,
        [
            'registration_fee',
            'event_category',
            'start_date',
            'end_date'
        ]
    ).then(r => {

        if (r.message) {

            let event = r.message;

            let message = `
                <b>Event Category:</b> ${event.event_category || '-'}<br>
                <b>Start Date:</b> ${event.start_date || '-'}<br>
                <b>End Date:</b> ${event.end_date || '-'}<br>
                <b>Registration Fee:</b> ₹${event.registration_fee || 0}
            `;

            frm.set_intro(message, 'blue');
        }
    });
}


// Set Ticket Amount based on Ticket Type
function calculate_ticket_amount(frm) {

    if (!frm.doc.ticket_type) {
        frm.set_value('ticket_amount', 0);
        calculate_total_amount(frm);
        return;
    }

    frappe.db.get_value(
        'Ticket Type',
        frm.doc.ticket_type,
        'ticket_price'
    ).then(r => {

        if (r.message) {

            frm.set_value(
                'ticket_amount',
                r.message.ticket_price || 0
            );

        } else {

            frm.set_value('ticket_amount', 0);

        }

        calculate_total_amount(frm);
    });
}


// Calculate Total Amount after Discount
function calculate_total_amount(frm) {

    let ticket_amount = frm.doc.ticket_amount || 0;
    let discount = frm.doc.discount || 0;

    frm.toggle_reqd('discount', discount > 0);

    let total = ticket_amount - discount;

    if (total < 0) {
        total = 0;
    }

    frm.set_value('total_amount', total);
}
