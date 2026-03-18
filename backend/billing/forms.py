from django import forms
from .models import Invoice, InvoiceItem
from django.forms import inlineformset_factory

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['patient', 'appointment', 'status']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'appointment': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    fields=('service_name', 'unit_cost', 'quantity'),
    extra=1,
    widgets={
        'service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Blood Test'}),
        'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cost'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)