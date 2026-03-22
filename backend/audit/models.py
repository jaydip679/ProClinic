from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='audit_logs'
    )
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=100, help_text="e.g., Patient, Invoice")
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(
        null=True, 
        blank=True, 
        help_text="Store before/after diffs in JSON format"
    )

    def __str__(self):
        return f"{self.action_type} on {self.entity_type} by {self.actor} at {self.timestamp}"