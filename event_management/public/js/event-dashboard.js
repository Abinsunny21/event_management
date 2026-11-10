// ==========================================
// EventPro - Registration Staff Dashboard
// ==========================================

(function () {

    function setValue(id, value) {
        const element = document.getElementById(id);

        if (element) {
            element.textContent = value ?? 0;
        }
    }

    function createCell(value) {
        const td = document.createElement("td");
        td.textContent = value || "N/A";
        return td;
    }

    function renderRegistrations(registrations) {
        const tbody = document.getElementById("recent-registrations");

        if (!tbody) return;

        tbody.replaceChildren();

        if (!registrations || registrations.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-message";
            cell.textContent = "No registrations found.";

            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }

        registrations.forEach(function (registration) {
            const row = document.createElement("tr");

            const idCell = document.createElement("td");
            const link = document.createElement("a");

            link.href = "/registration-details?name=" +
                encodeURIComponent(registration.name);

            link.textContent = registration.name;
            idCell.appendChild(link);

            row.appendChild(idCell);
            row.appendChild(createCell(registration.participant));
            row.appendChild(createCell(registration.event));
            row.appendChild(createCell(registration.payment_status));
            row.appendChild(createCell(registration.workflow_state));

            tbody.appendChild(row);
        });
    }

    function showError() {
        const tbody = document.getElementById("recent-registrations");

        if (!tbody) return;

        tbody.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-message";
        cell.textContent = "Unable to load dashboard data.";

        row.appendChild(cell);
        tbody.appendChild(row);
    }

    function loadDashboard() {

        frappe.call({
            method: "event_management.portal.get_registration_dashboard_data",

            callback: function (response) {

                if (!response.message) {
                    showError();
                    return;
                }

                const data = response.message;

                setValue("total-registrations", data.total_registrations);
                setValue("pending-registrations", data.pending_registrations);
                setValue("approved-registrations", data.approved_registrations);
                setValue("total-participants", data.total_participants);

                renderRegistrations(data.recent_registrations);
            },

            error: function () {
                showError();
            }
        });
    }

    // Run only on the Registration Staff dashboard.
    function initializeDashboard() {
        if (!document.getElementById("total-registrations")) {
            return;
        }

        loadDashboard();
        window.addEventListener("storage", function (event) {
            if (event.key === "eventpro-portal-data-changed") {
                loadDashboard();
            }
        });
        window.addEventListener("pageshow", function (event) {
            if (event.persisted) loadDashboard();
        });
    }

    if (window.frappe && frappe.ready) {
        frappe.ready(initializeDashboard);
    } else {
        document.addEventListener("DOMContentLoaded", initializeDashboard);
    }

})();