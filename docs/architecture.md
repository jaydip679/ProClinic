# ProClinic — System Architecture

## Overview

ProClinic is a **monolithic Django application** structured around self-contained Django apps, each owning its models, views, URLs, forms, and admin. A shared `api/` package exposes a RESTful interface over all domains using Django REST Framework.

---

## Layer Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
│                                                                      │
│   ┌──────────────────┐           ┌──────────────────────────────┐    │
│   │  Web Browser     │           │  API Client (mobile / curl)  │    │
│   │  (HTML / CSS)    │           │  (JSON + JWT)                │    │
│   └────────┬─────────┘           └──────────────┬───────────────┘    │
└────────────┼─────────────────────────────────────┼──────────────────┘
             │ HTTP                                 │ HTTP
             ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Django Application                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                    WSGI / Gunicorn                          │     │
│  └─────────────────────┬───────────────────────────────────────┘     │
│                        │                                             │
│  ┌─────────────────────▼───────────────────────────────────────┐     │
│  │                  URL Router (core/urls.py)                  │     │
│  └──┬──────────────────────────┬──────────────────────────┬────┘     │
│     │ /api/*                   │ /accounts/*              │ /*        │
│     ▼                          ▼                          ▼           │
│  ┌──────────┐   ┌─────────────────────────┐  ┌─────────────────┐    │
│  │ DRF      │   │  Authentication Views   │  │  App Views      │    │
│  │ ViewSets │   │  (login/logout/signup)  │  │  (HTML render)  │    │
│  └────┬─────┘   └─────────────────────────┘  └────────┬────────┘    │
│       │                                                │             │
│  ┌────▼────────────────────────────────────────────────▼───────┐     │
│  │              Business Logic Layer (Models + Managers)       │     │
│  │                                                             │     │
│  │  accounts  patients  appointments  prescriptions  billing   │     │
│  │  publications  audit                                        │     │
│  └────────────────────────────┬────────────────────────────────┘     │
│                               │ Django Signals (post_save/delete)    │
│                               │                                      │
│  ┌────────────────────────────▼────────────────────────────────┐     │
│  │                 Audit App (audit/signals.py)                │     │
│  │   Captures CREATE / UPDATE / DELETE for all key entities    │     │
│  │   Actor sourced from AuditUserMiddleware (threading.local)  │     │
│  └────────────────────────────┬────────────────────────────────┘     │
└───────────────────────────────┼──────────────────────────────────────┘
                                │ Django ORM
                    ┌───────────▼──────────────┐
                    │  Database                │
                    │  SQLite (dev)            │
                    │  PostgreSQL (prod)       │
                    └──────────────────────────┘
```

---

## Django App Responsibilities

| App | Responsibility |
|---|---|
| `core` | Project settings, root URL config, base views (dashboard, home), WSGI/ASGI |
| `accounts` | `CustomUser` model (role-aware), login/logout/signup views |
| `patients` | `Patient`, `Visit`, `LabReport` models and staff management views |
| `appointments` | `Appointment`, `DoctorUnavailability`; booking, cancel, reschedule logic |
| `prescriptions` | `Prescription`, `PrescriptionItem`; PDF generation via WeasyPrint |
| `billing` | `Invoice`, `InvoiceItem`; invoice generation and patient portal |
| `publications` | Research paper submission → admin approval → public listing |
| `audit` | `AuditLog` model, signals, middleware, log viewer |
| `api` | DRF ViewSets, serializers, filters, pagination, JWT auth endpoints |

---

## Authentication Architecture

```
Login Request
     │
     ├── /accounts/login/staff/   → Django session auth (staff / doctors)
     │
     └── /api/token/              → JWT pair (access + refresh)
                                        │
                                        └── access token in Authorization header
                                            for all /api/* calls
```

**Role system** (`CustomUser.role`):
- `ADMIN` — full access; can approve/reject publications, manage users
- `DOCTOR` — clinical access; appointments, prescriptions, own publications
- `PATIENT` — self-service only; book appointments, view own records

---

## Audit Signal Architecture

```
HTTP Request
     │
     └── AuditUserMiddleware ──► stores user in threading.local
                                              │
     Model.save() ──► pre_save signal ───────►│
                   │   (snapshot old values)  │
                   └──► post_save signal ─────►│ get_current_user()
                         (diff old vs new)     │          │
                                               └─► AuditLog.objects.create(
                                                     actor=user,
                                                     action_type=CREATE/UPDATE,
                                                     entity_type="Patient",
                                                     entity_id=pk,
                                                     changes={diff}
                                                   )
```

Tracked models: `Patient`, `Appointment`, `Prescription`, `Invoice`, `Publication`, `LabReport`

---

## Request / Response Flow (REST API)

```
Client → JWT Token → API Request
                          │
                     URL Router
                          │
                     ViewSet.dispatch()
                          │
                     ┌────▼────────────────────────┐
                     │ Permission check            │
                     │ IsAuthenticated + IsStaff   │
                     │ (or AllowAny for public-list│
                     └────┬────────────────────────┘
                          │
                     ┌────▼────────────────────────┐
                     │ Filter backends              │
                     │ DjangoFilterBackend          │
                     │ SearchFilter                 │
                     │ OrderingFilter               │
                     └────┬────────────────────────┘
                          │
                     ┌────▼────────────────────────┐
                     │ Pagination                  │
                     │ StandardResultsSetPagination│
                     │ (page_size=20, max=100)      │
                     └────┬────────────────────────┘
                          │
                     Serializer → JSON Response
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Monolithic structure | Simpler deployment, easier cross-app queries, appropriate for hospital scale |
| SQLite in dev / PostgreSQL in prod | Zero-dependency dev setup; production-grade with psycopg2 |
| Thread-local for audit actor | Django signals have no request context; thread-local is the standard pattern |
| `update_fields` on model methods | Avoids overwriting concurrent writes; minimal DB updates |
| Exception-safe audit writes | Signal failures must never break the main transaction |
| Separate patient-facing API (`/api/patient/`) | Strong isolation between patient self-service and staff CRUD |
