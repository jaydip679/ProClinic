(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function showToast(message) {
    var stack = byId("pc-toast-stack");
    if (!stack) return;
    var item = document.createElement("div");
    item.className = "pc-toast";
    item.textContent = message;
    stack.appendChild(item);
    setTimeout(function () {
      item.remove();
    }, 3400);
  }

  function setFlowStep(stepName) {
    var steps = document.querySelectorAll(".pc-flow-step");
    steps.forEach(function (step) {
      step.classList.toggle("is-active", step.dataset.step === stepName);
    });
  }

  function toggleModal(id, open) {
    var modal = byId(id);
    if (!modal) return;
    modal.classList.toggle("is-open", open);
  }

  function parseTime(value) {
    return new Date(value).getTime();
  }

  function hasConflict(start, end, events) {
    var startTime = parseTime(start);
    var endTime = parseTime(end);
    return events.filter(function (event) {
      var existingStart = parseTime(event.start);
      var existingEnd = parseTime(event.end);
      return startTime < existingEnd && endTime > existingStart;
    });
  }

  var state = {
    role: "Receptionist",
    selectedAlternative: null
  };

  var roleNotes = {
    Admin: "Admin role: staff controls, audit review, and approvals are visible.",
    Doctor: "Doctor role: queue, patient view, and prescription actions are visible.",
    Receptionist: "Reception role: quick booking and check-in actions are visible.",
    Pharmacist: "Pharmacist role: dispense queue actions are visible.",
    Accountant: "Accountant role: invoice and payment actions are visible.",
    Patient: "Patient role: own appointments, helpdesk, and payment actions are visible."
  };

  function applyRolePermissions(role) {
    state.role = role;

    var preview = byId("pc-role-preview");
    if (preview) preview.textContent = role;

    var roleNote = byId("pc-role-note");
    if (roleNote) roleNote.textContent = roleNotes[role] || "Role loaded.";

    document.querySelectorAll("[data-roles]").forEach(function (item) {
      var allowedRoles = (item.dataset.roles || "")
        .split(",")
        .map(function (token) { return token.trim(); })
        .filter(Boolean);
      item.classList.toggle("pc-hidden", allowedRoles.indexOf(role) === -1);
    });
  }

  function clearInlineError(id) {
    var errorEl = byId(id);
    if (!errorEl) return;
    errorEl.textContent = "";
    errorEl.style.display = "none";
  }

  function showInlineError(id, message) {
    var errorEl = byId(id);
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.style.display = "block";
  }

  function renderConflict(overlaps, suggestions) {
    var overlapList = byId("pc-overlap-list");
    var suggestionList = byId("pc-suggestion-list");
    var conflictMessage = byId("pc-conflict-message");

    if (conflictMessage) {
      conflictMessage.textContent =
        "Appointment conflict: this slot overlaps with another appointment. " +
        "Conflicts: " +
        overlaps
          .map(function (row) {
            return row.doctor + " " + row.startLabel + "-" + row.endLabel;
          })
          .join(", ");
    }

    if (overlapList) {
      overlapList.innerHTML = overlaps
        .map(function (row) {
          return (
            "<li><strong>" +
            row.doctor +
            "</strong> | " +
            row.patient +
            " | " +
            row.startLabel +
            "-" +
            row.endLabel +
            "</li>"
          );
        })
        .join("");
    }

    if (suggestionList) {
      suggestionList.innerHTML = suggestions
        .map(function (row, index) {
          var selectedClass = index === 0 ? " is-selected" : "";
          return (
            "<button class='pc-btn pc-btn--ghost pc-alt-slot" +
            selectedClass +
            "' type='button' data-start='" +
            row.start +
            "' data-end='" +
            row.end +
            "'>" +
            row.label +
            "</button>"
          );
        })
        .join("");
    }

    state.selectedAlternative = suggestions[0] || null;
  }

  var roleButtons = document.querySelectorAll("[data-role-select]");
  roleButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var role = button.dataset.roleSelect;
      applyRolePermissions(role);
      setFlowStep("dashboard");
      showToast("Logged in as " + role + " - role landing loaded.");
    });
  });

  function goToStepIfAllowed(stepName, allowedRoles, deniedMessage) {
    if (allowedRoles.indexOf(state.role) === -1) {
      showToast(deniedMessage);
      return;
    }
    setFlowStep(stepName);
  }

  var resetFlow = byId("pc-reset-flow");
  if (resetFlow) {
    resetFlow.addEventListener("click", function () {
      clearInlineError("pc-booking-error");
      clearInlineError("pc-audit-error");
      byId("pc-audit-reason").value = "";
      toggleModal("pc-conflict-modal", false);
      toggleModal("pc-audit-modal", false);
      toggleModal("pc-helpdesk-modal", false);
      applyRolePermissions("Receptionist");
      setFlowStep("login");
    });
  }

  var sampleEvents = [
    {
      doctor: "Dr. A. Desai",
      patient: "Nitin Sharma",
      start: "2026-02-20T10:00:00",
      end: "2026-02-20T10:30:00",
      startLabel: "10:00",
      endLabel: "10:30"
    },
    {
      doctor: "Dr. A. Desai",
      patient: "Isha Patel",
      start: "2026-02-20T11:00:00",
      end: "2026-02-20T11:30:00",
      startLabel: "11:00",
      endLabel: "11:30"
    }
  ];

  var sampleSuggestions = [
    { start: "2026-02-20T10:30", end: "2026-02-20T11:00", label: "10:30 - 11:00" },
    { start: "2026-02-20T11:30", end: "2026-02-20T12:00", label: "11:30 - 12:00" },
    { start: "2026-02-20T12:00", end: "2026-02-20T12:30", label: "12:00 - 12:30" }
  ];

  var bookingForm = byId("pc-booking-form");
  if (bookingForm) {
    bookingForm.addEventListener("submit", function (event) {
      event.preventDefault();
      clearInlineError("pc-booking-error");

      var startInput = byId("pc-book-start");
      var endInput = byId("pc-book-end");
      if (!startInput || !endInput || !startInput.value || !endInput.value) {
        showInlineError("pc-booking-error", "Please choose appointment start and end times.");
        return;
      }

      if (parseTime(endInput.value) <= parseTime(startInput.value)) {
        showInlineError("pc-booking-error", "End time must be after start time.");
        return;
      }

      var overlaps = hasConflict(startInput.value, endInput.value, sampleEvents);
      if (overlaps.length) {
        renderConflict(overlaps, sampleSuggestions);
        toggleModal("pc-conflict-modal", true);
        return;
      }

      showToast("Appointment confirmed - email sent to patient@example.com");
      if (state.role === "Receptionist") {
        setFlowStep("checkin");
      } else {
        setFlowStep("dashboard");
      }
    });
  }

  function addMedicineRow() {
    var medicineBody = byId("pc-proto-medicine-body");
    if (!medicineBody) return;

    var row = document.createElement("tr");
    row.innerHTML =
      "<td><input class='pc-input' placeholder='Medicine name' /></td>" +
      "<td><input class='pc-input' placeholder='500mg' /></td>" +
      "<td><input class='pc-input pc-qty' type='number' min='1' value='1' /></td>" +
      "<td><input class='pc-input' placeholder='1-0-1 after food' /></td>" +
      "<td><input class='pc-input' placeholder='5 days' /></td>";
    medicineBody.appendChild(row);
  }

  var addMedicine = byId("pc-proto-add-medicine");
  if (addMedicine) {
    addMedicine.addEventListener("click", addMedicineRow);
  }

  var lineItems = [
    { label: "Consultation", amount: 500 },
    { label: "Medicines", amount: 800 }
  ];

  function renderInvoiceSummary() {
    var subTotal = lineItems.reduce(function (sum, row) {
      return sum + row.amount;
    }, 0);
    var gst = Math.round(subTotal * 0.18);
    var total = subTotal + gst;

    var list = byId("pc-line-items");
    if (list) {
      list.innerHTML = lineItems
        .map(function (row) {
          return "<li>" + row.label + " <strong>₹" + row.amount + "</strong></li>";
        })
        .join("");
    }

    var gstEl = byId("pc-gst");
    var totalEl = byId("pc-grand-total");
    if (gstEl) gstEl.textContent = "₹" + gst;
    if (totalEl) totalEl.textContent = "₹" + total;
  }

  function appendHelpdeskMessage(text, sender) {
    var log = byId("pc-helpdesk-log");
    if (!log) return;

    var bubble = document.createElement("div");
    bubble.className = "pc-chat-msg " + (sender === "user" ? "pc-chat-msg--user" : "pc-chat-msg--bot");
    bubble.textContent = text;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
  }

  function getHelpdeskReply(inputText) {
    var text = inputText.toLowerCase();
    if (text.indexOf("reschedule") !== -1 || text.indexOf("appointment") !== -1) {
      return "You can reschedule from Appointments -> Upcoming. Suggested next slots are shown if conflicts exist.";
    }
    if (text.indexOf("invoice") !== -1 || text.indexOf("payment") !== -1 || text.indexOf("bill") !== -1) {
      return "Invoice payments support UPI/Card. GST at 18% is applied automatically before checkout.";
    }
    if (text.indexOf("prescription") !== -1 || text.indexOf("rx") !== -1) {
      return "Open Prescriptions in your portal and use Download PDF for the latest signed copy.";
    }
    return "I can help with appointments, prescriptions, invoices, and navigation. Ask a specific question for faster help.";
  }

  function sendHelpdeskMessage(text) {
    if (!text || !text.trim()) return;
    appendHelpdeskMessage(text.trim(), "user");
    var reply = getHelpdeskReply(text);
    setTimeout(function () {
      appendHelpdeskMessage(reply, "bot");
    }, 250);
  }

  var helpdeskInput = byId("pc-helpdesk-input");
  if (helpdeskInput) {
    helpdeskInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        sendHelpdeskMessage(helpdeskInput.value);
        helpdeskInput.value = "";
      }
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target;

    if (target.closest("#pc-go-booking")) {
      goToStepIfAllowed("booking", ["Receptionist", "Patient", "Admin"], "Booking is hidden for your role.");
      return;
    }

    if (target.closest("#pc-go-checkin")) {
      goToStepIfAllowed("checkin", ["Receptionist"], "Check-in is available only for reception users.");
      return;
    }

    if (target.closest("#pc-go-doctor-visit")) {
      goToStepIfAllowed("doctor-visit", ["Doctor"], "Doctor visit actions are hidden for your role.");
      return;
    }

    if (target.closest("#pc-go-invoice")) {
      goToStepIfAllowed("invoice", ["Accountant", "Admin"], "Invoice tools are hidden for your role.");
      return;
    }

    if (target.closest("#pc-go-audit")) {
      goToStepIfAllowed("audit", ["Admin"], "Audit actions are hidden for your role.");
      return;
    }

    if (target.closest("#pc-simulate-restricted")) {
      if (state.role === "Admin") {
        showToast("Access granted for Admin.");
      } else {
        window.location.href = "/permission-denied/";
      }
      return;
    }

    if (target.closest("#pc-cancel-booking")) {
      setFlowStep("dashboard");
      return;
    }

    if (target.closest("#pc-close-modal")) {
      toggleModal("pc-conflict-modal", false);
      return;
    }

    var altSlot = target.closest(".pc-alt-slot");
    if (altSlot) {
      document.querySelectorAll(".pc-alt-slot").forEach(function (button) {
        button.classList.remove("is-selected");
      });
      altSlot.classList.add("is-selected");
      state.selectedAlternative = {
        start: altSlot.dataset.start,
        end: altSlot.dataset.end,
        label: altSlot.textContent
      };
      return;
    }

    if (target.closest("#pc-confirm-slot")) {
      if (!state.selectedAlternative) {
        showToast("Pick an alternative slot first.");
        return;
      }
      byId("pc-book-start").value = state.selectedAlternative.start;
      byId("pc-book-end").value = state.selectedAlternative.end;
      toggleModal("pc-conflict-modal", false);
      showToast("Alternative slot selected. Confirm to continue.");
      return;
    }

    if (target.closest("#pc-request-override")) {
      if (state.role !== "Admin") {
        showToast("Override request sent to Admin for approval.");
      } else {
        showToast("Override approved by Admin.");
      }
      toggleModal("pc-conflict-modal", false);
      return;
    }

    if (target.closest("#pc-checkin-submit")) {
      var patient = byId("pc-checkin-patient").value || "Patient";
      var room = byId("pc-checkin-room").value || "Room";
      showToast("Check-in complete: " + patient + " assigned to " + room + ".");
      setFlowStep("dashboard");
      return;
    }

    if (target.closest("#pc-save-prescription")) {
      var quantities = document.querySelectorAll("#pc-proto-medicine-body .pc-qty");
      var invalidQty = Array.prototype.some.call(quantities, function (input) {
        return !input.value || Number(input.value) <= 0;
      });

      if (invalidQty) {
        showToast("Quantity must be at least 1 for every medicine line.");
        return;
      }

      var severeAllergy = byId("pc-allergy-flag");
      if (severeAllergy && severeAllergy.checked) {
        showToast("Allergy warning: Severe Penicillin reaction. Prescription blocked.");
        return;
      }

      showToast("Prescription saved - PDF ready to download.");
      setFlowStep("invoice");
      return;
    }

    if (target.closest("#pc-preview-invoice")) {
      window.open("/design-system/invoice-a4/", "_blank", "noopener");
      return;
    }

    if (target.closest("#pc-create-invoice")) {
      showToast("Invoice created - GST (18%) applied.");
      setFlowStep("payment");
      return;
    }

    if (target.closest("#pc-pay-now")) {
      showToast("Payment successful. Receipt emailed to patient.");
      setFlowStep("dashboard");
      return;
    }

    if (target.closest("#pc-open-audit-confirm")) {
      toggleModal("pc-audit-modal", true);
      return;
    }

    if (target.closest("#pc-cancel-audit")) {
      toggleModal("pc-audit-modal", false);
      return;
    }

    if (target.closest("#pc-confirm-audit")) {
      clearInlineError("pc-audit-error");
      var reason = byId("pc-audit-reason").value.trim();
      if (reason.length < 5) {
        showInlineError("pc-audit-error", "Reason is required (minimum 5 characters).");
        return;
      }
      toggleModal("pc-audit-modal", false);
      showToast("Audit entry created with reason: " + reason);
      setFlowStep("dashboard");
      return;
    }

    if (target.closest("#pc-open-helpdesk")) {
      toggleModal("pc-helpdesk-modal", true);
      if (!byId("pc-helpdesk-log").children.length) {
        appendHelpdeskMessage("Hi, I am ProClinic Assist. Ask about appointments, prescriptions, or billing.", "bot");
      }
      return;
    }

    if (target.closest("#pc-close-helpdesk")) {
      toggleModal("pc-helpdesk-modal", false);
      return;
    }

    if (target.closest("#pc-helpdesk-send")) {
      sendHelpdeskMessage(byId("pc-helpdesk-input").value);
      byId("pc-helpdesk-input").value = "";
      return;
    }

    var suggestion = target.closest(".pc-helpdesk-suggest");
    if (suggestion) {
      sendHelpdeskMessage(suggestion.dataset.prompt || "");
      return;
    }
  });

  renderInvoiceSummary();
  applyRolePermissions("Receptionist");
  setFlowStep("login");
})();
