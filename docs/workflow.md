# ProClinic — User Workflows

Detailed step-by-step flows for the key user journeys in ProClinic.

---

## 1. Patient Registration & First Login

```
New Patient
    │
    ├─► /accounts/signup/patient/
    │     POST: username, email, password, first_name, last_name, phone
    │     → Creates CustomUser(role=PATIENT)
    │     → Creates Patient record (linked via user FK)
    │     → Redirects to patient login
    │
    └─► /accounts/login/patient/
          → Django session auth
          → Redirected to /dashboard/
```

API equivalent:
```bash
# 1. Register
POST /accounts/signup/patient/

# 2. Obtain JWT
POST /api/token/
{ "username": "patient1", "password": "pass" }

# 3. Use token for all /api/patient/* calls
```

---

## 2. Appointment Booking (Patient)

```
Patient logs in
    │
    ├─► Browse available slots
    │     GET /appointments/api/slots/?doctor_id=3&date=2026-04-20
    │     Returns: list of free 30-min slots
    │
    └─► Book appointment
          Web:  POST /appointments/book/
                { doctor: 3, scheduled_time: "2026-04-20T09:00" }
          API:  POST /api/patient/appointments/
                { "doctor": 3, "scheduled_time": "...", "reason": "..." }
          │
          ├─► Appointment created (status=SCHEDULED)
          ├─► AuditLog: CREATE Appointment (via signal)
          └─► Redirect to appointment list / 200 OK
```

### Reschedule Flow

```
Patient requests reschedule
    │
    └─► POST /api/patient/appointments/{id}/reschedule/
          { "new_time": "2026-04-25T11:00:00Z" }
          │
          ├─► Conflict check: is doctor free at new_time?
          │     YES → appointment.reschedule(new_time)
          │             status = RESCHEDULED
          │             scheduled_time = new_time
          │             AuditLog: UPDATE Appointment
          │     NO  → 409 Conflict
          └─► 200 OK with updated appointment
```

### Cancellation Flow

```
Patient cancels
    │
    └─► POST /api/patient/appointments/{id}/cancel/
          { "reason": "Cannot attend" }
          │
          ├─► Is appointment cancellable? (status == SCHEDULED)
          │     YES → appointment.cancel(user, reason)
          │             status = CANCELLED
          │             cancelled_at = now()
          │             AuditLog: UPDATE Appointment
          │     NO  → 400 Bad Request
          └─► 200 OK
```

---

## 3. Clinical Visit & Prescription (Doctor)

```
Doctor logs in
    │
    ├─► View appointment list: GET /appointments/doctor/
    │
    └─► Open appointment: GET /appointments/doctor/{id}/
          │
          ├─► Record Visit
          │     POST /visits/ (or via admin)
          │     { patient, doctor, appointment, notes, diagnosis }
          │     → Visit created
          │     → AuditLog: CREATE Visit
          │
          └─► Create Prescription
                GET /prescriptions/add/
                Selects patient, appointment, fills items
                POST /prescriptions/add/
                │
                ├─► Prescription + PrescriptionItems created
                ├─► AuditLog: CREATE Prescription
                └─► Option: GET /api/prescriptions/{id}/pdf/
                      → WeasyPrint renders HTML → PDF response
```

---

## 4. Invoice Generation & Payment (Staff)

```
Doctor / Admin
    │
    └─► Generate invoice: GET /billing/new/
          Select patient, add line items, set total
          POST /billing/new/
          │
          ├─► Invoice(status=UNPAID) created
          ├─► InvoiceItems created
          └─► AuditLog: CREATE Invoice

Patient views invoices
    │
    └─► GET /billing/my-invoices/
          OR GET /api/patient/invoices/
          → Only their own invoices shown
```

---

## 5. Lab Report Upload & Verification

```
Doctor uploads report
    │
    └─► POST /api/patient/lab-reports/
          multipart: pdf_file, test_name, report_date
          │
          ├─► File validation:
          │     PDF only → pass
          │     > 5 MB   → 400 error
          │
          ├─► LabReport(status=pending) created
          └─► AuditLog: CREATE LabReport

Admin verifies report
    │
    └─► labreport.mark_verified(admin_user)
          status = "verified"
          verified_by = admin_user
          AuditLog: UPDATE LabReport
```

---

## 6. Research Paper Submission & Approval

```
Doctor submits paper
    │
    └─► POST /publications/submit/
          { title, abstract, authors, pdf_file }
          │
          ├─► Publication(status=PENDING) created
          ├─► AuditLog: CREATE Publication
          └─► Doctor sees paper in /publications/my-papers/
                with status badge "Pending Review"


Admin reviews paper
    │
    └─► GET /publications/review/
          Shows: pending queue, recent approved, recent rejected
          │
          ├─► APPROVE:
          │     POST /publications/{id}/approve/
          │       OR  → Web: click "Approve" button
          │
          │     publication.approve(reviewer=admin)
          │       status = APPROVED
          │       approved_by = admin
          │       approved_at = now()
          │       rejection_reason = ''
          │     AuditLog: UPDATE Publication (status: PENDING → APPROVED)
          │
          │     → Paper now visible at /publications/ (public)
          │     → Visible at /api/publications/public-list/ (no auth)
          │
          └─► REJECT:
                POST /publications/{id}/reject/
                  body: { reason: "Insufficient data" }
                  OR  → Web: expand reject form, enter reason, confirm

                publication.reject(reviewer=admin, reason="...")
                  status = REJECTED
                  rejection_reason = "Insufficient data"
                AuditLog: UPDATE Publication (status: PENDING → REJECTED)

                → Doctor sees rejection reason in /publications/my-papers/
```

---

## 7. Audit Log Review (Admin)

```
Admin
    │
    └─► GET /audit/logs/
          Displays all AuditLog entries in reverse chronological order
          Columns: Timestamp | Action | Entity | ID | Actor

          OR via Django admin:
          GET /admin/audit/auditlog/
          Filter by: action_type, entity_type, timestamp
          Search by: actor username, entity type

          → Read-only: no add / change / delete allowed in admin
```

---

## 8. Public Research Listing (Unauthenticated)

```
Public visitor
    │
    ├─► GET /publications/
    │     Lists all APPROVED papers (cards with title, authors, date)
    │     No login required
    │
    ├─► GET /publications/{id}/
    │     Full detail: abstract, authors, doctor, approval date
    │     PDF download button → serves pdf_file
    │
    └─► API: GET /api/publications/public-list/?search=cardiology
          Returns paginated APPROVED papers
          Uses minimal serializer (no admin metadata exposed)
```

---

## Permission Matrix

| Action | Admin | Doctor | Patient | Anonymous |
|---|:---:|:---:|:---:|:---:|
| View all patients | ✅ | ✅ | ❌ | ❌ |
| View own patient profile | — | — | ✅ | ❌ |
| Book appointment | ✅ | ✅ | ✅ | ❌ |
| Create prescription | ✅ | ✅ | ❌ | ❌ |
| Generate invoice | ✅ | ✅ | ❌ | ❌ |
| View own invoices | — | — | ✅ | ❌ |
| Upload lab report | ✅ | ✅ | ✅ | ❌ |
| Submit research paper | ✅ | ✅ | ❌ | ❌ |
| Approve / reject paper | ✅ | ❌ | ❌ | ❌ |
| View approved papers | ✅ | ✅ | ✅ | ✅ |
| View audit logs | ✅ | ❌ | ❌ | ❌ |
