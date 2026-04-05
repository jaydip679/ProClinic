from django.contrib import admin
from django.utils import timezone
from .models import Publication


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'doctor', 'status', 'approved_by', 'approved_at', 'created_at')
    list_filter  = ('status', 'created_at')
    search_fields = ('title', 'abstract', 'authors', 'doctor__first_name', 'doctor__last_name')
    readonly_fields = ('approved_by', 'approved_at', 'created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('doctor', 'title', 'abstract', 'authors', 'pdf_file', 'status'),
        }),
        ('Review', {
            'fields': ('admin_notes', 'rejection_reason', 'approved_by', 'approved_at'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    actions = ['approve_publications', 'reject_publications']

    def approve_publications(self, request, queryset):
        now = timezone.now()
        updated = queryset.exclude(status=Publication.STATUS_APPROVED).update(
            status=Publication.STATUS_APPROVED,
            approved_by=request.user,
            approved_at=now,
            rejection_reason='',
        )
        self.message_user(request, f'{updated} publication(s) approved.')
    approve_publications.short_description = 'Approve selected publications'

    def reject_publications(self, request, queryset):
        updated = queryset.exclude(status=Publication.STATUS_REJECTED).update(
            status=Publication.STATUS_REJECTED,
            approved_by=None,
            approved_at=None,
        )
        self.message_user(request, f'{updated} publication(s) rejected.')
    reject_publications.short_description = 'Reject selected publications'