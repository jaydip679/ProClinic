from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST

from prescriptions.forms import DoctorPrescriptionForm, MedicineFormSet
from .forms import AppointmentForm, DoctorUnavailabilityForm
from .models import Appointment, DoctorUnavailability
from patients.models import Patient


BOOKING_ALLOWED_ROLES = {'ADMIN', 'RECEPTIONIST', 'PATIENT'}


def _patient_profile_for_user(user):
    return Patient.objects.filter(
        Q(email=user.email) | Q(contact_number=user.phone_number) | Q(contact_number=user.username)
    ).first()


@login_required
def book_appointment(request):
    if request.user.role == 'DOCTOR':
        return redirect('doctor_appointments')

    if request.user.role not in BOOKING_ALLOWED_ROLES:
        return redirect('dashboard')

    patient_profile = None
    if request.user.role == 'PATIENT':
        patient_profile = _patient_profile_for_user(request.user)

    form = AppointmentForm(
        request.POST or None,
        request_user=request.user,
        patient_profile=patient_profile,
    )

    # Patient bookings must always be for their own profile.
    if request.user.role == 'PATIENT' and patient_profile:
        form.instance.patient = patient_profile

    if request.method == 'POST':
        if form.is_valid():
            appointment = form.save(commit=False)
            if request.user.role == 'PATIENT':
                appointment.patient = patient_profile
            appointment.created_by = request.user
            appointment.save()
            messages.success(request, "Appointment booked successfully.")
            if request.user.role == 'PATIENT':
                return redirect('dashboard')
            return redirect('patient_list')

    context = {
        'form': form,
        'is_patient_portal': request.user.role == 'PATIENT',
        'patient_profile': patient_profile,
    }
    return render(request, 'appointments/book_appointment.html', context)


@login_required
def doctor_appointments(request):
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')

    now = timezone.now()
    upcoming_appointments = Appointment.objects.filter(
        doctor=request.user,
        status='SCHEDULED',
        scheduled_time__gte=now,
    ).select_related('patient', 'prescription').order_by('scheduled_time')

    past_appointments = Appointment.objects.filter(
        doctor=request.user
    ).filter(
        Q(status__in=['COMPLETED', 'CANCELLED', 'NOSHOW']) | Q(scheduled_time__lt=now)
    ).select_related('patient', 'prescription').order_by('-scheduled_time')

    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments[:20],
    }
    return render(request, 'appointments/doctor_appointments.html', context)


@login_required
def doctor_appointment_detail(request, appointment_id):
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')

    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor'),
        pk=appointment_id,
        doctor=request.user,
    )
    prescription = getattr(appointment, 'prescription', None)

    if request.method == 'POST':
        if prescription:
            messages.info(request, "Prescription already exists for this appointment.")
            return redirect('doctor_appointment_detail', appointment_id=appointment.id)

        prescription_form = DoctorPrescriptionForm(request.POST)
        medicine_formset = MedicineFormSet(request.POST, prefix='medicine')
        if prescription_form.is_valid() and medicine_formset.is_valid():
            with transaction.atomic():
                new_prescription = prescription_form.save(commit=False)
                new_prescription.patient = appointment.patient
                new_prescription.appointment = appointment
                new_prescription.doctor = request.user
                new_prescription.save()

                medicine_formset.instance = new_prescription
                medicine_formset.save()

                appointment.status = 'COMPLETED'
                appointment.save(update_fields=['status'])

            messages.success(
                request,
                "Prescription issued and appointment moved to past appointments.",
            )
            return redirect('doctor_appointments')
    else:
        prescription_form = DoctorPrescriptionForm()
        medicine_formset = MedicineFormSet(prefix='medicine')

    context = {
        'appointment': appointment,
        'prescription': prescription,
        'prescription_form': prescription_form,
        'medicine_formset': medicine_formset,
    }
    return render(request, 'appointments/doctor_appointment_detail.html', context)


@login_required
def doctor_unavailability(request):
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')

    form = DoctorUnavailabilityForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        block = form.save(commit=False)
        block.doctor = request.user
        block.save()
        messages.success(request, "Unavailability added successfully.")
        return redirect('doctor_unavailability')

    blocks = DoctorUnavailability.objects.filter(
        doctor=request.user
    ).order_by('-start_time')

    context = {
        'form': form,
        'blocks': blocks,
    }
    return render(request, 'appointments/doctor_unavailability.html', context)


@require_POST
@login_required
def delete_doctor_unavailability(request, block_id):
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')

    block = get_object_or_404(DoctorUnavailability, pk=block_id, doctor=request.user)
    block.delete()
    messages.success(request, "Unavailability entry removed.")
    return redirect('doctor_unavailability')
