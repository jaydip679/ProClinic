from django.db import models
from django.conf import settings
from patients.models import Patient
from appointments.models import Appointment

class Prescription(models.Model):
    # Link to patient and the specific appointment (visit)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='prescription')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    notes = models.TextField(blank=True, help_text="General advice or clinical notes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Placeholder for the generated PDF file mentioned in the PRD
    pdf_file = models.FileField(upload_to='prescriptions/pdfs/', blank=True, null=True)

    def __str__(self):
        return f"Prescription for {self.patient} - {self.created_at.date()}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg")
    instructions = models.CharField(max_length=255, help_text="e.g., Once daily after food")
    duration = models.CharField(max_length=100, help_text="e.g., 5 days")

    def __str__(self):
        return f"{self.medicine_name} for {self.prescription.patient}"