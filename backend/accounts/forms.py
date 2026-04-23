from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError

from .models import CustomUser
from patients.models import Patient


class PatientSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, validators=[EmailValidator(message="Enter a valid email address.")])
    phone_number = forms.CharField(
        required=True, 
        max_length=10, 
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be exactly 10 digits.')]
    )
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
    email = forms.EmailField(required=True, validators=[EmailValidator(message="Enter a valid email address.")])
    phone_number = forms.CharField(
        required=True, 
        max_length=10, 
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be exactly 10 digits.')]
    )

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
    contact_number = forms.CharField(
        required=True, 
        max_length=10, 
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be exactly 10 digits.')]
    )
    email = forms.EmailField(required=True, validators=[EmailValidator(message="Enter a valid email address.")])
    
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


class CustomPasswordChangeForm(PasswordChangeForm):
    def clean_new_password1(self):
        old_password = self.cleaned_data.get('old_password')
        new_password = self.cleaned_data.get('new_password1')
        if old_password and new_password:
            if old_password == new_password:
                raise forms.ValidationError("Your new password cannot be the same as your old password.")
        return new_password

class PatientPasswordChangeForm(CustomPasswordChangeForm):
    pass

class StaffPasswordChangeForm(CustomPasswordChangeForm):
    pass


class StaffProfileForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=True, 
        max_length=10, 
        validators=[RegexValidator(regex=r'^\d{10}$', message='Phone number must be exactly 10 digits.')]
    )
    email = forms.EmailField(required=True, validators=[EmailValidator(message="Enter a valid email address.")])
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'specialization']
