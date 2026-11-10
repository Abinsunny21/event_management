
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("registration-search");
    const workflowFilter = document.getElementById("workflow-filter");
    const paymentFilter = document.getElementById("payment-filter");
    const tableBody = document.getElementById("registrations-table-body");
    const noResults = document.getElementById("no-search-results");

    if (!searchInput || !workflowFilter || !paymentFilter || !tableBody) {
        return;
    }

    function renderRegistrationRows(data) {
        tableBody.replaceChildren();
        if (!data.registrations.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 8;
            cell.className = "empty-registrations";
            cell.textContent = "No registrations found.";
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
        data.registrations.forEach(function (item) {
            const row = document.createElement("tr");
            row.dataset.registration = (item.name || "").toLowerCase();
            row.dataset.participant = (item.participant || "").toLowerCase();
            row.dataset.event = (item.event || "").toLowerCase();
            row.dataset.workflow = item.workflow_state || "Draft";
            row.dataset.payment = item.payment_status || "Unpaid";
            const idCell = document.createElement("td");
            const link = document.createElement("a");
            link.href = "/registration-details?name=" + encodeURIComponent(item.name);
            link.textContent = item.name;
            idCell.appendChild(link);
            row.appendChild(idCell);
            [item.participant, item.event, item.ticket_type, "₹" + Number(item.total_amount || 0).toFixed(2),
                item.payment_status, item.workflow_state].forEach(function (value) {
                const cell = document.createElement("td");
                cell.textContent = value || "—";
                row.appendChild(cell);
            });
            const actionCell = document.createElement("td");
            const viewLink = document.createElement("a");
            viewLink.href = link.href;
            viewLink.className = "registration-view-button";
            viewLink.textContent = "View";
            actionCell.appendChild(viewLink);
            row.appendChild(actionCell);
            tableBody.appendChild(row);
        });
        filterRegistrations();
        const total = document.getElementById("registration-total-count");
        const pending = document.getElementById("registration-pending-count");
        const approved = document.getElementById("registration-approved-count");
        const unpaid = document.getElementById("registration-unpaid-count");
        const recordCount = document.getElementById("registration-record-count");
        if (total) total.textContent = data.total;
        if (pending) pending.textContent = data.pending;
        if (approved) approved.textContent = data.approved;
        if (unpaid) unpaid.textContent = data.unpaid;
        if (recordCount) recordCount.textContent = data.total + " Records";
    }

    function refreshRegistrationRows() {
        frappe.call({
            method: "event_management.portal.get_portal_registrations",
            callback: function (response) {
                if (response.message) renderRegistrationRows(response.message);
            },
            error: function () {
                const empty = document.getElementById("no-search-results");
                if (empty) {
                    empty.textContent = "Could not refresh registrations.";
                    empty.hidden = false;
                }
            }
        });
    }

    function filterRegistrations() {

        const searchValue = searchInput.value.toLowerCase().trim();
        const workflowValue = workflowFilter.value;
        const paymentValue = paymentFilter.value;

        const rows = tableBody.querySelectorAll("tr[data-registration]");

        let visibleCount = 0;

        rows.forEach(function (row) {

            const registration = row.dataset.registration || "";
            const participant = row.dataset.participant || "";
            const event = row.dataset.event || "";
            const workflow = row.dataset.workflow || "";
            const payment = row.dataset.payment || "";

            const matchesSearch =
                registration.includes(searchValue) ||
                participant.includes(searchValue) ||
                event.includes(searchValue);

            const matchesWorkflow =
                !workflowValue || workflow === workflowValue;

            const matchesPayment =
                !paymentValue || payment === paymentValue;

            const shouldShow =
                matchesSearch && matchesWorkflow && matchesPayment;

            row.hidden = !shouldShow;

            if (shouldShow) {
                visibleCount++;
            }

        });

        if (noResults) {
            noResults.hidden = visibleCount !== 0;
        }
    }

    searchInput.addEventListener("input", filterRegistrations);
    workflowFilter.addEventListener("change", filterRegistrations);
    paymentFilter.addEventListener("change", filterRegistrations);
    window.addEventListener("storage", function (event) {
        if (event.key === "eventpro-portal-data-changed") refreshRegistrationRows();
    });
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) refreshRegistrationRows();
    });
});
