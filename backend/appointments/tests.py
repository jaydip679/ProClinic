from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from patients.models import Patient
from appointments.models import Appointment
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class AppointmentCheckInTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create roles
        self.admin = User.objects.create_user(username='admin', password='password', role='ADMIN')
        self.receptionist = User.objects.create_user(username='receptionist', password='password', role='RECEPTIONIST')
        self.patient_user = User.objects.create_user(username='patient', password='password', role='PATIENT')
        self.doctor = User.objects.create_user(username='doctor', password='password', role='DOCTOR')
        
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='Male',
            blood_group='O+',
            contact_number='1234567890',
            address='123 Street'
        )
        
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=1),
            status='SCHEDULED',
            created_by=self.doctor
        )

    def test_receptionist_can_check_in_patient_no_room(self):
        self.client.login(username='receptionist', password='password')
        response = self.client.post(reverse('receptionist_checkin_appointment', args=[self.appointment.pk]))
        self.assertRedirects(response, reverse('receptionist_appointments'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'CHECKED_IN')
        self.assertEqual(self.appointment.room_assignment, None)

    def test_receptionist_can_check_in_patient_with_room(self):
        self.client.login(username='receptionist', password='password')
        response = self.client.post(reverse('receptionist_checkin_appointment', args=[self.appointment.pk]), data={
            'room_assignment': 'Exam Room 1'
        })
        self.assertRedirects(response, reverse('receptionist_appointments'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'CHECKED_IN')
        self.assertEqual(self.appointment.room_assignment, 'Exam Room 1')

    def test_patient_cannot_check_in(self):
        self.client.login(username='patient', password='password')
        response = self.client.post(reverse('receptionist_checkin_appointment', args=[self.appointment.pk]))
        self.assertRedirects(response, reverse('dashboard'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'SCHEDULED')
        
    def test_receptionist_can_cancel_checked_in_patient(self):
        self.appointment.status = 'CHECKED_IN'
        self.appointment.save()
        
        self.client.login(username='receptionist', password='password')
        response = self.client.post(reverse('receptionist_cancel_appointment', args=[self.appointment.pk]), {
            'reason': 'Staff override'
        })
        self.assertRedirects(response, reverse('receptionist_appointments'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'CANCELLED')
