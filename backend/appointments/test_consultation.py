from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from patients.models import Patient, Visit
from appointments.models import Appointment
from prescriptions.models import Prescription
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class ConsultationNotesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(username='doctor', password='password', role='DOCTOR')
        self.patient_user = User.objects.create_user(username='patient1', password='password', role='PATIENT')
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
        )
        
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_time=timezone.now() + timedelta(days=1),
            status='SCHEDULED',
            created_by=self.doctor
        )

    def test_notes_submitted_successfully(self):
        self.client.login(username='doctor', password='password')
        form_data = {
            'notes': 'Patient has a mild fever.',
            'medicine-TOTAL_FORMS': '1',
            'medicine-INITIAL_FORMS': '0',
            'medicine-MIN_NUM_FORMS': '1',
            'medicine-MAX_NUM_FORMS': '1000',
            'medicine-0-medicine_name': 'Paracetamol',
            'medicine-0-dosage': '500mg',
            'medicine-0-instructions': '1-0-1',
            'medicine-0-duration': '5 days'
        }
        response = self.client.post(
            reverse('doctor_appointment_detail', args=[self.appointment.pk]),
            data=form_data
        )
        self.assertRedirects(response, reverse('doctor_appointments'))
        
        visit = Visit.objects.get(appointment=self.appointment)
        self.assertEqual(visit.notes, 'Patient has a mild fever.')

    def test_notes_visible_after_completion(self):
        # First complete the appointment
        self.client.login(username='doctor', password='password')
        self.client.post(
            reverse('doctor_appointment_detail', args=[self.appointment.pk]),
            data={
                'notes': 'Needs rest.',
                'medicine-TOTAL_FORMS': '1',
                'medicine-INITIAL_FORMS': '0',
                'medicine-MIN_NUM_FORMS': '1',
                'medicine-MAX_NUM_FORMS': '1000',
                'medicine-0-medicine_name': 'Aspirin',
                'medicine-0-dosage': '100mg',
                'medicine-0-instructions': 'daily',
                'medicine-0-duration': '5 days',
            }
        )
        
        # Then GET the detail page to verify notes show
        response = self.client.get(reverse('doctor_appointment_detail', args=[self.appointment.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Needs rest.')

    def test_blank_notes(self):
        self.client.login(username='doctor', password='password')
        self.client.post(
            reverse('doctor_appointment_detail', args=[self.appointment.pk]),
            data={
                'notes': '',
                'medicine-TOTAL_FORMS': '1',
                'medicine-INITIAL_FORMS': '0',
                'medicine-MIN_NUM_FORMS': '1',
                'medicine-MAX_NUM_FORMS': '1000',
                'medicine-0-medicine_name': 'Vitamin C',
                'medicine-0-dosage': '500mg',
                'medicine-0-instructions': 'daily',
                'medicine-0-duration': '10 days',
            }
        )
        
        visit = Visit.objects.get(appointment=self.appointment)
        self.assertEqual(visit.notes, '')
        
        response = self.client.get(reverse('doctor_appointment_detail', args=[self.appointment.pk]))
        self.assertContains(response, '>-<')  # Checking for default:"-" inside HTML tags
