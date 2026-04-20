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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent loading thousands of appointments initially
        if 'appointment' in self.fields:
            if not self.is_bound:
                from appointments.models import Appointment
                self.fields['appointment'].queryset = Appointment.objects.none()
            else:
                try:
                    patient_id = self.data.get('patient')
                    from appointments.models import Appointment
                    if patient_id:
                        self.fields['appointment'].queryset = Appointment.objects.filter(patient_id=int(patient_id))
                    else:
                        self.fields['appointment'].queryset = Appointment.objects.none()
                except (ValueError, TypeError):
                    self.fields['appointment'].queryset = Appointment.objects.none()

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