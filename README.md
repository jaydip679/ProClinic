# 🏥 ProClinic — Hospital Management System

[![Django](https://img.shields.io/badge/Django-4.2-brightgreen?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red?logo=python)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**ProClinic** is a full-featured Hospital Management System built with **Django** and **Django REST Framework**. It supports multi-role authentication (Admin, Doctor, Patient), appointment scheduling, electronic health records, prescriptions, billing with PDF export, audit logging, and a research publications module.

---

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Quick Start (Local)](#-quick-start-local)
- [Docker Setup](#-docker-setup)
- [Environment Variables](#-environment-variables)
- [API Reference](#-api-reference)
- [Running Tests](#-running-tests)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Module | Description |
|---|---|
| **Authentication & Roles** | Role-based access for Admin, Doctor, and Patient with JWT + session auth |
| **Patient Records** | Full EHR including visit history, demographics, and lab reports |
| **Appointments** | Booking, rescheduling, cancellation, and doctor availability management |
| **Prescriptions** | Create and manage prescriptions; generate PDF exports via WeasyPrint |
| **Billing & Invoices** | Generate itemised invoices; PDF export; patient invoice portal |
| **Lab Reports** | Upload and retrieve lab reports linked to patient visits |
| **Audit Logging** | System-wide activity log for all sensitive operations |
| **Research Module** | Manage and browse clinical research publications |
| **REST API** | Full JWT-secured REST API built with Django REST Framework |

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

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT access + refresh token |
| `POST` | `/api/token/refresh/` | Refresh access token |

**Example — obtain a token:**
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

Use the returned `access` token in subsequent requests:
```bash
-H "Authorization: Bearer <access_token>"
```

---

### Staff API (Doctor / Admin)

#### Patients

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patients/` | List all patients |
| `POST` | `/api/patients/` | Create a new patient record |
| `GET` | `/api/patients/{id}/` | Retrieve a specific patient |
| `PUT` | `/api/patients/{id}/` | Update a patient record |
| `DELETE` | `/api/patients/{id}/` | Delete a patient record |

#### Appointments

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/appointments/` | List all appointments |
| `POST` | `/api/appointments/` | Create an appointment |
| `GET` | `/api/appointments/{id}/` | Retrieve an appointment |
| `PUT` | `/api/appointments/{id}/` | Update an appointment |
| `DELETE` | `/api/appointments/{id}/` | Delete an appointment |

#### Prescriptions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/prescriptions/` | List all prescriptions |
| `POST` | `/api/prescriptions/` | Create a prescription |
| `GET` | `/api/prescriptions/{id}/` | Retrieve a prescription |

#### Invoices

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/invoices/` | List all invoices |
| `POST` | `/api/invoices/` | Create an invoice |
| `GET` | `/api/invoices/{id}/` | Retrieve an invoice |

#### Publications

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/publications/` | List research publications |
| `POST` | `/api/publications/` | Create a publication |
| `GET` | `/api/publications/{id}/` | Retrieve a publication |

---

### Patient-Facing API (`/api/patient/`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patient/profile/` | View own profile |
| `GET` | `/api/patient/visits/` | List own visit history |
| `GET` | `/api/patient/appointments/` | List own appointments |
| `POST` | `/api/patient/appointments/` | Book an appointment |
| `POST` | `/api/patient/appointments/{id}/reschedule/` | Reschedule an appointment |
| `POST` | `/api/patient/appointments/{id}/cancel/` | Cancel an appointment |
| `GET` | `/api/patient/prescriptions/` | List own prescriptions |
| `GET` | `/api/patient/prescriptions/{id}/` | View a prescription |
| `GET` | `/api/patient/invoices/` | List own invoices |
| `GET` | `/api/patient/lab-reports/` | List own lab reports |
| `POST` | `/api/patient/lab-reports/` | Upload a lab report |

---

### Web UI Endpoints

| URL | Access | Description |
|---|---|---|
| `/accounts/choose-login/` | Public | Role selection login page |
| `/accounts/login/staff/` | Public | Staff / Doctor login |
| `/accounts/login/patient/` | Public | Patient login |
| `/accounts/signup/patient/` | Public | Patient self-registration |
| `/appointments/book/` | Authenticated | Book appointment (patient) |
| `/appointments/doctor/` | Doctor | Doctor's appointment list |
| `/billing/new/` | Doctor / Admin | Generate an invoice |
| `/billing/my-invoices/` | Patient | Patient invoice portal |
| `/prescriptions/add/` | Doctor | Create a prescription |
| `/audit/logs/` | Admin | Audit activity log |
| `/admin/` | Superuser | Django admin panel |

---

## 🧪 Running Tests

### Run All Tests

```bash
cd backend
python manage.py test
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

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
