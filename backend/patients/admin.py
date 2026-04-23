from django.contrib import admin
from django.utils.html import format_html
from .models import LabReport, Patient, Visit


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'blood_group', 'date_of_birth', 'contact_number')
    search_fields = ('first_name', 'last_name', 'contact_number', 'email')
    list_filter = ('blood_group', 'gender')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'visit_date', 'diagnosis')
    list_select_related = ('patient', 'doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__last_name', 'diagnosis')
    list_filter = ('visit_date',)
    date_hierarchy = 'visit_date'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


def _action_mark_verified(modeladmin, request, queryset):
    for report in queryset.select_related():
        report.mark_verified(request.user)
_action_mark_verified.short_description = "✔ Mark selected reports as Verified"


def _action_mark_archived(modeladmin, request, queryset):
    for report in queryset:
        report.mark_archived()
_action_mark_archived.short_description = "📁 Archive selected reports"


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display = (
        'test_name', 'patient', 'report_date', 'status_badge',
        'uploaded_by', 'verified_by', 'uploaded_at',
    )
    list_select_related = ('patient', 'uploaded_by', 'verified_by')
    list_filter = ('status', 'report_date')
    search_fields = (
        'test_name',
        'patient__first_name', 'patient__last_name',
        'uploaded_by__username',
    )
    date_hierarchy = 'report_date'
    readonly_fields = ('uploaded_at', 'updated_at', 'verified_by')
    actions = [_action_mark_verified, _action_mark_archived]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'pending': '#f59e0b',
            'verified': '#10b981',
            'archived': '#6b7280',
        }
        colour = colours.get(obj.status, '#000')
        return format_html(
            '<span style="color:{}; font-weight:600">{}</span>',
            colour,
            obj.get_status_display(),
        )