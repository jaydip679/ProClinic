from django.test import TestCase
from django.utils import timezone
import datetime
from accounts.models import CustomUser
from patients.models import Patient
from .models import Appointment, DoctorUnavailability

class DoctorUnavailabilityConflictTests(TestCase):
    def setUp(self):
        self.doctor = CustomUser.objects.create_user(
            username='doctor1',
            role='DOCTOR'
        )
        self.admin = CustomUser.objects.create_user(
            username='admin1',
            role='ADMIN'
        )
        user = CustomUser.objects.create_user(
            username='patient1',
            role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=user,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='Male'
        )
        self.now = timezone.now()
        self.tomorrow = self.now + datetime.timedelta(days=1)
        
        self.unavailability = DoctorUnavailability.objects.create(
            doctor=self.doctor,
            start_time=self.tomorrow,
            end_time=self.tomorrow + datetime.timedelta(hours=2),
            reason='In Surgery'
        )

    def test_booking_during_unavailability_raises_error(self):
        from django.core.exceptions import ValidationError
        appointment = Appointment(
            doctor=self.doctor,
            patient=self.patient,
            scheduled_time=self.tomorrow + datetime.timedelta(hours=1), # Middle of unavailability
            reason='General Checkup',
            created_by=self.admin
        )
        with self.assertRaises(ValidationError) as context:
            appointment.clean()
        self.assertIn('Doctor is unavailable', str(context.exception))

    def test_booking_outside_unavailability_succeeds(self):
        appointment = Appointment(
            doctor=self.doctor,
            patient=self.patient,
            scheduled_time=self.tomorrow + datetime.timedelta(hours=3), # After unavailability
            reason='General Checkup',
            created_by=self.admin
        )
        appointment.clean() # Should not raise
        appointment.save()
        self.assertEqual(Appointment.objects.count(), 1)
