from django.contrib import admin
from .models import Prescription, PrescriptionItem


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'visit', 'created_at')
    list_select_related = ('patient', 'doctor', 'visit')
    inlines = [PrescriptionItemInline]
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__last_name')
    raw_id_fields = ('visit', 'appointment')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False