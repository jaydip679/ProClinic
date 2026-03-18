from django.contrib import admin
from .models import Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [InvoiceItemInline]
    search_fields = ('patient__first_name', 'patient__last_name')

    # Optional: Automatically calculate total_amount based on items (basic version)
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        invoice = form.instance
        total = sum(item.line_total for item in invoice.items.all())
        invoice.total_amount = total
        invoice.save()