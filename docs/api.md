# ProClinic — API Reference

All REST endpoints are mounted under `/api/`. Authenticated endpoints require a JWT `Bearer` token in the `Authorization` header.

---

## Authentication

### Obtain Token

```http
POST /api/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response `200 OK`:**
```json
{
  "access":  "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

### Refresh Token

```http
POST /api/token/refresh/
Content-Type: application/json

{ "refresh": "<jwt_refresh_token>" }
```

**Response `200 OK`:**
```json
{ "access": "<new_jwt_access_token>" }
```

---

## Pagination

All list endpoints return paginated results with default page size of 20 (max 100).

```json
{
  "count": 84,
  "next": "http://localhost:8000/api/patients/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

| Param | Description |
|---|---|
| `?page=<n>` | Page number (1-indexed) |
| `?page_size=<n>` | Items per page (max 100 for standard endpoints, 200 for publications) |

---

## Common Query Params

All list endpoints support:

| Param | Example | Description |
|---|---|---|
| `?search=<text>` | `?search=alice` | Full-text search across indexed fields |
| `?ordering=<field>` | `?ordering=-created_at` | Sort ascending or descending (prefix `-`) |
| `?page=<n>` | `?page=2` | Page number |
| `?page_size=<n>` | `?page_size=50` | Results per page |

---

## Patients — `/api/patients/`

> **Auth:** Staff / Doctor only

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/patients/` | List all patients |
| `POST` | `/api/patients/` | Create a patient record |
| `GET` | `/api/patients/{id}/` | Retrieve a patient |
| `PUT` | `/api/patients/{id}/` | Full update |
| `PATCH` | `/api/patients/{id}/` | Partial update |
| `DELETE` | `/api/patients/{id}/` | Delete |

### Filter Params

| Param | Description |
|---|---|
| `?first_name=<str>` | Filter by first name (case-insensitive contains) |
| `?last_name=<str>` | Filter by last name |
| `?blood_group=<str>` | Exact match — e.g. `A+`, `O-` |
| `?gender=<str>` | Exact match — `Male`, `Female` |
| `?search=<str>` | Search across first name, last name, email |

### Example Request

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/patients/?search=alice&blood_group=A%2B&ordering=-created_at"
```

---

## Appointments — `/api/appointments/`

> **Auth:** Staff / Doctor only

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/appointments/` | List appointments |
| `POST` | `/api/appointments/` | Create appointment |
| `GET` | `/api/appointments/{id}/` | Retrieve |
| `PUT/PATCH` | `/api/appointments/{id}/` | Update |
| `DELETE` | `/api/appointments/{id}/` | Delete |
| `POST` | `/api/appointments/{id}/cancel/` | Cancel with reason |
| `POST` | `/api/appointments/{id}/reschedule/` | Reschedule to new time |

### Filter Params

| Param | Description |
|---|---|
| `?status=SCHEDULED` | Filter by status (`SCHEDULED`, `COMPLETED`, `CANCELLED`, `RESCHEDULED`, `NO_SHOW`) |
| `?doctor_id=<int>` | Filter by doctor's user ID |
| `?patient_id=<int>` | Filter by patient record ID |
| `?date=YYYY-MM-DD` | Exact date |
| `?date_from=YYYY-MM-DD` | Appointments from this date (inclusive) |
| `?date_to=YYYY-MM-DD` | Appointments up to this date (inclusive) |

### Cancel Action

```http
POST /api/appointments/{id}/cancel/
Authorization: Bearer <token>
Content-Type: application/json

{ "reason": "Patient called to cancel." }
```

**Response `200 OK`:** Updated appointment object.

**Error `400`:** If appointment is not cancellable (already COMPLETED or CANCELLED).

### Reschedule Action

```http
POST /api/appointments/{id}/reschedule/
Authorization: Bearer <token>
Content-Type: application/json

{ "new_time": "2026-04-15T10:00:00Z" }
```

**Response `200 OK`:** Updated appointment object.

**Error `400`:** If `new_time` is missing or invalid, or if the doctor already has a booking at that time.

---

## Prescriptions — `/api/prescriptions/`

> **Auth:** Staff / Doctor only

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/prescriptions/` | List prescriptions |
| `POST` | `/api/prescriptions/` | Create prescription |
| `GET` | `/api/prescriptions/{id}/` | Retrieve |
| `GET` | `/api/prescriptions/{id}/pdf/` | Download prescription as PDF |
| `GET` | `/api/prescriptions/{id}/html-preview/` | HTML preview |

### Filter Params

| Param | Description |
|---|---|
| `?patient_id=<int>` | Filter by patient |
| `?doctor_id=<int>` | Filter by doctor |
| `?created_from=YYYY-MM-DD` | Created on or after |
| `?created_to=YYYY-MM-DD` | Created on or before |
| `?search=<text>` | Search medicine names (via items) |

---

## Invoices — `/api/invoices/`

> **Auth:** Staff / Doctor only

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/invoices/` | List invoices |
| `POST` | `/api/invoices/` | Create invoice |
| `GET` | `/api/invoices/{id}/` | Retrieve |
| `PUT/PATCH` | `/api/invoices/{id}/` | Update |

### Filter Params

| Param | Description |
|---|---|
| `?status=UNPAID` | `UNPAID`, `PAID`, `CANCELLED` |
| `?patient_id=<int>` | Filter by patient |
| `?created_from=YYYY-MM-DD` | Filter by creation date |
| `?created_to=YYYY-MM-DD` | Filter by creation date |

---

## Publications — `/api/publications/`

> **Auth:** Staff for CRUD; **None** for `public-list`

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/api/publications/` | Staff | List all publications (any status) |
| `POST` | `/api/publications/` | Staff | Create a publication |
| `GET` | `/api/publications/{id}/` | Staff | Retrieve |
| `GET` | `/api/publications/public-list/` | **None** | Approved papers only |
| `POST` | `/api/publications/{id}/approve/` | Admin | Approve and publish |
| `POST` | `/api/publications/{id}/reject/` | Admin | Reject with reason |

### Filter Params (staff list)

| Param | Description |
|---|---|
| `?status=APPROVED` | `DRAFT`, `PENDING`, `APPROVED`, `REJECTED` |
| `?authors=<str>` | Contains match on authors field |
| `?year=<YYYY>` | Filter by year of creation |
| `?search=<str>` | Search title, abstract, authors |

### Public List

```http
GET /api/publications/public-list/?search=cardiology
```

No authentication required. Returns only `APPROVED` publications using the minimal public serializer (no admin notes, rejection reasons, or metadata).

### Approve Action

```http
POST /api/publications/{id}/approve/
Authorization: Bearer <admin_token>
```

**Response `200 OK`:** Full publication object with `status: "APPROVED"`, `approved_by`, `approved_at`.

**Error `400`:** Already approved.
**Error `403`:** Non-admin caller.

### Reject Action

```http
POST /api/publications/{id}/reject/
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "reason": "Insufficient citations." }
```

**Response `200 OK`:** Full publication object with `status: "REJECTED"`, `rejection_reason`.

---

## Patient API — `/api/patient/`

> **Auth:** Patient role only. Each patient sees only their own data.

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/patient/profile/` | Own patient profile |
| `PATCH` | `/api/patient/profile/` | Update own profile |
| `GET` | `/api/patient/visits/` | Visit history |
| `GET` | `/api/patient/appointments/` | Own appointments |
| `POST` | `/api/patient/appointments/` | Book appointment |
| `POST` | `/api/patient/appointments/{id}/reschedule/` | Reschedule |
| `POST` | `/api/patient/appointments/{id}/cancel/` | Cancel |
| `GET` | `/api/patient/prescriptions/` | Own prescriptions |
| `GET` | `/api/patient/prescriptions/{id}/` | Prescription detail |
| `GET` | `/api/patient/invoices/` | Own invoices |
| `GET` | `/api/patient/lab-reports/` | Own lab reports |
| `POST` | `/api/patient/lab-reports/` | Upload lab report (PDF ≤5 MB) |

### Book Appointment Example

```http
POST /api/patient/appointments/
Authorization: Bearer <patient_token>
Content-Type: application/json

{
  "doctor": 3,
  "scheduled_time": "2026-04-20T09:00:00Z",
  "reason": "Annual check-up"
}
```

**Error `409`:** Doctor already booked at that time.

### Upload Lab Report

```http
POST /api/patient/lab-reports/
Authorization: Bearer <patient_token>
Content-Type: multipart/form-data

pdf_file=<file.pdf>
test_name=CBC
report_date=2026-04-01
```

**Error `400`:** File > 5 MB or non-PDF type.

---

## HTTP Status Codes

| Code | Meaning |
|---|---|
| `200 OK` | Successful read or action |
| `201 Created` | Resource created |
| `400 Bad Request` | Validation error or invalid input |
| `401 Unauthorized` | Missing or invalid JWT token |
| `403 Forbidden` | Authenticated but insufficient permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Business rule violation (e.g. double-booking) |
