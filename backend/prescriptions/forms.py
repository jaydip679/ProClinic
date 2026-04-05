from django import forms
from .models import Prescription, PrescriptionItem
from django.forms import inlineformset_factory


class PrescriptionForm(forms.ModelForm):
    """Form for creating a prescription linked to a clinical Visit."""

    def __init__(self, *args, doctor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if doctor:
            from patients.models import Visit
            # Only show visits where this doctor is the treating doctor
            visit_qs = Visit.objects.filter(doctor=doctor).select_related('patient').order_by('-visit_date')
            self.fields['visit'].queryset = visit_qs
            self.fields['patient'].queryset = self.fields['patient'].queryset.filter(
                visits__doctor=doctor
            ).distinct()

    class Meta:
        model = Prescription
        fields = ['patient', 'visit']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'visit': forms.Select(attrs={'class': 'form-select'}),
        }


# MedicineFormSet — unchanged, tied to PrescriptionItem
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

