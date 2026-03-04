from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('DOCTOR', 'Doctor'),
        ('RECEPTIONIST', 'Receptionist'),
        ('PHARMACIST', 'Pharmacist'),
        ('ACCOUNTANT', 'Accountant'),
        ('PATIENT', 'Patient'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"