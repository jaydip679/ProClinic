from django.contrib import admin
from .models import Publication

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'doctor', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'abstract', 'authors')
    
    # Admin-specific actions for approval workflow
    actions = ['approve_publications', 'reject_publications']

    def approve_publications(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_publications.short_description = "Mark selected publications as Approved"

    def reject_publications(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_publications.short_description = "Mark selected publications as Rejected"