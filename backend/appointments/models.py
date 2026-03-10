from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from patients.models import Patient


class DoctorUnavailability(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='unavailable_slots',
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}

        if self.start_time and timezone.is_naive(self.start_time):
            self.start_time = timezone.make_aware(
                self.start_time,
                timezone.get_current_timezone(),
            )
        if self.end_time and timezone.is_naive(self.end_time):
            self.end_time = timezone.make_aware(
                self.end_time,
                timezone.get_current_timezone(),
            )

        if self.doctor_id:
            User = get_user_model()
            doctor_obj = User.objects.filter(pk=self.doctor_id).only('role').first()
            if not doctor_obj or doctor_obj.role != 'DOCTOR':
                errors['doctor'] = "Unavailability can only be assigned to a doctor."

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors['end_time'] = "End time must be after start time."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.doctor} unavailable from {self.start_time} to {self.end_time}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NOSHOW', 'No Show'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    scheduled_time = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_appointments')

    def clean(self):
        errors = {}

        if self.scheduled_time and timezone.is_naive(self.scheduled_time):
            self.scheduled_time = timezone.make_aware(
                self.scheduled_time,
                timezone.get_current_timezone(),
            )

        # Keep appointment creation in the future.
        if self.scheduled_time and self.scheduled_time <= timezone.now():
            errors['scheduled_time'] = "Scheduled time must be in the future."

        # Doctor user must be a doctor account.
        if self.doctor_id:
            User = get_user_model()
            doctor_obj = User.objects.filter(pk=self.doctor_id).only('role').first()
            if not doctor_obj or doctor_obj.role != 'DOCTOR':
                errors['doctor'] = "Please select a valid doctor."

        # Doctor cannot be booked during blocked availability periods.
        if self.doctor_id and self.scheduled_time:
            has_block = DoctorUnavailability.objects.filter(
                doctor_id=self.doctor_id,
                start_time__lte=self.scheduled_time,
                end_time__gt=self.scheduled_time,
            ).exists()
            if has_block:
                errors['scheduled_time'] = "Doctor is unavailable at this selected time."

        # Check for double-booking for the same doctor at the same time.
        if self.doctor_id and self.scheduled_time:
            overlapping_appointments = Appointment.objects.filter(
                doctor_id=self.doctor_id,
                scheduled_time=self.scheduled_time,
                status='SCHEDULED'
            ).exclude(pk=self.pk)  # Exclude the current appointment if updating.

            if overlapping_appointments.exists():
                errors['doctor'] = "This doctor already has an appointment at that time."

        # Patient cannot hold two active appointments at the same time.
        if self.patient_id and self.scheduled_time:
            patient_conflicts = Appointment.objects.filter(
                patient_id=self.patient_id,
                scheduled_time=self.scheduled_time,
                status='SCHEDULED'
            ).exclude(pk=self.pk)
            if patient_conflicts.exists():
                errors['scheduled_time'] = "You already have an appointment booked at this time."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensures clean() is called before saving.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} with Dr. {self.doctor.last_name} on {self.scheduled_time}"
