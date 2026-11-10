(function () {
    "use strict";
    const SUCCESS_MESSAGE_KEY = "eventpro-portal-success";
    const DATA_CHANGED_KEY = "eventpro-portal-data-changed";

    function call(method, args) {
        return new Promise(function (resolve, reject) {
            const request = frappe.call({
                method: "event_management.portal." + method,
                type: method.indexOf("get_") === 0 ? "GET" : "POST",
                args: args || {},
                callback: function (response) {
                    if (response.exc) {
                        reject(new Error(response._server_messages || "The request could not be completed."));
                    } else {
                        resolve(response.message);
                    }
                }
            });
            if (request && typeof request.fail === "function") {
                request.fail(function (xhr) {
                    let response = xhr && xhr.responseJSON;
                    if (!response && xhr && xhr.responseText) {
                        try {
                            response = JSON.parse(xhr.responseText);
                        } catch (parseError) {
                            response = null;
                        }
                    }
                    const message = response && (
                        response._server_messages ||
                        response._error_message ||
                        response.message
                    );
                    const error = new Error(message || "The request was rejected by the server. Please review the form and try again.");
                    error.responseText = xhr && xhr.responseText;
                    reject(error);
                });
            }
        });
    }

    function showMessage(scope, message, isError) {
        const target = scope.querySelector(".portal-message");
        if (!target) return;
        target.textContent = message;
        target.classList.toggle("error", Boolean(isError));
        target.classList.toggle("success", !isError);
        target.setAttribute("role", isError ? "alert" : "status");
        target.setAttribute("aria-live", isError ? "assertive" : "polite");
        target.hidden = !message;
    }

    function reloadWithMessage(message, destination) {
        window.sessionStorage.setItem(SUCCESS_MESSAGE_KEY, message);
        window.location.assign(destination || window.location.href);
    }

    function showStoredMessage(root) {
        const message = window.sessionStorage.getItem(SUCCESS_MESSAGE_KEY);
        if (!message) return;
        window.sessionStorage.removeItem(SUCCESS_MESSAGE_KEY);
        showMessage(root, message, false);
    }

    function announceDataChange(type) {
        const detail = { type: type, timestamp: Date.now() };
        try {
            window.localStorage.setItem(DATA_CHANGED_KEY, JSON.stringify(detail));
        } catch (error) {
            console.warn("Could not notify other EventPro tabs about this update.", error);
        }
    }

    function listenForDataChanges(callback) {
        window.addEventListener("storage", function (event) {
            if (event.key !== DATA_CHANGED_KEY || !event.newValue) return;
            try {
                callback(JSON.parse(event.newValue).type);
            } catch (error) {
                console.error("Could not read the portal data update notification.", error);
            }
        });
    }

    function reloadWhenDataChanges(root, types) {
        listenForDataChanges(function (type) {
            if (types.includes(type)) window.location.reload();
        });
        window.addEventListener("pageshow", function (event) {
            if (event.persisted && root.isConnected) window.location.reload();
        });
    }

    function validationMessage(form, root) {
        const invalidFields = Array.from(form.elements).filter(function (field) {
            return field.willValidate && !field.validity.valid;
        });
        if (!invalidFields.length) return true;

        const messages = invalidFields.map(function (field) {
            const labelElement = field.labels && field.labels[0];
            const labelText = labelElement && Array.from(labelElement.childNodes)
                .filter(function (node) { return node.nodeType === Node.TEXT_NODE; })
                .map(function (node) { return node.textContent.trim(); })
                .filter(Boolean)
                .join(" ");
            const label = labelText || field.getAttribute("aria-label") || field.name || "This field";
            return label + ": " + field.validationMessage;
        });
        invalidFields[0].reportValidity();
        showMessage(root, messages.join("\n"), true);
        return false;
    }

    function errorText(error) {
        function readable(value, depth) {
            if (depth > 4 || value == null) return "";
            if (typeof value === "string") {
                try {
                    return readable(JSON.parse(value), depth + 1);
                } catch (parseError) {
                    return value.trim();
                }
            }
            if (Array.isArray(value)) {
                return value.map(function (item) {
                    return readable(item, depth + 1);
                }).filter(Boolean).join("\n");
            }
            if (typeof value === "object") {
                if (value.message) return readable(value.message, depth + 1);
                if (value._server_messages) return readable(value._server_messages, depth + 1);
            }
            return "";
        }

        const response = error && error.responseJSON;
        const message = readable(response && response._server_messages, 0) ||
            readable(response && response.message, 0) ||
            readable(error && error.message, 0);
        return message || "The request could not be completed. Please check the form and try again.";
    }

    function paymentErrorText(error) {
        const message = errorText(error);
        if (message !== "The request could not be completed. Please check the form and try again." &&
            message !== "The request was rejected by the server. Please review the form and try again.") {
            return message;
        }

        if (error && error.responseText) {
            const responseText = new DOMParser()
                .parseFromString(error.responseText, "text/html")
                .body.textContent;
            const validationError = responseText.match(
                /frappe\.exceptions\.(?:ValidationError|MandatoryError|LinkValidationError):\s*([^\r\n]+)/
            );
            if (validationError) return validationError[1].trim();
        }

        return message;
    }

    function setBusy(form, busy, label) {
        const button = form.querySelector('button[type="submit"]');
        if (!button) return;
        if (busy) {
            button.dataset.originalLabel = button.textContent;
            button.disabled = true;
            button.textContent = label || "Saving…";
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalLabel || "Save";
        }
    }

    function fillSelect(select, rows, valueField, labelField, placeholder, selected) {
        select.replaceChildren(new Option(placeholder, ""));
        rows.forEach(function (row) {
            const option = new Option(row[labelField] || row[valueField], row[valueField]);
            if (row[valueField] === selected) option.selected = true;
            select.add(option);
        });
    }

    function localToday() {
        const date = new Date();
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        return date.toISOString().slice(0, 10);
    }

    function initializeRegistrationForm(root) {
        const form = root.querySelector("#registration-form");
        if (!form) return;
        form.noValidate = true;
        const eventSelect = form.querySelector("#registration-event");
        const participantSelect = form.querySelector("#registration-participant");
        const ticketSelect = form.querySelector("#registration-ticket");
        const discountInput = form.querySelector("#registration-discount");
        const priceDisplay = form.querySelector("#registration-ticket-price");
        const totalDisplay = form.querySelector("#registration-total");
        const info = form.querySelector("#selected-event-info");
        const noEvents = form.querySelector("#no-available-events");
        let options;

        form.querySelector("#registration-date").value = localToday();
        function loadOptions() {
            return call("get_registration_options").then(function (data) {
            options = data;
            fillSelect(
                eventSelect,
                data.events,
                "name",
                "event_name",
                data.events.length ? "Select event" : "No available events"
            );
            fillSelect(participantSelect, data.participants, "name", "participant_name", "Select participant");
            noEvents.hidden = data.events.length > 0;
            return data;
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
                options = null;
                eventSelect.replaceChildren(new Option("Unable to load events", ""));
                participantSelect.replaceChildren(new Option("Unable to load participants", ""));
                fillSelect(ticketSelect, [], "name", "ticket_type_name", "Select an event first");
                updateTotal();
                noEvents.hidden = true;
                return null;
            });
        }
        loadOptions();
        listenForDataChanges(function (type) {
            if (type === "registration" || type === "event") loadOptions();
        });
        window.addEventListener("pageshow", function (event) {
            if (event.persisted && root.isConnected) loadOptions();
        });

        function selectedTicket() {
            return options && options.ticket_types.find(function (ticket) {
                return ticket.name === ticketSelect.value;
            });
        }

        function updateTotal() {
            const ticket = selectedTicket();
            const price = ticket ? Number(ticket.ticket_price || 0) : 0;
            const discount = Number(discountInput.value || 0);
            priceDisplay.value = ticket ? price.toFixed(2) : "—";
            totalDisplay.value = (price - discount).toFixed(2);
            discountInput.setCustomValidity(
                discount < 0 || discount > price ? "Discount must be between zero and the ticket price." : ""
            );
        }

        eventSelect.addEventListener("change", function () {
            const event = options && options.events.find(function (row) {
                return row.name === eventSelect.value;
            });
            info.hidden = !event;
            if (event) {
                info.textContent = [
                    event.event_category || "Event",
                    "Dates: " + (event.start_date || "—") + " – " + (event.end_date || "—"),
                    "Registration window: " + event.registration_start_date + " – " + event.registration_end_date,
                    "Registration fee: " + Number(event.registration_fee || 0).toFixed(2)
                ].join(" · ");
            }
            if (options) fillSelect(ticketSelect, options.ticket_types, "name", "ticket_type_name", "Select ticket type");
            updateTotal();
        });
        ticketSelect.addEventListener("change", updateTotal);
        discountInput.addEventListener("input", updateTotal);

        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!validationMessage(form, root)) return;
            setBusy(form, true, "Creating…");
            call("create_registration", {
                event: eventSelect.value,
                participant: participantSelect.value,
                registration_date: form.querySelector("#registration-date").value,
                ticket_type: ticketSelect.value,
                discount: discountInput.value
            }).then(function (result) {
                announceDataChange("registration");
                reloadWithMessage(
                    "Registration " + result.name + " was created.",
                    "/registrations"
                );
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
                loadOptions();
            }).finally(function () {
                setBusy(form, false);
            });
        });
    }

    function initializeRegistrationEdit(root) {
        const form = root.querySelector("#registration-edit-form");
        if (!form) return;
        form.noValidate = true;
        const name = form.dataset.name;
        const eventSelect = form.querySelector("#edit-registration-event");
        const participantSelect = form.querySelector("#edit-registration-participant");
        const ticketSelect = form.querySelector("#edit-registration-ticket");
        call("get_registration_options", { registration_name: name }).then(function (data) {
            fillSelect(eventSelect, data.events, "name", "event_name", "Select event", eventSelect.dataset.current);
            fillSelect(participantSelect, data.participants, "name", "participant_name", "Select participant", participantSelect.dataset.current);
            fillSelect(ticketSelect, data.ticket_types, "name", "ticket_type_name", "Select active ticket", ticketSelect.dataset.current);
        }).catch(function (error) {
            showMessage(root, errorText(error), true);
        });
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!validationMessage(form, root)) return;
            const values = Object.fromEntries(new FormData(form).entries());
            setBusy(form, true, "Saving…");
            call("save_registration", { name: name, fields: JSON.stringify(values) }).then(function () {
                announceDataChange("registration");
                return refreshRegistrationDetails(root).then(function () {
                    showMessage(root, "Registration changes were saved.", false);
                });
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
            }).finally(function () {
                setBusy(form, false);
            });
        });
    }

    function initializeWorkflow(root) {
        root.querySelectorAll("[data-workflow-action]").forEach(function (button) {
            button.addEventListener("click", function () {
                const action = button.dataset.workflowAction;
                if (!window.confirm("Apply the “" + action + "” workflow action?")) return;
                button.disabled = true;
                call("apply_registration_workflow", {
                    name: root.dataset.name,
                    action: action
                }).then(function () {
                    announceDataChange("registration");
                    return refreshRegistrationDetails(root).then(function () {
                        showMessage(root, "Registration workflow updated.", false);
                    });
                }).catch(function (error) {
                    showMessage(root, errorText(error), true);
                    button.disabled = false;
                });
            });
        });
    }

    function initializeRegistrationDocumentActions(root, data) {
        const actions = root.querySelector("#registration-document-actions");
        if (!actions) return;
        actions.replaceChildren();

        [
            { action: "Cancel", visible: data.can_cancel, label: "Cancel registration" },
            { action: "Delete", visible: data.can_delete, label: "Delete registration" }
        ].filter(function (item) {
            return item.visible;
        }).forEach(function (item) {
            const button = document.createElement("button");
            button.className = "portal-button danger";
            button.type = "button";
            button.dataset.registrationDocumentAction = item.action;
            button.textContent = item.label;
            button.addEventListener("click", function () {
                const confirmation = item.action === "Cancel"
                    ? "Cancel this submitted registration?"
                    : "Permanently delete this cancelled registration?";
                if (!window.confirm(confirmation)) return;
                button.disabled = true;
                call(item.action === "Cancel" ? "cancel_registration" : "delete_registration", {
                    name: root.dataset.name
                }).then(function () {
                    announceDataChange("registration");
                    if (item.action === "Delete") {
                        reloadWithMessage("Registration " + root.dataset.name + " was deleted.", "/registrations");
                        return;
                    }
                    return refreshRegistrationDetails(root).then(function () {
                        showMessage(root, "Registration was cancelled.", false);
                    });
                }).catch(function (error) {
                    showMessage(root, errorText(error), true);
                    button.disabled = false;
                });
            });
            actions.appendChild(button);
        });
        actions.hidden = !actions.childElementCount;
    }

    function refreshRegistrationDetails(root) {
        return call("get_registration_details", { name: root.dataset.name }).then(function (data) {
            const values = {
                event: data.event,
                participant: data.participant,
                registration_date: data.registration_date,
                ticket_type: data.ticket_type,
                ticket_amount: "₹" + Number(data.ticket_amount || 0).toFixed(2),
                discount: "₹" + Number(data.discount || 0).toFixed(2),
                total_amount: "₹" + Number(data.total_amount || 0).toFixed(2),
                payment_status: data.payment_status || "Unpaid",
                workflow_state: data.workflow_state || "Draft",
                docstatus: data.docstatus === 1 ? "Submitted" : data.docstatus === 2 ? "Cancelled" : "Draft",
                modified: data.modified
            };
            root.querySelectorAll("[data-registration-field]").forEach(function (element) {
                const field = element.dataset.registrationField;
                if (values[field] !== undefined) element.textContent = values[field] || "—";
            });
            const actions = root.querySelector("#registration-workflow-actions");
            if (actions) {
                actions.replaceChildren();
                (data.transitions || []).forEach(function (transition) {
                    const button = document.createElement("button");
                    button.className = "portal-button" + (transition.action === "Reject" ? " danger" : " primary");
                    button.type = "button";
                    button.dataset.workflowAction = transition.action;
                    button.textContent = transition.action;
                    actions.appendChild(button);
                });
                actions.hidden = !data.transitions || !data.transitions.length;
                initializeWorkflow(root);
            }
            initializeRegistrationDocumentActions(root, data);
            return data;
        });
    }

    function initializeParticipantForm(root) {
        const form = root.querySelector("#participant-form");
        if (!form) return;
        form.noValidate = true;
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!validationMessage(form, root)) return;
            setBusy(form, true, "Saving…");
            call("save_participant", {
                name: form.dataset.name || null,
                fields: JSON.stringify(Object.fromEntries(new FormData(form).entries()))
            }).then(function (result) {
                announceDataChange("participant");
                reloadWithMessage(
                    "Participant " + result.name + " was saved.",
                    form.dataset.name
                        ? "/participant-details?name=" + encodeURIComponent(result.name)
                        : "/participants"
                );
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
                setBusy(form, false);
            }).finally(function () {
                setBusy(form, false);
            });
        });
    }

    function initializeEventForm(root) {
        const form = root.querySelector("#event-form");
        if (!form) return;
        form.noValidate = true;
        const startDate = form.querySelector('[name="start_date"]');
        const endDate = form.querySelector('[name="end_date"]');
        function validateEventDates() {
            endDate.setCustomValidity(
                startDate.value && endDate.value && endDate.value < startDate.value
                    ? "Event End Date cannot be earlier than Start Date."
                    : ""
            );
        }
        startDate.addEventListener("input", validateEventDates);
        endDate.addEventListener("input", validateEventDates);
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            validateEventDates();
            if (!validationMessage(form, root)) return;
            setBusy(form, true, "Saving…");
            call("save_event", {
                name: form.dataset.name || null,
                fields: JSON.stringify(Object.fromEntries(new FormData(form).entries()))
            }).then(function (result) {
                announceDataChange("event");
                reloadWithMessage(
                    "Event " + result.name + " was saved.",
                    form.dataset.name
                        ? "/event-details?name=" + encodeURIComponent(result.name)
                        : "/events"
                );
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
            }).finally(function () {
                setBusy(form, false);
            });
        });
        const deleteButton = root.querySelector("#delete-event");
        if (deleteButton) {
            deleteButton.addEventListener("click", function () {
                if (!window.confirm("Delete this event? This cannot be undone.")) return;
                deleteButton.disabled = true;
                call("delete_event", { name: deleteButton.dataset.name }).then(function () {
                    announceDataChange("event");
                    window.location.href = "/events";
                }).catch(function (error) {
                    showMessage(root, errorText(error), true);
                    deleteButton.disabled = false;
                });
            });
        }
    }

    function initializeTicketTypeForm(root) {
        const form = root.querySelector("#ticket-type-form");
        if (!form) return;
        form.noValidate = true;
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            if (!validationMessage(form, root)) return;
            const fields = Object.fromEntries(new FormData(form).entries());
            fields.is_active = form.querySelector('[name="is_active"]').checked ? 1 : 0;
            setBusy(form, true, "Saving…");
            call("save_ticket_type", {
                name: form.dataset.name || null,
                fields: JSON.stringify(fields)
            }).then(function (result) {
                announceDataChange("ticket-type");
                reloadWithMessage(
                    "Ticket type was saved.",
                    form.dataset.name
                        ? "/ticket-types?name=" + encodeURIComponent(result.name)
                        : "/ticket-types"
                );
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
            }).finally(function () {
                setBusy(form, false);
            });
        });
    }

    function initializePayments(root) {
        const form = root.querySelector("#payment-form");
        function refreshPayments(message) {
            return call("get_portal_payments").then(function (rows) {
                renderPaymentRows(root, rows);
                if (message) showMessage(root, message, false);
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
            });
        }
        if (form) {
            form.noValidate = true;
            const dateInput = form.querySelector('[name="payment_date"]');
            if (!dateInput.value) dateInput.value = localToday();
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                if (!validationMessage(form, root)) return;
                const formValues = Object.fromEntries(new FormData(form).entries());
                setBusy(form, true, "Saving…");
                const request = form.dataset.name
                    ? call("save_payment", { name: form.dataset.name, fields: JSON.stringify(formValues) })
                    : call("create_payment", formValues);
                request.then(function (result) {
                    announceDataChange("payment");
                    if (!form.dataset.name) form.dataset.name = result.name;
                    return refreshPayments("Payment draft " + result.name + " was saved.");
                }).catch(function (error) {
                    showMessage(root, paymentErrorText(error), true);
                }).finally(function () {
                    setBusy(form, false);
                });
            });
        }
        refreshPayments();
        listenForDataChanges(function (type) {
            if (type === "payment") refreshPayments();
        });
        root.addEventListener("click", function (event) {
            const button = event.target.closest("[data-payment-action]");
            if (!button || !root.contains(button)) return;
            const action = button.dataset.paymentAction;
            if (!window.confirm(action === "Cancel" ? "Cancel this submitted payment?" : "Submit this payment?")) return;
            button.disabled = true;
            call("update_payment_status", { name: button.dataset.name, action: action }).then(function () {
                announceDataChange("payment");
                return refreshPayments(action === "Submit" ? "Payment submitted." : "Payment cancelled.");
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
                button.disabled = false;
            });
        });
    }

    function renderPaymentRows(root, payments) {
        const tbody = root.querySelector("#payments-table tbody");
        if (!tbody) return;
        tbody.replaceChildren();
        if (!payments.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.className = "portal-empty";
            cell.colSpan = 8;
            cell.textContent = "No payment records are available.";
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }
        payments.forEach(function (payment) {
            const row = document.createElement("tr");
            row.dataset.paymentRow = payment.name;
            const values = [payment.name, payment.registration, payment.payment_date, payment.payment_mode];
            values.forEach(function (value, index) {
                const cell = document.createElement("td");
                if (index === 1) {
                    const link = document.createElement("a");
                    link.href = "/registration-details?name=" + encodeURIComponent(payment.registration);
                    link.textContent = payment.registration || "—";
                    cell.appendChild(link);
                } else {
                    cell.textContent = value || "—";
                }
                row.appendChild(cell);
            });
            const amount = document.createElement("td");
            amount.textContent = "₹" + Number(payment.amount || 0).toFixed(2);
            row.appendChild(amount);
            const reference = document.createElement("td");
            reference.textContent = payment.transaction_reference || "—";
            row.appendChild(reference);
            const statusCell = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = "portal-badge";
            badge.textContent = payment.docstatus === 1 ? "Submitted" : payment.docstatus === 2 ? "Cancelled" : "Draft";
            statusCell.appendChild(badge);
            row.appendChild(statusCell);
            const actions = document.createElement("td");
            if (payment.docstatus === 1) {
                const view = document.createElement("a");
                view.className = "portal-button small secondary";
                view.href = "/payment-details?name=" + encodeURIComponent(payment.name);
                view.textContent = "View";
                actions.appendChild(view);
            } else if (payment.docstatus === 0 && root.dataset.canEdit === "1") {
                const edit = document.createElement("a");
                edit.className = "portal-button small secondary";
                edit.href = "/payments?name=" + encodeURIComponent(payment.name);
                edit.textContent = "Edit";
                actions.appendChild(edit);
            }
            if (payment.docstatus === 0 && root.dataset.canSubmit === "1") {
                const submit = document.createElement("button");
                submit.className = "portal-button small primary";
                submit.type = "button";
                submit.dataset.paymentAction = "Submit";
                submit.dataset.name = payment.name;
                submit.textContent = "Submit";
                actions.appendChild(submit);
            } else if (payment.docstatus === 1 && root.dataset.canCancel === "1") {
                const cancel = document.createElement("button");
                cancel.className = "portal-button small danger";
                cancel.type = "button";
                cancel.dataset.paymentAction = "Cancel";
                cancel.dataset.name = payment.name;
                cancel.textContent = "Cancel";
                actions.appendChild(cancel);
            }
            row.appendChild(actions);
            tbody.appendChild(row);
        });
    }

    function refreshSubmittedPayments(root) {
        call("get_submitted_payments").then(function (rows) {
            const tbody = root.querySelector("#submitted-payments-table tbody");
            tbody.replaceChildren();
            if (!rows.length) {
                const row = document.createElement("tr");
                const cell = document.createElement("td");
                cell.className = "portal-empty";
                cell.colSpan = 9;
                cell.textContent = "No submitted payments are available.";
                row.appendChild(cell);
                tbody.appendChild(row);
                return;
            }
            rows.forEach(function (payment) {
                const row = document.createElement("tr");
                [payment.name, payment.registration, payment.participant, payment.event,
                    payment.payment_date, payment.payment_mode, "₹" + Number(payment.amount || 0).toFixed(2),
                    "Submitted"].forEach(function (value, index) {
                    const cell = document.createElement("td");
                    if (index === 1) {
                        const link = document.createElement("a");
                        link.href = "/registration-details?name=" + encodeURIComponent(payment.registration);
                        link.textContent = payment.registration || "—";
                        cell.appendChild(link);
                    } else {
                        cell.textContent = value || "—";
                    }
                    if (index === 7) {
                        const badge = document.createElement("span");
                        badge.className = "portal-badge";
                        badge.textContent = value;
                        cell.replaceChildren(badge);
                    }
                    row.appendChild(cell);
                });
                const action = document.createElement("td");
                const link = document.createElement("a");
                link.className = "portal-button small secondary";
                link.href = "/payment-details?name=" + encodeURIComponent(payment.name);
                link.textContent = "View";
                action.appendChild(link);
                row.appendChild(action);
                tbody.appendChild(row);
            });
        }).catch(function (error) {
            showMessage(root, errorText(error), true);
        });
    }

    function initializeSearch(root, inputId, tableId, emptyId, filterSelectors) {
        const input = root.querySelector("#" + inputId);
        const table = root.querySelector("#" + tableId);
        if (!input || !table) return;
        const empty = root.querySelector("#" + emptyId);
        const filters = filterSelectors.map(function (selector) {
            return root.querySelector(selector);
        }).filter(Boolean);
        function filterRows() {
            const needle = input.value.toLowerCase().trim();
            let visible = 0;
            table.querySelectorAll("tbody tr[data-search], tbody tr[data-category]").forEach(function (row) {
                let matches = (row.dataset.search || "").includes(needle);
                filters.forEach(function (select) {
                    const attribute = select.id.includes("category") ? "category" : "status";
                    matches = matches && (!select.value || row.dataset[attribute] === select.value);
                });
                row.hidden = !matches;
                if (matches) visible++;
            });
            if (empty) empty.hidden = visible !== 0;
        }
        input.addEventListener("input", filterRows);
        filters.forEach(function (select) { select.addEventListener("change", filterRows); });
    }

    function setText(root, id, value) {
        const element = root.querySelector("#" + id);
        if (element) element.textContent = value == null ? "0" : value;
    }

    function appendCell(row, value) {
        const cell = document.createElement("td");
        cell.textContent = value || "—";
        row.appendChild(cell);
    }

    function renderRegistrationRows(root, id, registrations) {
        const tbody = root.querySelector("#" + id);
        tbody.replaceChildren();
        if (!registrations.length) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 6;
            cell.className = "portal-empty";
            cell.textContent = "No registrations are available.";
            row.appendChild(cell);
            tbody.appendChild(row);
            return;
        }
        registrations.forEach(function (item) {
            const row = document.createElement("tr");
            const idCell = document.createElement("td");
            const link = document.createElement("a");
            link.href = "/registration-details?name=" + encodeURIComponent(item.name);
            link.textContent = item.name;
            idCell.appendChild(link);
            row.appendChild(idCell);
            appendCell(row, item.participant);
            appendCell(row, item.event);
            appendCell(row, "₹" + Number(item.total_amount || 0).toFixed(2));
            appendCell(row, item.payment_status);
            appendCell(row, item.docstatus === 2 ? "Cancelled" : item.workflow_state);
            tbody.appendChild(row);
        });
    }

    function initializeManagerDashboard(root) {
        if (!root.matches('[data-portal-page="manager-dashboard"]')) return;
        function loadDashboard() {
            return call("get_manager_dashboard_data").then(function (data) {
            setText(root, "manager-total-events", data.total_events);
            setText(root, "manager-total-registrations", data.total_registrations);
            setText(root, "manager-pending-approvals", data.pending_approvals);
            setText(root, "manager-approved-registrations", data.approved_registrations);
            setText(root, "manager-rejected-registrations", data.rejected_registrations);
            setText(root, "manager-total-participants", data.total_participants);
            setText(root, "manager-total-payments", data.payments);

            renderRegistrationRows(root, "manager-pending-registrations", data.pending_registrations);
            renderRegistrationRows(root, "manager-registrations", data.recent_registrations);

            renderManagerList(root, "manager-events", data.upcoming_events, function (item) {
                return { href: "/event-details?name=" + encodeURIComponent(item.name), title: item.event_name, detail: item.start_date + " · " + (item.event_category || "") };
            });
            renderManagerList(root, "manager-payments", data.recent_payments, function (item) {
                return { href: "/payment-details?name=" + encodeURIComponent(item.name), title: item.name, detail: item.registration + " · ₹" + Number(item.amount || 0).toFixed(2) };
            });
            }).catch(function (error) {
                showMessage(root, errorText(error), true);
            });
        }
        loadDashboard();
        listenForDataChanges(function (type) {
            if (["registration", "payment", "event", "participant"].includes(type)) loadDashboard();
        });
        window.addEventListener("pageshow", function (event) {
            if (event.persisted && root.isConnected) loadDashboard();
        });
    }

    function renderManagerList(root, id, rows, map) {
        const list = root.querySelector("#" + id);
        list.replaceChildren();
        if (!rows.length) {
            const empty = document.createElement("p");
            empty.className = "portal-empty";
            empty.textContent = "No records to display.";
            list.appendChild(empty);
            return;
        }
        rows.forEach(function (row) {
            const item = map(row);
            const link = document.createElement("a");
            link.className = "portal-list-item";
            link.href = item.href;
            const title = document.createElement("strong");
            title.textContent = item.title || "—";
            const detail = document.createElement("small");
            detail.textContent = item.detail || "";
            link.append(title, detail);
            list.appendChild(link);
        });
    }

    function init() {
        if (!window.frappe || typeof frappe.call !== "function") return;
        document.querySelectorAll(".event-dashboard[data-portal-page]").forEach(function (root) {
            const page = root.dataset.portalPage;
            showStoredMessage(root);
            if (page === "new-registration") initializeRegistrationForm(root);
            if (page === "registration-details") {
                initializeRegistrationEdit(root);
                initializeWorkflow(root);
                initializeRegistrationDocumentActions(root, {
                    can_cancel: root.querySelector('[data-registration-document-action="Cancel"]') !== null,
                    can_delete: root.querySelector('[data-registration-document-action="Delete"]') !== null
                });
                listenForDataChanges(function (type) {
                    if (type === "payment") refreshRegistrationDetails(root).catch(function (error) {
                        showMessage(root, errorText(error), true);
                    });
                });
            }
            if (page === "participant-details") initializeParticipantForm(root);
            if (page === "event-details") initializeEventForm(root);
            if (page === "ticket-types") initializeTicketTypeForm(root);
            if (page === "payments") initializePayments(root);
            if (page === "manager-dashboard") initializeManagerDashboard(root);
            if (page === "submitted-payments") {
                listenForDataChanges(function (type) {
                    if (type === "payment") refreshSubmittedPayments(root);
                });
            }
            if (page === "participants") initializeSearch(root, "participant-search", "participants-table", "participant-empty-search", []);
            if (page === "events") initializeSearch(root, "event-search", "events-table", "event-empty-search", ["#event-category-filter", "#event-status-filter"]);
            if (page === "registrations") reloadWhenDataChanges(root, ["registration"]);
            if (page === "events") reloadWhenDataChanges(root, ["event", "registration"]);
            if (page === "participants") reloadWhenDataChanges(root, ["participant"]);
            if (page === "ticket-types") reloadWhenDataChanges(root, ["ticket-type"]);
        });
    }

    if (window.frappe && frappe.ready) {
        frappe.ready(init);
    } else {
        document.addEventListener("DOMContentLoaded", init);
    }
})();
