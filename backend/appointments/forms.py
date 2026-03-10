from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from accounts.models import CustomUser
from .models import Appointment, DoctorUnavailability

class AppointmentForm(forms.ModelForm):
    def __init__(self, *args, request_user=None, patient_profile=None, **kwargs):
        self.request_user = request_user
        self.patient_profile = patient_profile
        super().__init__(*args, **kwargs)

        doctor_queryset = CustomUser.objects.filter(
            role='DOCTOR',
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')

        # If a time is already selected, show only doctors who are free at that slot.
        selected_time_raw = self.data.get('scheduled_time')
        if selected_time_raw:
            try:
                selected_time = self.fields['scheduled_time'].to_python(selected_time_raw)
                if selected_time and timezone.is_naive(selected_time):
                    selected_time = timezone.make_aware(
                        selected_time,
                        timezone.get_current_timezone(),
                    )
                busy_doctor_ids = Appointment.objects.filter(
                    scheduled_time=selected_time,
                    status='SCHEDULED',
                ).values_list('doctor_id', flat=True)
                blocked_doctor_ids = DoctorUnavailability.objects.filter(
                    start_time__lte=selected_time,
                    end_time__gt=selected_time,
                ).values_list('doctor_id', flat=True)
                doctor_queryset = doctor_queryset.exclude(id__in=busy_doctor_ids).exclude(
                    id__in=blocked_doctor_ids
                )

                # Keep the posted doctor in queryset so the form can show a clear
                # validation error instead of "Select a valid choice."
                selected_doctor_id = self.data.get('doctor')
                if selected_doctor_id:
                    available_ids = doctor_queryset.values_list('id', flat=True)
                    doctor_queryset = CustomUser.objects.filter(
                        role='DOCTOR',
                        is_active=True,
                    ).filter(
                        Q(id__in=available_ids) | Q(pk=selected_doctor_id)
                    ).order_by('first_name', 'last_name', 'username')
            except ValidationError:
                pass

        self.fields['doctor'].queryset = doctor_queryset
        self.fields['doctor'].label_from_instance = (
            lambda user: user.get_full_name() or user.username
        )

        if self.request_user and self.request_user.role == 'PATIENT':
            self.fields.pop('patient')

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        scheduled_time = cleaned_data.get('scheduled_time')

        if doctor and scheduled_time:
            is_doctor_busy = Appointment.objects.filter(
                doctor=doctor,
                scheduled_time=scheduled_time,
                status='SCHEDULED',
            ).exclude(pk=self.instance.pk).exists()
            if is_doctor_busy:
                self.add_error('doctor', 'Selected doctor is not available at this time.')

            is_doctor_blocked = DoctorUnavailability.objects.filter(
                doctor=doctor,
                start_time__lte=scheduled_time,
                end_time__gt=scheduled_time,
            ).exists()
            if is_doctor_blocked:
                self.add_error('scheduled_time', 'Doctor has marked this time as unavailable.')

        if (
            self.request_user
            and self.request_user.role == 'PATIENT'
            and not self.patient_profile
        ):
            raise forms.ValidationError(
                "Patient profile is missing. Please contact reception first."
            )

        return cleaned_data

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'scheduled_time', 'reason']
        widgets = {
            # Use the browser's native datetime picker
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DoctorUnavailabilityForm(forms.ModelForm):
    class Meta:
        model = DoctorUnavailability
        fields = ['start_time', 'end_time', 'reason']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'reason': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Leave, surgery, emergency, etc.'}
            ),
        }
