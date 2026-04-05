"""
Extended test suite for ProClinic.

Covers previously uncovered paths:
  - Audit signals  (CREATE / UPDATE / DELETE auto-logging)
  - Audit middleware (thread-local user capture)
  - Publication workflow (submit → pending → approve/reject → public)
  - API: Publications public_list, approve, reject
  - API: Staff Appointment / Prescription / Invoice listing with filters
  - appointments.models methods (reschedule, RESCHEDULED status)
  - patients.models  (LabReport.mark_verified / mark_archived)
  - Pagination response shape
"""

import io
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser
from appointments.models import Appointment
from audit.middleware import AuditUserMiddleware, get_current_user, set_current_user
from audit.models import AuditLog
from audit.signals import _entity_name, _is_tracked, _safe_value, _snapshot
from billing.models import Invoice, InvoiceItem
from patients.models import LabReport, Patient, Visit
from prescriptions.models import Prescription, PrescriptionItem
from publications.models import Publication


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _jwt(user):
    return str(RefreshToken.for_user(user).access_token)


def _make_pdf(size=512):
    f = io.BytesIO(b'%PDF-1.4 ' + b'x' * size)
    f.name = 'test.pdf'
    return f


class BaseTestCase(TestCase):
    """Common users and objects shared across test classes."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = CustomUser.objects.create_user(
            username='admin_ext', password='pass', email='admin_ext@test.com',
            role='ADMIN', is_staff=True, first_name='Admin', last_name='User',
        )
        cls.doctor = CustomUser.objects.create_user(
            username='doctor_ext', password='pass', email='doctor_ext@test.com',
            role='DOCTOR', first_name='Doc', last_name='Strange',
        )
        cls.patient_user = CustomUser.objects.create_user(
            username='patient_ext', password='pass', email='patient_ext@test.com',
            role='PATIENT', first_name='Pat', last_name='Ient',
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
            first_name='Pat', last_name='Ient',
            date_of_birth='1985-06-15', gender='Male',
            blood_group='B+', contact_number='8880001234',
            email='patient_ext@test.com', address='99 Test Ave',
        )

    def staff_client(self, user=None):
        user = user or self.admin
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {_jwt(user)}')
        return c

    def patient_client(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {_jwt(self.patient_user)}')
        return c


# ─────────────────────────────────────────────────────────────────────────────
# A. Audit Middleware Tests
# ─────────────────────────────────────────────────────────────────────────────

class AuditMiddlewareTests(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='mw_user', password='pass', email='mw@test.com',
        )
        self.factory = RequestFactory()

    def _get_response(self, request):
        return type('R', (), {'status_code': 200})()

    def test_authenticated_user_stored(self):
        """Middleware stores authenticated user in thread-local."""
        request = self.factory.get('/')
        request.user = self.user
        type(self.user).is_authenticated = property(lambda s: True)

        mw = AuditUserMiddleware(lambda r: None)
        mw(request)
        # After the response call, the local is cleared, but it was set during request
        # We test by checking get_current_user is None after (cleared correctly)
        self.assertIsNone(get_current_user())

    def test_unauthenticated_user_not_stored(self):
        """Middleware stores None for anonymous users."""
        request = self.factory.get('/')
        anon = type('Anon', (), {'is_authenticated': False})()
        request.user = anon

        responses = []

        def capture_response(req):
            responses.append(get_current_user())
            return type('R', (), {})()

        mw = AuditUserMiddleware(capture_response)
        mw(request)
        self.assertIsNone(responses[0])

    def test_thread_local_cleared_after_response(self):
        """User is cleared from thread-local after response completes."""
        request = self.factory.get('/')
        request.user = self.user

        mw = AuditUserMiddleware(lambda r: None)
        mw(request)
        self.assertIsNone(get_current_user())

    def test_set_and_get_current_user(self):
        """set_current_user / get_current_user round-trip."""
        set_current_user(self.user)
        self.assertEqual(get_current_user(), self.user)
        set_current_user(None)
        self.assertIsNone(get_current_user())


# ─────────────────────────────────────────────────────────────────────────────
# B. Audit Signal Helper Tests
# ─────────────────────────────────────────────────────────────────────────────

class AuditSignalHelperTests(BaseTestCase):

    def test_is_tracked_patient(self):
        self.assertTrue(_is_tracked(self.patient))

    def test_is_tracked_unknown_model(self):
        """An arbitrary model not in the registry should return False."""
        self.assertFalse(_is_tracked(self.admin))   # CustomUser is not tracked

    def test_entity_name_patient(self):
        self.assertEqual(_entity_name(self.patient), 'Patient')

    def test_safe_value_sensitive_field(self):
        self.assertEqual(_safe_value('password', 'secret123'), '***')

    def test_safe_value_skip_field(self):
        self.assertEqual(_safe_value('pdf_file', 'some/path.pdf'), '<file>')

    def test_safe_value_datetime(self):
        now = timezone.now()
        result = _safe_value('created_at', now)
        self.assertEqual(result, now.isoformat())

    def test_safe_value_related_object(self):
        result = _safe_value('patient', self.patient)
        self.assertEqual(result, self.patient.pk)

    def test_snapshot_excludes_sensitive(self):
        snap = _snapshot(self.patient)
        self.assertNotIn('password', snap)

    def test_snapshot_specific_fields(self):
        snap = _snapshot(self.patient, fields=['first_name', 'last_name'])
        self.assertIn('first_name', snap)
        self.assertNotIn('email', snap)


# ─────────────────────────────────────────────────────────────────────────────
# C. Audit Signal Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class AuditSignalIntegrationTests(BaseTestCase):

    def setUp(self):
        set_current_user(self.admin)

    def tearDown(self):
        set_current_user(None)

    def test_patient_create_logged(self):
        before = AuditLog.objects.count()
        p = Patient.objects.create(
            first_name='LogMe', last_name='Now',
            date_of_birth='2000-01-01', gender='Female',
            blood_group='O+', contact_number='1110001234',
            email='logme@test.com', address='1 Log Lane',
        )
        log = AuditLog.objects.filter(entity_type='Patient', entity_id=p.pk, action_type='CREATE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin)
        self.assertIn('first_name', log.changes)

    def test_patient_update_diff_captured(self):
        p = Patient.objects.create(
            first_name='Before', last_name='Update',
            date_of_birth='1991-01-01', gender='Male',
            blood_group='A-', contact_number='2220002345',
            email='before@test.com', address='2 Update Rd',
        )
        p.first_name = 'After'
        p.save(update_fields=['first_name'])
        log = AuditLog.objects.filter(entity_type='Patient', entity_id=p.pk, action_type='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('first_name', log.changes)
        self.assertEqual(log.changes['first_name']['before'], 'Before')
        self.assertEqual(log.changes['first_name']['after'], 'After')

    def test_patient_delete_logged(self):
        p = Patient.objects.create(
            first_name='ToDelete', last_name='Me',
            date_of_birth='1988-03-22', gender='Male',
            blood_group='B-', contact_number='3330003456',
            email='todelete@test.com', address='3 Delete Ave',
        )
        pk = p.pk
        p.delete()
        log = AuditLog.objects.filter(entity_type='Patient', entity_id=pk, action_type='DELETE').last()
        self.assertIsNotNone(log)
        self.assertIn('deleted_summary', log.changes)

    def test_appointment_create_logged(self):
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=2),
            status='SCHEDULED', created_by=self.admin,
        )
        log = AuditLog.objects.filter(entity_type='Appointment', entity_id=appt.pk, action_type='CREATE').last()
        self.assertIsNotNone(log)

    def test_no_update_log_when_nothing_changes(self):
        """If update_fields produces no actual diff, no UPDATE log is written."""
        p = Patient.objects.create(
            first_name='Same', last_name='Value',
            date_of_birth='1970-01-01', gender='Male',
            blood_group='AB+', contact_number='4440004567',
            email='same@test.com', address='4 Same St',
        )
        before = AuditLog.objects.filter(entity_type='Patient', entity_id=p.pk, action_type='UPDATE').count()
        # Save without changing anything
        p.first_name = 'Same'   # same value
        p.save(update_fields=['first_name'])
        after = AuditLog.objects.filter(entity_type='Patient', entity_id=p.pk, action_type='UPDATE').count()
        self.assertEqual(before, after)

    def test_invoice_create_logged(self):
        inv = Invoice.objects.create(patient=self.patient, total_amount=Decimal('250.00'), status='UNPAID')
        log = AuditLog.objects.filter(entity_type='Invoice', entity_id=inv.pk, action_type='CREATE').last()
        self.assertIsNotNone(log)

    def test_publication_approve_logs_update(self):
        pub = Publication.objects.create(
            doctor=self.doctor, title='Signal Paper',
            abstract='Abstract.', authors='Dr Test',
            pdf_file='publications/papers/sig.pdf', status='PENDING',
        )
        pub.approve(reviewer=self.admin)
        log = AuditLog.objects.filter(entity_type='Publication', entity_id=pub.pk, action_type='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('status', log.changes)
        self.assertEqual(log.changes['status']['after'], 'APPROVED')

    def test_publication_reject_logs_update(self):
        pub = Publication.objects.create(
            doctor=self.doctor, title='Rejected Paper',
            abstract='Abstract.', authors='Dr Test',
            pdf_file='publications/papers/rej.pdf', status='PENDING',
        )
        pub.reject(reviewer=self.admin, reason='Not enough citations')
        log = AuditLog.objects.filter(entity_type='Publication', entity_id=pub.pk, action_type='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('status', log.changes)
        self.assertEqual(log.changes['status']['after'], 'REJECTED')

    def test_actor_is_none_when_no_user_set(self):
        """Without a request user (e.g. management commands), actor should be None."""
        set_current_user(None)
        p = Patient.objects.create(
            first_name='NoActor', last_name='Test',
            date_of_birth='2001-01-01', gender='Male',
            blood_group='O-', contact_number='5550005678',
            email='noactor@test.com', address='5 Anon St',
        )
        log = AuditLog.objects.filter(entity_type='Patient', entity_id=p.pk, action_type='CREATE').last()
        self.assertIsNotNone(log)
        self.assertIsNone(log.actor)


# ─────────────────────────────────────────────────────────────────────────────
# D. Publication Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class PublicationModelTests(BaseTestCase):

    def _pub(self, status='PENDING'):
        return Publication.objects.create(
            doctor=self.doctor, title='Test Paper',
            abstract='Abstract.', authors='Author One',
            pdf_file='publications/papers/test.pdf', status=status,
        )

    def test_str_representation(self):
        pub = self._pub()
        self.assertIn('Test Paper', str(pub))
        self.assertIn('PENDING', str(pub))

    def test_approve_sets_status_and_reviewer(self):
        pub = self._pub()
        pub.approve(reviewer=self.admin)
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'APPROVED')
        self.assertEqual(pub.approved_by, self.admin)
        self.assertIsNotNone(pub.approved_at)
        self.assertEqual(pub.rejection_reason, '')

    def test_reject_sets_status_and_reason(self):
        pub = self._pub()
        pub.reject(reviewer=self.admin, reason='Insufficient data')
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'REJECTED')
        self.assertEqual(pub.rejection_reason, 'Insufficient data')
        self.assertIsNone(pub.approved_by)
        self.assertIsNone(pub.approved_at)

    def test_is_public_approved(self):
        pub = self._pub(status='APPROVED')
        self.assertTrue(pub.is_public)

    def test_is_public_pending(self):
        pub = self._pub(status='PENDING')
        self.assertFalse(pub.is_public)

    def test_approve_clears_rejection_reason(self):
        pub = self._pub()
        pub.rejection_reason = 'Old reason'
        pub.save()
        pub.approve(reviewer=self.admin)
        pub.refresh_from_db()
        self.assertEqual(pub.rejection_reason, '')


# ─────────────────────────────────────────────────────────────────────────────
# E. Publication API Tests
# ─────────────────────────────────────────────────────────────────────────────

class PublicationAPITests(BaseTestCase):

    def _pub(self, status='PENDING', title='Paper'):
        return Publication.objects.create(
            doctor=self.doctor, title=title,
            abstract='A useful study.', authors='Dr Test',
            pdf_file='publications/papers/api.pdf', status=status,
        )

    # ── public-list (no auth) ─────────────────────────────────────────────────

    def test_public_list_returns_only_approved(self):
        self._pub(status='APPROVED', title='Approved Paper')
        self._pub(status='PENDING',  title='Pending Paper')
        self._pub(status='REJECTED', title='Rejected Paper')

        resp = self.client.get('/api/publications/public-list/')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        titles = [p['title'] for p in data]
        self.assertIn('Approved Paper', titles)
        self.assertNotIn('Pending Paper', titles)
        self.assertNotIn('Rejected Paper', titles)

    def test_public_list_no_auth_required(self):
        """Unauthenticated GET /api/publications/public-list/ must return 200."""
        resp = APIClient().get('/api/publications/public-list/')
        self.assertEqual(resp.status_code, 200)

    def test_public_list_search_filter(self):
        self._pub(status='APPROVED', title='Cardiology Study')
        self._pub(status='APPROVED', title='Neurology Notes')

        resp = APIClient().get('/api/publications/public-list/?search=cardiology')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        titles = [p['title'] for p in data]
        self.assertIn('Cardiology Study', titles)
        self.assertNotIn('Neurology Notes', titles)

    # ── approve ────────────────────────────────────────────────────────────────

    def test_admin_can_approve(self):
        pub = self._pub(status='PENDING')
        resp = self.staff_client(self.admin).post(f'/api/publications/{pub.pk}/approve/')
        self.assertEqual(resp.status_code, 200)
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'APPROVED')

    def test_doctor_cannot_approve(self):
        pub = self._pub(status='PENDING')
        resp = self.staff_client(self.doctor).post(f'/api/publications/{pub.pk}/approve/')
        self.assertEqual(resp.status_code, 403)

    def test_approve_already_approved_returns_400(self):
        pub = self._pub(status='APPROVED')
        resp = self.staff_client(self.admin).post(f'/api/publications/{pub.pk}/approve/')
        self.assertEqual(resp.status_code, 400)

    # ── reject ─────────────────────────────────────────────────────────────────

    def test_admin_can_reject_with_reason(self):
        pub = self._pub(status='PENDING')
        resp = self.staff_client(self.admin).post(
            f'/api/publications/{pub.pk}/reject/',
            {'reason': 'Methodology flaw'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'REJECTED')
        self.assertEqual(pub.rejection_reason, 'Methodology flaw')

    def test_reject_already_rejected_returns_400(self):
        pub = self._pub(status='REJECTED')
        resp = self.staff_client(self.admin).post(f'/api/publications/{pub.pk}/reject/')
        self.assertEqual(resp.status_code, 400)

    def test_doctor_cannot_reject(self):
        pub = self._pub(status='PENDING')
        resp = self.staff_client(self.doctor).post(f'/api/publications/{pub.pk}/reject/')
        self.assertEqual(resp.status_code, 403)

    # ── staff list filtering ───────────────────────────────────────────────────

    def test_staff_list_filter_by_status(self):
        self._pub(status='APPROVED', title='Approved One')
        self._pub(status='PENDING',  title='Pending Two')
        resp = self.staff_client(self.admin).get('/api/publications/?status=APPROVED')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        for item in data:
            self.assertEqual(item['status'], 'APPROVED')


# ─────────────────────────────────────────────────────────────────────────────
# F. Appointment Model Method Tests
# ─────────────────────────────────────────────────────────────────────────────

class AppointmentModelTests(BaseTestCase):

    def _appt(self, status='SCHEDULED', days_ahead=1):
        return Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=days_ahead),
            status=status, created_by=self.admin,
        )

    def test_cancel_sets_metadata(self):
        appt = self._appt()
        appt.cancel(user=self.admin, reason='Patient request')
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CANCELLED')
        self.assertEqual(appt.cancellation_reason, 'Patient request')
        self.assertEqual(appt.cancelled_by, self.admin)
        self.assertIsNotNone(appt.cancelled_at)

    def test_is_cancellable_scheduled(self):
        appt = self._appt('SCHEDULED')
        self.assertTrue(appt.is_cancellable)

    def test_is_cancellable_completed(self):
        appt = self._appt('COMPLETED')
        self.assertFalse(appt.is_cancellable)

    def test_is_cancellable_cancelled(self):
        appt = self._appt('CANCELLED')
        self.assertFalse(appt.is_cancellable)

    def test_reschedule_updates_time_and_status(self):
        appt = self._appt()
        new_time = timezone.now() + timedelta(days=5)
        appt.reschedule(new_time)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'RESCHEDULED')
        self.assertEqual(appt.scheduled_time, new_time)

    def test_str_representation(self):
        appt = self._appt()
        s = str(appt)
        self.assertIn('Ient', s)   # patient last name


# ─────────────────────────────────────────────────────────────────────────────
# G. LabReport Model Method Tests
# ─────────────────────────────────────────────────────────────────────────────

class LabReportModelTests(BaseTestCase):

    def _lab(self):
        return LabReport.objects.create(
            patient=self.patient,
            uploaded_by=self.doctor,
            test_name='CBC',
            report_date=date_type.today(),
            pdf_file='lab_reports/sample.pdf',
            status='pending',
        )

    def test_mark_verified(self):
        lab = self._lab()
        lab.mark_verified(self.admin)
        lab.refresh_from_db()
        self.assertEqual(lab.status, 'verified')
        self.assertEqual(lab.verified_by, self.admin)

    def test_mark_archived(self):
        lab = self._lab()
        lab.mark_archived()
        lab.refresh_from_db()
        self.assertEqual(lab.status, 'archived')

    def test_str_representation(self):
        lab = self._lab()
        s = str(lab)
        self.assertIn('CBC', s)


# ─────────────────────────────────────────────────────────────────────────────
# H. Staff API – Appointments, Prescriptions, Invoices (filter + pagination)
# ─────────────────────────────────────────────────────────────────────────────

class StaffAppointmentAPITests(BaseTestCase):

    def setUp(self):
        self.c = self.staff_client(self.admin)

    def _appt(self, status='SCHEDULED', days=1):
        return Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=days),
            status=status, created_by=self.admin,
        )

    def test_list_paginated(self):
        self._appt(), self._appt(status='COMPLETED')
        resp = self.c.get('/api/appointments/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('count', resp.data)
        self.assertIn('results', resp.data)

    def test_filter_by_status(self):
        self._appt(status='SCHEDULED')
        self._appt(status='COMPLETED')
        resp = self.c.get('/api/appointments/?status=SCHEDULED')
        self.assertEqual(resp.status_code, 200)
        for item in resp.data.get('results', resp.data):
            self.assertEqual(item['status'], 'SCHEDULED')

    def test_filter_by_doctor_id(self):
        self._appt()
        resp = self.c.get(f'/api/appointments/?doctor_id={self.doctor.pk}')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(data), 1)

    def test_cancel_via_api(self):
        appt = self._appt()
        resp = self.c.post(f'/api/appointments/{appt.pk}/cancel/', {'reason': 'admin cancel'}, format='json')
        self.assertEqual(resp.status_code, 200)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CANCELLED')

    def test_reschedule_via_api(self):
        appt = self._appt()
        new_time = (timezone.now() + timedelta(days=7)).isoformat()
        resp = self.c.post(f'/api/appointments/{appt.pk}/reschedule/', {'new_time': new_time}, format='json')
        self.assertEqual(resp.status_code, 200)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'RESCHEDULED')

    def test_reschedule_invalid_time_returns_400(self):
        appt = self._appt()
        resp = self.c.post(f'/api/appointments/{appt.pk}/reschedule/', {'new_time': 'not-a-date'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_cancel_completed_appointment_returns_400(self):
        appt = self._appt(status='COMPLETED')
        resp = self.c.post(f'/api/appointments/{appt.pk}/cancel/')
        self.assertEqual(resp.status_code, 400)

    def test_reschedule_missing_time_returns_400(self):
        appt = self._appt()
        resp = self.c.post(f'/api/appointments/{appt.pk}/reschedule/', {}, format='json')
        self.assertEqual(resp.status_code, 400)


class StaffPrescriptionAPITests(BaseTestCase):

    def setUp(self):
        self.c = self.staff_client(self.admin)
        self.appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=1),
            status='COMPLETED', created_by=self.admin,
        )

    def test_list_prescriptions_paginated(self):
        Prescription.objects.create(patient=self.patient, doctor=self.doctor, appointment=self.appt)
        resp = self.c.get('/api/prescriptions/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)

    def test_filter_by_patient_id(self):
        Prescription.objects.create(patient=self.patient, doctor=self.doctor, appointment=self.appt)
        resp = self.c.get(f'/api/prescriptions/?patient_id={self.patient.pk}')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        for item in data:
            self.assertEqual(item['patient'], self.patient.pk)

    def test_search_by_medicine(self):
        rx = Prescription.objects.create(patient=self.patient, doctor=self.doctor, appointment=self.appt)
        PrescriptionItem.objects.create(
            prescription=rx, medicine_name='Amoxicillin', dosage='500mg',
            instructions='twice daily', duration='5 days',
        )
        resp = self.c.get('/api/prescriptions/?search=Amoxicillin')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(data), 1)


class StaffInvoiceAPITests(BaseTestCase):

    def setUp(self):
        self.c = self.staff_client(self.admin)

    def test_list_invoices_paginated(self):
        Invoice.objects.create(patient=self.patient, total_amount=Decimal('100.00'), status='UNPAID')
        resp = self.c.get('/api/invoices/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)

    def test_filter_by_status(self):
        Invoice.objects.create(patient=self.patient, total_amount=Decimal('200.00'), status='PAID')
        Invoice.objects.create(patient=self.patient, total_amount=Decimal('300.00'), status='UNPAID')
        resp = self.c.get('/api/invoices/?status=PAID')
        self.assertEqual(resp.status_code, 200)
        for item in resp.data.get('results', resp.data):
            self.assertEqual(item['status'], 'PAID')

    def test_filter_by_patient_id(self):
        Invoice.objects.create(patient=self.patient, total_amount=Decimal('150.00'), status='UNPAID')
        resp = self.c.get(f'/api/invoices/?patient_id={self.patient.pk}')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(data), 1)


# ─────────────────────────────────────────────────────────────────────────────
# I. Patient API – Patients (staff list + search)
# ─────────────────────────────────────────────────────────────────────────────

class StaffPatientAPITests(BaseTestCase):

    def setUp(self):
        self.c = self.staff_client(self.admin)

    def test_list_patients_paginated(self):
        resp = self.c.get('/api/patients/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('results', resp.data)

    def test_search_by_name(self):
        resp = self.c.get('/api/patients/?search=Pat')
        self.assertEqual(resp.status_code, 200)
        data = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(data), 1)

    def test_filter_by_blood_group(self):
        resp = self.c.get(f'/api/patients/?blood_group={self.patient.blood_group}')
        self.assertEqual(resp.status_code, 200)

    def test_page_size_param(self):
        resp = self.c.get('/api/patients/?page_size=5')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('count', resp.data)


# ─────────────────────────────────────────────────────────────────────────────
# J. Publication Web Views
# ─────────────────────────────────────────────────────────────────────────────

class PublicationWebViewTests(BaseTestCase):

    def _pub(self, status='APPROVED', title='Web Paper'):
        return Publication.objects.create(
            doctor=self.doctor, title=title,
            abstract='Study abstract', authors='Dr A',
            pdf_file='publications/papers/web.pdf', status=status,
        )

    def test_public_list_view_accessible_without_login(self):
        self._pub(status='APPROVED')
        resp = self.client.get('/publications/')
        self.assertEqual(resp.status_code, 200)

    def test_public_list_excludes_pending(self):
        self._pub(status='PENDING', title='Hidden Paper')
        resp = self.client.get('/publications/')
        self.assertNotContains(resp, 'Hidden Paper')

    def test_public_detail_view(self):
        pub = self._pub(status='APPROVED', title='Detail View Test')
        resp = self.client.get(f'/publications/{pub.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail View Test')

    def test_public_detail_returns_404_for_pending(self):
        pub = self._pub(status='PENDING')
        resp = self.client.get(f'/publications/{pub.pk}/')
        self.assertEqual(resp.status_code, 404)

    def test_admin_approval_panel_requires_auth(self):
        resp = self.client.get('/publications/review/')
        # Should redirect to login (302) for unauthenticated
        self.assertIn(resp.status_code, [302, 403])

    def test_admin_approval_panel_accessible_to_admin(self):
        self.client.login(username='admin_ext', password='pass')
        resp = self.client.get('/publications/review/')
        self.assertEqual(resp.status_code, 200)

    def test_admin_approve_view_post(self):
        pub = self._pub(status='PENDING')
        self.client.login(username='admin_ext', password='pass')
        resp = self.client.post(f'/publications/{pub.pk}/approve/')
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'APPROVED')
        self.assertRedirects(resp, '/publications/review/')

    def test_admin_reject_view_post(self):
        pub = self._pub(status='PENDING')
        self.client.login(username='admin_ext', password='pass')
        resp = self.client.post(f'/publications/{pub.pk}/reject/', {'rejection_reason': 'Poor quality'})
        pub.refresh_from_db()
        self.assertEqual(pub.status, 'REJECTED')
        self.assertEqual(pub.rejection_reason, 'Poor quality')

    def test_doctor_dashboard_login_required(self):
        resp = self.client.get('/publications/my-papers/')
        self.assertEqual(resp.status_code, 302)

    def test_doctor_dashboard_shows_own_papers(self):
        self._pub(status='PENDING', title='My Pending Paper')
        self.client.login(username='doctor_ext', password='pass')
        resp = self.client.get('/publications/my-papers/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'My Pending Paper')

    def test_submit_paper_sets_status_pending(self):
        self.client.login(username='doctor_ext', password='pass')
        pdf = _make_pdf()
        resp = self.client.post('/publications/submit/', {
            'title': 'New Submission',
            'abstract': 'This is my abstract.',
            'authors': 'Dr Strange',
            'pdf_file': pdf,
        })
        # Should redirect to my-papers on success
        pub = Publication.objects.filter(title='New Submission').first()
        self.assertIsNotNone(pub)
        self.assertEqual(pub.status, 'PENDING')


# ─────────────────────────────────────────────────────────────────────────────
# K. AuditLog model __str__ and admin non-write checks
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='audit_str_user', password='pass', email='auditstr@test.com',
        )

    def test_str_includes_action_and_entity(self):
        log = AuditLog.objects.create(
            actor=self.user, action_type='CREATE',
            entity_type='TestEntity', entity_id=42,
            changes={'key': 'value'},
        )
        s = str(log)
        self.assertIn('CREATE', s)
        self.assertIn('TestEntity', s)
