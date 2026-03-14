from django import forms
from .models import Prescription, PrescriptionItem
from django.forms import inlineformset_factory


class PrescriptionForm(forms.ModelForm):
    def __init__(self, *args, doctor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if doctor:
            appointment_queryset = doctor.doctor_appointments.order_by('-scheduled_time')
            self.fields['appointment'].queryset = appointment_queryset
            self.fields['patient'].queryset = self.fields['patient'].queryset.filter(
                appointments__doctor=doctor
            ).distinct()

    class Meta:
        model = Prescription
        fields = ['patient', 'appointment', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Clinical findings...'}),
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'appointment': forms.Select(attrs={'class': 'form-select'}),
        }


class DoctorPrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Clinical findings and plan...'}
            ),
        }

# This creates a dynamic group of medicine inputs
MedicineFormSet = inlineformset_factory(
    Prescription, PrescriptionItem,
    fields=('medicine_name', 'dosage', 'instructions', 'duration'),
    extra=1,
    min_num=1,
    validate_min=True,
    widgets={
        'medicine_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine'}),
        'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 500mg'}),
        'instructions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-0-1'}),
        'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5 days'}),
    }
)
