"""
Comprehensive tests for the patient-facing API endpoints.

Covers:
  - Profile access (own vs. other patient)
  - Appointment booking, double-booking, reschedule, cancel
  - Prescription read-only access
  - Invoice read-only access
  - Lab report upload validation & ownership
  - Permission checks (401/403 for unauthorized access)
"""

import io
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import CustomUser
from appointments.models import Appointment
from billing.models import Invoice, InvoiceItem
from patients.models import LabReport, Patient, Visit
from prescriptions.models import Prescription, PrescriptionItem


class PatientTestBase(TestCase):
    """Shared setup for patient API tests."""

    @classmethod
    def setUpTestData(cls):
        # Create a doctor
        cls.doctor = CustomUser.objects.create_user(
            username='dr_smith', password='testpass123',
            email='dr@proclinic.test', role='DOCTOR',
            first_name='John', last_name='Smith',
        )

        # Create patient user + profile
        cls.patient_user = CustomUser.objects.create_user(
            username='patient1', password='testpass123',
            email='patient1@test.com', role='PATIENT',
            first_name='Alice', last_name='Doe',
            phone_number='9999999999',
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
            first_name='Alice', last_name='Doe',
            date_of_birth='1990-05-15', gender='Female',
            blood_group='A+', contact_number='9999999999',
            email='patient1@test.com', address='123 Main St',
            allergies='Penicillin',
        )

        # Create second patient user + profile
        cls.patient_user2 = CustomUser.objects.create_user(
            username='patient2', password='testpass123',
            email='patient2@test.com', role='PATIENT',
            first_name='Bob', last_name='Roe',
            phone_number='8888888888',
        )
        cls.patient2 = Patient.objects.create(
            user=cls.patient_user2,
            first_name='Bob', last_name='Roe',
            date_of_birth='1985-01-10', gender='Male',
            blood_group='B+', contact_number='8888888888',
            email='patient2@test.com', address='456 Oak Ave',
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_patient(self, user=None):
        self.client.force_authenticate(user=user or self.patient_user)

    def authenticate_doctor(self):
        self.client.force_authenticate(user=self.doctor)

    def _future_time(self, hours=24):
        return timezone.now() + timedelta(hours=hours)


# ─── Profile Tests ────────────────────────────────────────────────────────────

class PatientProfileTests(PatientTestBase):

    def test_unauthenticated_returns_401(self):
        resp = self.client.get('/api/patient/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_doctor_returns_403(self):
        self.authenticate_doctor()
        resp = self.client.get('/api/patient/profile/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_own_profile(self):
        self.authenticate_patient()
        resp = self.client.get('/api/patient/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['first_name'], 'Alice')
        self.assertEqual(resp.data['blood_group'], 'A+')

    def test_update_own_profile(self):
        self.authenticate_patient()
        resp = self.client.put('/api/patient/profile/', {'allergies': 'None'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.allergies, 'None')

    def test_cannot_access_other_patient_profile(self):
        """Patient 1 can only see their own profile, not patient 2's."""
        self.authenticate_patient()
        resp = self.client.get('/api/patient/profile/')
        self.assertEqual(resp.data['email'], 'patient1@test.com')
        # There's no endpoint to access another patient's profile by ID

    def test_patient2_sees_own_profile(self):
        self.authenticate_patient(self.patient_user2)
        resp = self.client.get('/api/patient/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['first_name'], 'Bob')


# ─── Appointment Tests ────────────────────────────────────────────────────────

class PatientAppointmentTests(PatientTestBase):

    def test_book_appointment_success(self):
        self.authenticate_patient()
        resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(48).isoformat(),
            'reason': 'Checkup',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['doctor'], self.doctor.pk)
        self.assertEqual(resp.data['status'], 'SCHEDULED')

    def test_double_booking_same_doctor_same_time_fails(self):
        self.authenticate_patient()
        future = self._future_time(72)
        # Book first
        self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': future.isoformat(),
            'reason': 'First',
        })
        # Try to book same slot with patient 2
        self.authenticate_patient(self.patient_user2)
        resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': future.isoformat(),
            'reason': 'Second',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_appointments(self):
        self.authenticate_patient()
        future = self._future_time(96)
        self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': future.isoformat(),
            'reason': 'Test',
        })
        resp = self.client.get('/api/patient/appointments/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_list_appointments_filter_upcoming(self):
        self.authenticate_patient()
        future = self._future_time(120)
        self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': future.isoformat(),
        })
        resp = self.client.get('/api/patient/appointments/', {'status': 'upcoming'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for appt in resp.data:
            self.assertEqual(appt['status'], 'SCHEDULED')

    def test_cancel_appointment(self):
        self.authenticate_patient()
        book_resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(144).isoformat(),
        })
        appt_id = book_resp.data['id']
        resp = self.client.post(f'/api/patient/appointments/{appt_id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        appt = Appointment.objects.get(pk=appt_id)
        self.assertEqual(appt.status, 'CANCELLED')

    def test_cancel_already_cancelled_fails(self):
        self.authenticate_patient()
        book_resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(168).isoformat(),
        })
        appt_id = book_resp.data['id']
        self.client.post(f'/api/patient/appointments/{appt_id}/cancel/')
        resp = self.client.post(f'/api/patient/appointments/{appt_id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_other_patients_appointment_fails(self):
        """Patient 2 cannot cancel Patient 1's appointment."""
        self.authenticate_patient()
        book_resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(192).isoformat(),
        })
        appt_id = book_resp.data['id']

        # Switch to patient 2
        self.authenticate_patient(self.patient_user2)
        resp = self.client.post(f'/api/patient/appointments/{appt_id}/cancel/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_reschedule_appointment(self):
        self.authenticate_patient()
        book_resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(216).isoformat(),
        })
        appt_id = book_resp.data['id']
        new_time = self._future_time(240).isoformat()
        resp = self.client.put(f'/api/patient/appointments/{appt_id}/reschedule/', {
            'scheduled_time': new_time,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_reschedule_conflict_fails(self):
        """Reschedule to a time where the doctor is already booked."""
        self.authenticate_patient()
        conflict_time = self._future_time(264)

        # Book first appointment at that time (with patient 2)
        self.authenticate_patient(self.patient_user2)
        self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': conflict_time.isoformat(),
        })

        # Patient 1 books and tries to reschedule into the conflict slot
        self.authenticate_patient()
        book_resp = self.client.post('/api/patient/appointments/', {
            'doctor': self.doctor.pk,
            'scheduled_time': self._future_time(288).isoformat(),
        })
        appt_id = book_resp.data['id']
        resp = self.client.put(f'/api/patient/appointments/{appt_id}/reschedule/', {
            'scheduled_time': conflict_time.isoformat(),
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Prescription Tests ──────────────────────────────────────────────────────

class PatientPrescriptionTests(PatientTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create an appointment + prescription for patient
        cls.appt = Appointment.objects.create(
            patient=cls.patient, doctor=cls.doctor,
            scheduled_time=timezone.now() + timedelta(days=1),
            status='COMPLETED', created_by=cls.doctor,
        )
        cls.prescription = Prescription.objects.create(
            patient=cls.patient, appointment=cls.appt,
            doctor=cls.doctor,
        )
        PrescriptionItem.objects.create(
            prescription=cls.prescription,
            medicine_name='Amoxicillin', dosage='500mg',
            instructions='1-0-1', duration='5 days',
        )

    def test_list_own_prescriptions(self):
        self.authenticate_patient()
        resp = self.client.get('/api/patient/prescriptions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertGreaterEqual(len(resp.data[0]['items']), 1)

    def test_detail_own_prescription(self):
        self.authenticate_patient()
        resp = self.client.get(f'/api/patient/prescriptions/{self.prescription.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], self.prescription.pk)

    def test_other_patient_cannot_see_prescriptions(self):
        self.authenticate_patient(self.patient_user2)
        resp = self.client.get('/api/patient/prescriptions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_other_patient_cannot_see_prescription_detail(self):
        self.authenticate_patient(self.patient_user2)
        resp = self.client.get(f'/api/patient/prescriptions/{self.prescription.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_cannot_use_patient_endpoint(self):
        self.authenticate_doctor()
        resp = self.client.get('/api/patient/prescriptions/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── Invoice Tests ────────────────────────────────────────────────────────────

class PatientInvoiceTests(PatientTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.invoice = Invoice.objects.create(
            patient=cls.patient, total_amount=Decimal('1500.00'),
            status='UNPAID',
        )
        InvoiceItem.objects.create(
            invoice=cls.invoice, service_name='General Consultation',
            unit_cost=Decimal('1000.00'), quantity=1,
        )
        InvoiceItem.objects.create(
            invoice=cls.invoice, service_name='Blood Test',
            unit_cost=Decimal('500.00'), quantity=1,
        )

    def test_list_own_invoices(self):
        self.authenticate_patient()
        resp = self.client.get('/api/patient/invoices/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['total_amount'], '1500.00')
        self.assertEqual(len(resp.data[0]['items']), 2)

    def test_other_patient_cannot_see_invoices(self):
        self.authenticate_patient(self.patient_user2)
        resp = self.client.get('/api/patient/invoices/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_patient_cannot_create_invoice(self):
        """Patient API has no POST for invoices — only GET."""
        self.authenticate_patient()
        resp = self.client.post('/api/patient/invoices/', {
            'patient': self.patient.pk,
            'total_amount': '200.00',
            'status': 'UNPAID',
        })
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patient_blocked_from_staff_invoice_api(self):
        """Patient should be blocked from the staff /api/invoices/ endpoint."""
        self.authenticate_patient()
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── Lab Report Tests ────────────────────────────────────────────────────────

from datetime import date as date_type

class PatientLabReportTests(PatientTestBase):

    def _make_pdf(self, name='report.pdf', size=1024):
        content = b'%PDF-1.4 ' + b'x' * size
        f = io.BytesIO(content)
        f.name = name
        return f

    def test_upload_lab_report_pdf(self):
        self.authenticate_patient()
        f = self._make_pdf()
        resp = self.client.post('/api/patient/lab-reports/', {
            'test_name': 'Blood Work Q1',
            'report_date': date_type.today().isoformat(),
            'pdf_file': f,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['test_name'], 'Blood Work Q1')

    def test_list_own_lab_reports(self):
        self.authenticate_patient()
        f = self._make_pdf()
        self.client.post('/api/patient/lab-reports/', {
            'test_name': 'CBC Report',
            'report_date': date_type.today().isoformat(),
            'pdf_file': f,
        }, format='multipart')
        resp = self.client.get('/api/patient/lab-reports/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_other_patient_cannot_see_lab_reports(self):
        self.authenticate_patient()
        f = self._make_pdf()
        self.client.post('/api/patient/lab-reports/', {
            'test_name': 'Private report',
            'report_date': date_type.today().isoformat(),
            'pdf_file': f,
        }, format='multipart')

        self.authenticate_patient(self.patient_user2)
        resp = self.client.get('/api/patient/lab-reports/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [r['test_name'] for r in resp.data]
        self.assertNotIn('Private report', names)

    def test_upload_invalid_file_type_rejected(self):
        self.authenticate_patient()
        f = io.BytesIO(b'not a pdf')
        f.name = 'malware.exe'
        resp = self.client.post('/api/patient/lab-reports/', {
            'test_name': 'Bad file',
            'report_date': date_type.today().isoformat(),
            'pdf_file': f,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_file_over_5mb_rejected(self):
        """Files over 5 MB must be rejected by the validator."""
        self.authenticate_patient()
        big = self._make_pdf(size=5 * 1024 * 1024 + 1)  # 5 MB + 1 byte
        resp = self.client.post('/api/patient/lab-reports/', {
            'test_name': 'Oversized',
            'report_date': date_type.today().isoformat(),
            'pdf_file': big,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Visit / EHR Tests ───────────────────────────────────────────────────────

class PatientVisitTests(PatientTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.visit = Visit.objects.create(
            patient=cls.patient, doctor=cls.doctor,
            visit_date=timezone.now() - timedelta(days=3),
            notes='Follow-up visit', diagnosis='Healthy',
        )

    def test_list_own_visits(self):
        self.authenticate_patient()
        resp = self.client.get('/api/patient/visits/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['diagnosis'], 'Healthy')

    def test_other_patient_cannot_see_visits(self):
        self.authenticate_patient(self.patient_user2)
        resp = self.client.get('/api/patient/visits/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


# ─── Staff API Permission Tests ──────────────────────────────────────────────

class StaffAPIPermissionTests(PatientTestBase):
    """Verify that patients are blocked from staff-level API endpoints."""

    def test_patient_blocked_from_appointments_api(self):
        self.authenticate_patient()
        resp = self.client.get('/api/appointments/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_blocked_from_patients_api(self):
        self.authenticate_patient()
        resp = self.client.get('/api/patients/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_blocked_from_prescriptions_api(self):
        self.authenticate_patient()
        resp = self.client.get('/api/prescriptions/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_blocked_from_invoices_api(self):
        self.authenticate_patient()
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_access_staff_api(self):
        self.authenticate_doctor()
        resp = self.client.get('/api/appointments/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
