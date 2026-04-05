# 🏥 ProClinic — Hospital Management System

[![Django](https://img.shields.io/badge/Django-4.2-brightgreen?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red?logo=python)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**ProClinic** is a full-featured Hospital Management System built with **Django** and **Django REST Framework**. It supports multi-role authentication (Admin, Doctor, Patient), appointment scheduling, electronic health records, prescriptions, billing with PDF export, audit logging, and a research publications module.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start (Local)](#-quick-start-local)
- [Docker Setup](#-docker-setup)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Database Design](#-database-design)
- [Running Tests & Coverage](#-running-tests--coverage)
- [Troubleshooting](#-troubleshooting)
- [Further Docs](#-further-docs)

---

## ✨ Features

| Module | Description |
|---|---|
| **Authentication & Roles** | Role-based access (Admin, Doctor, Patient) with JWT + session auth. Argon2 password hashing. |
| **Patient Records** | Full EHR: demographics, visit history, diagnoses, allergies. |
| **Appointments** | Booking, rescheduling, cancellation with status lifecycle (SCHEDULED → COMPLETED / CANCELLED / RESCHEDULED / NO_SHOW). |
| **Prescriptions** | Create multi-item prescriptions; generate and cache PDF exports via WeasyPrint. |
| **Billing & Invoices** | Itemised invoices with UNPAID / PAID / CANCELLED lifecycle; patient self-service portal. |
| **Lab Reports** | Upload PDF lab reports (≤5 MB); pending → verified → archived status tracking. |
| **Audit Logging** | Automatic CREATE / UPDATE / DELETE logs for all key models via Django signals. |
| **Research Module** | Doctor submission → admin approval → public listing workflow. |
| **REST API** | Full JWT-secured REST API with filtering, search, ordering, and pagination. |

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser / Client                        │
└────────────────────┬──────────────────────────┬────────────────┘
                     │ Web UI (HTML)             │ REST API (JSON)
                     ▼                           ▼
┌────────────────────────────────────────────────────────────────┐
│                     Django Application Layer                    │
│                                                                 │
│  ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐   │
│  │ accounts  │  │ patients │  │  appts  │  │ prescriptions│   │
│  │ (auth)    │  │ (EHR)    │  │         │  │ + billing    │   │
│  └───────────┘  └──────────┘  └─────────┘  └──────────────┘   │
│  ┌───────────┐  ┌──────────┐  ┌─────────────────────────────┐  │
│  │   audit   │  │  publi-  │  │   api/  (DRF ViewSets,      │  │
│  │ (signals) │  │ cations  │  │   serializers, filters)     │  │
│  └───────────┘  └──────────┘  └─────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────┘
                                 │ ORM (Django)
                     ┌───────────▼──────────┐
                     │   Database (SQLite   │
                     │   or PostgreSQL)     │
                     └──────────────────────┘
```

**Request flow:**
1. Request hits Django's URL router → dispatched to a view or DRF ViewSet.
2. JWT middleware authenticates the token; `AuditUserMiddleware` extracts the actor for signals.
3. Business logic runs in the view/model layer.
4. Django signals fire `post_save` / `post_delete` → `AuditLog` rows are written automatically.
5. Response returned as HTML (web UI) or JSON (REST API).

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend framework** | Django 4.2 |
| **REST API** | Django REST Framework 3.15 |
| **Authentication** | `djangorestframework-simplejwt` (JWT) + Django sessions |
| **Database** | SQLite (dev) / PostgreSQL (prod via `psycopg2-binary`) |
| **PDF generation** | WeasyPrint 62 |
| **Filtering / search** | `django-filter` 24 |
| **Password hashing** | Argon2 (`django-argon2`) |
| **Environment config** | `django-environ` |
| **Production server** | Gunicorn |
| **Containerisation** | Docker + Docker Compose |
| **Test coverage** | `coverage.py` (79%) |

---

## 📁 Project Structure

```
ProClinic/
├── backend/                  # Django project root
│   ├── core/                 # Settings, root URLs, WSGI/ASGI
│   ├── accounts/             # Custom user model, roles, authentication views
│   ├── patients/             # Patient model, EHR, lab reports
│   ├── appointments/         # Appointment booking, slots, doctor unavailability
│   ├── prescriptions/        # Prescription creation and PDF generation
│   ├── billing/              # Invoice generation and PDF export
│   ├── publications/         # Research publications module
│   ├── audit/                # Audit trail and activity logs
│   ├── api/                  # DRF REST API (serializers, viewsets, JWT auth)
│   ├── manage.py
│   └── .env                  # Local environment variables (not committed)
├── frontend/
│   ├── templates/            # Django HTML templates
│   └── static/               # CSS, JS, images
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (Local)

### Prerequisites

- Python 3.10+
- pip
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ProClinic.git
cd ProClinic
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
# venv\Scripts\activate        # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example below into `backend/.env` and update the values:

```ini
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost
```

> **Note:** For production, set `DEBUG=False` and use a strong, random `SECRET_KEY`.

### 5. Run Database Migrations

```bash
cd backend
python manage.py migrate
```

### 6. Create a Superuser (Admin)

```bash
python manage.py createsuperuser
```

### 7. Start the Development Server

```bash
python manage.py runserver
```

Open your browser at **http://127.0.0.1:8000/**

| Portal | URL |
|---|---|
| Home | http://127.0.0.1:8000/ |
| Admin panel | http://127.0.0.1:8000/admin/ |
| Login selector | http://127.0.0.1:8000/accounts/choose-login/ |
| Dashboard | http://127.0.0.1:8000/dashboard/ |

---

## 🐳 Docker Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Build and Start Containers

```bash
docker-compose up --build
```

### 2. Run Migrations Inside the Container

```bash
docker-compose exec web python manage.py migrate
```

### 3. Create a Superuser Inside the Container

```bash
docker-compose exec web python manage.py createsuperuser
```

The application will be available at **http://localhost:8000/**

### Stopping the Containers

```bash
docker-compose down
```

> **Tip:** To reset the database volume, run `docker-compose down -v`.

---

## 🔐 Environment Variables

All environment variables are loaded from `backend/.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ Yes | — | Django secret key (use a long random string in production) |
| `DEBUG` | ✅ Yes | `False` | Enable debug mode (`True` for development only) |
| `ALLOWED_HOSTS` | ✅ Yes | `127.0.0.1,localhost` | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | ⬜ No | SQLite (default) | PostgreSQL URL, e.g. `postgres://user:pass@host:5432/dbname` |

### Generating a Secure Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🔌 API Reference

The REST API is mounted at `/api/`. All endpoints require a valid **JWT Bearer token** unless stated otherwise.

> **Full endpoint catalogue:** [`docs/api.md`](docs/api.md)

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT access + refresh token |
| `POST` | `/api/token/refresh/` | Refresh an expired access token |

```bash
# Obtain token
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpass"}'

# Use the token
curl http://127.0.0.1:8000/api/patients/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Staff API — Key Endpoints

#### Patients `/api/patients/`
| Method | Endpoint | Filters / Params |
|---|---|---|
| `GET` | `/api/patients/` | `?search=` `?first_name=` `?blood_group=` `?ordering=` `?page=` `?page_size=` |
| `POST` | `/api/patients/` | — |
| `GET/PUT/DELETE` | `/api/patients/{id}/` | — |

#### Appointments `/api/appointments/`
| Method | Endpoint | Note |
|---|---|---|
| `GET` | `/api/appointments/` | `?status=` `?doctor_id=` `?date=` `?date_from=` `?date_to=` `?search=` |
| `POST` | `/api/appointments/{id}/cancel/` | Body: `{"reason": "..."}` |
| `POST` | `/api/appointments/{id}/reschedule/` | Body: `{"new_time": "<ISO8601>"}` |

#### Prescriptions `/api/prescriptions/`
| Method | Endpoint | Note |
|---|---|---|
| `GET` | `/api/prescriptions/` | `?patient_id=` `?doctor_id=` `?search=` |
| `GET` | `/api/prescriptions/{id}/pdf/` | Returns `application/pdf` |
| `GET` | `/api/prescriptions/{id}/html-preview/` | HTML preview for template debug |

#### Publications `/api/publications/`
| Method | Endpoint | Auth |
|---|---|---|
| `GET` | `/api/publications/public-list/` | **None required** |
| `POST` | `/api/publications/{id}/approve/` | Admin only |
| `POST` | `/api/publications/{id}/reject/` | Admin only – body: `{"reason": "..."}` |

---

### Patient API `/api/patient/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patient/profile/` | View own profile |
| `PATCH` | `/api/patient/profile/` | Update own profile |
| `GET` | `/api/patient/visits/` | Visit history |
| `GET/POST` | `/api/patient/appointments/` | List / book appointments |
| `POST` | `/api/patient/appointments/{id}/reschedule/` | Reschedule |
| `POST` | `/api/patient/appointments/{id}/cancel/` | Cancel |
| `GET` | `/api/patient/prescriptions/` | List prescriptions |
| `GET` | `/api/patient/invoices/` | List invoices |
| `GET/POST` | `/api/patient/lab-reports/` | List / upload lab reports |

---

### Pagination Response Shape

All list endpoints return paginated results:

```json
{
  "count": 42,
  "next": "http://127.0.0.1:8000/api/patients/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

Query params: `?page=<n>` · `?page_size=<n>` (max 100)

---

### Web UI Endpoints

| URL | Access | Description |
|---|---|---|
| `/accounts/choose-login/` | Public | Role selection login page |
| `/accounts/login/staff/` | Public | Staff / Doctor login |
| `/accounts/login/patient/` | Public | Patient login |
| `/accounts/signup/patient/` | Public | Patient self-registration |
| `/publications/` | Public | Approved research papers |
| `/publications/<id>/` | Public | Paper detail with PDF download |
| `/publications/submit/` | Doctor | Upload a research paper |
| `/publications/my-papers/` | Doctor | Own paper status dashboard |
| `/publications/review/` | Admin | Approval panel |
| `/appointments/book/` | Patient | Book appointment |
| `/appointments/doctor/` | Doctor | Doctor's appointment list |
| `/billing/new/` | Doctor / Admin | Generate an invoice |
| `/billing/my-invoices/` | Patient | Patient invoice portal |
| `/prescriptions/add/` | Doctor | Create a prescription |
| `/audit/logs/` | Admin | Audit activity log |
| `/admin/` | Superuser | Django admin panel |

---

## 🗄 Database Design

ProClinic uses a single relational database. Below is the high-level entity map.

```
CustomUser
  ├── [1:N] → Patient          (doctor creates, patient owns via user FK)
  ├── [1:N] → Appointment      (as doctor or created_by)
  ├── [1:N] → Prescription     (as doctor)
  ├── [1:N] → Publication      (as doctor / approved_by)
  └── [1:N] → AuditLog        (as actor)

Patient
  ├── [1:N] → Visit
  ├── [1:N] → LabReport
  ├── [1:N] → Appointment
  ├── [1:N] → Prescription
  └── [1:N] → Invoice

Appointment
  ├── [1:1] → Visit            (optional)
  └── [1:1] → Invoice          (optional)

Prescription
  ├── [1:N] → PrescriptionItem
  └── FK    → Visit            (optional)

Invoice
  └── [1:N] → InvoiceItem

Publication
  └── FK    → CustomUser (approved_by, nullable)

AuditLog
  └── FK    → CustomUser (actor, nullable)
```

> Full schema documentation: [`docs/models.md`](docs/models.md)

---

## 🧪 Running Tests & Coverage

**Current coverage: 79%** (113 tests)

### Run All Tests

```bash
cd backend
python manage.py test
```

### Run the Extended Test Suite

```bash
python manage.py test api api.tests_extended
```

### Run Tests for a Specific App

```bash
python manage.py test api
python manage.py test patients
python manage.py test appointments
```

### Run with Coverage

```bash
pip install coverage
coverage run manage.py test
coverage report -m
```

Generate an HTML coverage report:
```bash
coverage html
# Open htmlcov/index.html in your browser
```

---

## 🔧 Troubleshooting

### `ModuleNotFoundError: No module named 'rest_framework'`

You are running the project outside the virtual environment. Activate it first:

```bash
source venv/bin/activate       # Linux / macOS
# venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

---

### Database Errors / `OperationalError: no such table`

Migrations have not been applied. Run:

```bash
cd backend
python manage.py migrate
```

If you changed a model and the error persists, try:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### PDF Generation Fails (`WeasyPrint` / `OSError`)

WeasyPrint requires system-level font and rendering libraries. Install them:

**Ubuntu / Debian:**
```bash
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1
```

**macOS (Homebrew):**
```bash
brew install pango
```

Then reinstall WeasyPrint:
```bash
pip install --force-reinstall WeasyPrint==62.3
```

---

### Port 8000 Already in Use

Use a different port:

```bash
python manage.py runserver 8080
```

Or kill the process occupying port 8000:

```bash
# Linux / macOS
lsof -ti:8000 | xargs kill -9
```

---

### `django.core.exceptions.ImproperlyConfigured` (Missing SECRET_KEY)

Ensure the `.env` file exists inside the `backend/` directory and contains a `SECRET_KEY`:

```bash
ls backend/.env          # Should exist
cat backend/.env         # Should contain SECRET_KEY, DEBUG, ALLOWED_HOSTS
```

---

### Static Files Not Loading

In development, Django serves static files automatically when `DEBUG=True`. If they are missing:

```bash
python manage.py collectstatic
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 📚 Further Docs

Detailed documentation lives in the [`docs/`](docs/) folder:

| File | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, layers, request flow, signal architecture |
| [`docs/api.md`](docs/api.md) | Complete endpoint catalogue with request/response examples |
| [`docs/models.md`](docs/models.md) | All models, fields, relationships, and lifecycle notes |
| [`docs/workflow.md`](docs/workflow.md) | Step-by-step user flows: appointment, prescription, publication |

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
