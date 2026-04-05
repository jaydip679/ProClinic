from django.contrib import admin
from .models import Appointment, DoctorUnavailability

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_time', 'status', 'cancelled_at', 'cancelled_by')
    list_filter = ('status', 'scheduled_time', 'doctor')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__last_name')
    readonly_fields = ('cancelled_at', 'cancelled_by', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('patient', 'doctor', 'scheduled_time', 'reason', 'status', 'created_by', 'created_at'),
        }),
        ('Cancellation Details', {
            'classes': ('collapse',),
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason'),
        }),
    )



@admin.register(DoctorUnavailability)
class DoctorUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_time', 'end_time', 'reason')
    list_filter = ('doctor', 'start_time')
    search_fields = ('doctor__username', 'doctor__first_name', 'doctor__last_name', 'reason')
