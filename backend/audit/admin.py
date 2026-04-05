from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('timestamp', 'action_type', 'entity_type', 'entity_id', 'actor')
    list_filter   = ('action_type', 'entity_type', 'timestamp')
    search_fields = ('entity_type', 'actor__username', 'actor__first_name', 'actor__last_name')
    readonly_fields = ('actor', 'action_type', 'entity_type', 'entity_id', 'timestamp', 'changes')
    ordering = ('-timestamp',)

    # Audit logs must be immutable — no add / change / delete from admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False