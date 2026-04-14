from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from .models import CustomUser
from patients.models import Patient


class PatientSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True, max_length=15)
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=Patient._meta.get_field('gender').choices
    )
    blood_group = forms.ChoiceField(
        choices=Patient.BLOOD_GROUP_CHOICES
    )
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}))
    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')

    def clean_email(self):
        email = self.cleaned_data['email']
        if Patient.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A patient profile with this email already exists."
            )
        return email


class StaffCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            choice for choice in CustomUser.ROLE_CHOICES if choice[0] != 'PATIENT'
        ]
    )
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'specialization')

    def save(self, commit=True):
        user = super().save(commit=False)
        # Only ADMIN role receives Django admin access.
        # All other staff roles (DOCTOR, RECEPTIONIST, PHARMACIST, ACCOUNTANT)
        # do not need is_staff and should not have access to the Django admin panel.
        user.is_staff = (user.role == 'ADMIN')
        if commit:
            user.save()
        return user


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name',
            'last_name',
            'date_of_birth',
            'gender',
            'blood_group',
            'contact_number',
            'email',
            'address',
            'allergies',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
        }


class PatientPasswordChangeForm(PasswordChangeForm):
    pass


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'specialization']
