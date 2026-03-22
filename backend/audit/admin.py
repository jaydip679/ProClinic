from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'entity_type', 'actor', 'timestamp')
    list_filter = ('action_type', 'entity_type', 'timestamp')
    search_fields = ('entity_type', 'actor__username')
    
    # Audit logs should be read-only in the admin for integrity
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False