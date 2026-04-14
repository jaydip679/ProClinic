from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        # We exclude 'user' because creating a user is optional or done via patient_signup
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group', 'contact_number', 'email', 'address', 'allergies']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'pc-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'pc-input', 'placeholder': 'Last Name'}),
            'contact_number': forms.TextInput(attrs={'class': 'pc-input', 'placeholder': 'e.g. +1 234 567 890'}),
            'email': forms.EmailInput(attrs={'class': 'pc-input', 'placeholder': 'patient@example.com'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'pc-input'}),
            'gender': forms.Select(attrs={'class': 'pc-input'}),
            'blood_group': forms.Select(attrs={'class': 'pc-input'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'pc-textarea', 'placeholder': 'Full residential address'}),
            'allergies': forms.Textarea(attrs={'rows': 2, 'class': 'pc-textarea', 'placeholder': 'e.g. Penicillin, Peanuts (leave blank if none)'}),
        }
