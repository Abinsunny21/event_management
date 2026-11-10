frappe.ui.form.on('Event Details', {

    refresh(frm) {

        calculate_event_duration(frm);

        // Show button only for saved events
        if (!frm.is_new()) {

            frm.add_custom_button(__('View Registrations'), function() {

                frappe.set_route('List', 'Event Registration', {
                    event: frm.doc.name
                });

            });

        }
    },

    start_date(frm) {
        calculate_event_duration(frm);
    },

    end_date(frm) {
        calculate_event_duration(frm);
    },

    // Validate event dates before saving
    validate(frm) {
        if (
            frm.doc.start_date &&
            frm.doc.end_date &&
            frm.doc.end_date < frm.doc.start_date
        ) {
            frappe.msgprint({
                title: __('Invalid Dates'),
                message: __('End Date cannot be earlier than Start Date.'),
                indicator: 'red'
            });

            frappe.validated = false;
        }
    }
});

function calculate_event_duration(frm) {

    let start_date = frm.doc.start_date;
    let end_date = frm.doc.end_date;

    if (!start_date || !end_date) {
        frm.set_value('event_duration', null);
        return;
    }

    let start = new Date(start_date + 'T00:00:00');
    let end = new Date(end_date + 'T00:00:00');

    if (end < start) {
        frm.set_value('event_duration', null);
        return;
    }

    let difference = end - start;

    let duration = Math.floor(
        difference / (1000 * 60 * 60 * 24)
    ) + 1;

    frm.set_value('event_duration', duration);
}