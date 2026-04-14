from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from patients.models import Patient
from appointments.models import Appointment
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class PatientWebViewsTests(TestCase):
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

    def test_receptionist_can_create_patient(self):
        self.client.login(username='receptionist', password='password')
        response = self.client.post(reverse('patient_create'), {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1995-05-05',
            'gender': 'Female',
            'blood_group': 'A+',
            'contact_number': '0987654321',
            'address': '456 Ave',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Patient.objects.filter(first_name='Jane', last_name='Smith').exists())

    def test_patient_cannot_create_patient(self):
        self.client.login(username='patient', password='password')
        response = self.client.get(reverse('patient_create'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_receptionist_can_update_patient(self):
        self.client.login(username='receptionist', password='password')
        response = self.client.post(reverse('patient_update', args=[self.patient.pk]), {
            'first_name': 'Johnny',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'gender': 'Male',
            'blood_group': 'O+',
            'contact_number': '1111111111',
            'address': 'New Address'
        })
        self.assertEqual(response.status_code, 302)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.first_name, 'Johnny')
        self.assertEqual(self.patient.address, 'New Address')

    def test_patient_cancel_appointment_uses_cancel_method(self):
        self.client.login(username='patient', password='password')
        response = self.client.post(reverse('patient_cancel_appointment', args=[self.appointment.pk]))
        self.assertRedirects(response, reverse('dashboard'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'CANCELLED')
        self.assertIsNotNone(self.appointment.cancelled_at)
        self.assertEqual(self.appointment.cancelled_by, self.patient_user)
        self.assertEqual(self.appointment.cancellation_reason, 'Patient cancelled via portal')

    def test_patient_cannot_cancel_already_cancelled(self):
        self.appointment.status = 'CANCELLED'
        self.appointment.save()
        self.client.login(username='patient', password='password')
        response = self.client.post(reverse('patient_cancel_appointment', args=[self.appointment.pk]))
        self.assertRedirects(response, reverse('dashboard'))
        # Should show a message or redirect without crashing

    def test_patient_cannot_cancel_checked_in(self):
        self.appointment.status = 'CHECKED_IN'
        self.appointment.save()
        self.client.login(username='patient', password='password')
        response = self.client.post(reverse('patient_cancel_appointment', args=[self.appointment.pk]))
        self.assertRedirects(response, reverse('dashboard'))
        self.appointment.refresh_from_db()
        # Should remain CHECKED_IN
        self.assertEqual(self.appointment.status, 'CHECKED_IN')
