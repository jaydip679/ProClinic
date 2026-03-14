from django.contrib import admin
from .models import Prescription, PrescriptionItem

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1 # Number of empty rows to show by default

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'created_at')
    inlines = [PrescriptionItemInline]
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__last_name')