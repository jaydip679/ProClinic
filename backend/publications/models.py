from django.db import models
from django.conf import settings

class Publication(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='publications'
    )
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    authors = models.CharField(
        max_length=500, 
        help_text="Comma-separated list of authors"
    )
    
    # File upload validation (size/MIME) will be handled in a later logic step
    pdf_file = models.FileField(upload_to='publications/papers/')
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='DRAFT'
    )
    admin_notes = models.TextField(
        blank=True, 
        help_text="Notes from admin during approval/rejection"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.doctor.last_name} ({self.status})"