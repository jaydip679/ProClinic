"""
appointments/test_noshow.py
────────────────────────────
Tests for the auto-NOSHOW management command and service.
"""
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from appointments.models import Appointment
from appointments.services import auto_mark_noshow
from patients.models import Patient

User = get_user_model()


class AutoNoshowServiceTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='dr_noshow', password='pw', role='DOCTOR'
        )
        self.patient_user = User.objects.create_user(
            username='pat_noshow', password='pw', role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='Test',
            last_name='Patient',
            date_of_birth='1990-01-01',
        )

    def _make_appointment(self, scheduled_time, status='SCHEDULED'):
        """Create appointment bypassing clean() so past times are allowed in tests.
        Uses queryset.update() after creation to set past times without triggering
        model validation.
        """
        # Create with a future time first (passes clean())
        from django.utils import timezone as tz
        future = tz.now() + timedelta(hours=1)
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_time=future,
            status='SCHEDULED',
            created_by=self.doctor,
        )
        # Bypass clean() to set past time and desired status directly
        Appointment.objects.filter(pk=appt.pk).update(
            scheduled_time=scheduled_time,
            status=status,
        )
        appt.refresh_from_db()
        return appt

    # ── Test: overdue SCHEDULED appointment becomes NOSHOW ────────────────────

    def test_scheduled_overdue_becomes_noshow(self):
        past_time = timezone.now() - timedelta(minutes=45)
        appt = self._make_appointment(past_time, status='SCHEDULED')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'NOSHOW')
        self.assertEqual(count, 1)

    # ── Test: overdue RESCHEDULED appointment becomes NOSHOW ─────────────────

    def test_rescheduled_overdue_becomes_noshow(self):
        past_time = timezone.now() - timedelta(minutes=60)
        appt = self._make_appointment(past_time, status='RESCHEDULED')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'NOSHOW')
        self.assertEqual(count, 1)

    # ── Test: appointment within grace period stays SCHEDULED ─────────────────

    def test_within_grace_stays_scheduled(self):
        # 10 minutes past — within the 30-minute grace
        recent_time = timezone.now() - timedelta(minutes=10)
        appt = self._make_appointment(recent_time, status='SCHEDULED')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'SCHEDULED')
        self.assertEqual(count, 0)

    # ── Test: CHECKED_IN appointment is never marked NOSHOW ──────────────────

    def test_checked_in_never_noshow(self):
        past_time = timezone.now() - timedelta(hours=2)
        appt = self._make_appointment(past_time, status='CHECKED_IN')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CHECKED_IN')
        self.assertEqual(count, 0)

    # ── Test: COMPLETED appointment is untouched ──────────────────────────────

    def test_completed_appointment_untouched(self):
        past_time = timezone.now() - timedelta(hours=3)
        appt = self._make_appointment(past_time, status='COMPLETED')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'COMPLETED')
        self.assertEqual(count, 0)

    # ── Test: CANCELLED appointment is untouched ──────────────────────────────

    def test_cancelled_appointment_untouched(self):
        past_time = timezone.now() - timedelta(hours=1)
        appt = self._make_appointment(past_time, status='CANCELLED')

        count = auto_mark_noshow(grace_minutes=30)

        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CANCELLED')
        self.assertEqual(count, 0)

    # ── Test: already-NOSHOW appointment not double-counted ───────────────────

    def test_already_noshow_not_recounted(self):
        past_time = timezone.now() - timedelta(hours=5)
        appt = self._make_appointment(past_time, status='NOSHOW')

        count = auto_mark_noshow(grace_minutes=30)

        self.assertEqual(count, 0)

    # ── Test: management command runs without error ───────────────────────────

    def test_management_command_runs(self):
        from django.core.management import call_command
        out = StringIO()
        call_command('mark_noshow', '--grace', '30', stdout=out)
        self.assertIn('NOSHOW', out.getvalue() + 'No appointments needed to be marked as NOSHOW.')
