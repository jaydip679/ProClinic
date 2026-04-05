from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django import forms as django_forms

from prescriptions.forms import MedicineFormSet
from .forms import AppointmentForm, DoctorUnavailabilityForm
from .models import Appointment, DoctorUnavailability
from patients.models import Patient, Visit


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

    # Fetch existing visit + prescription via the appointment if they exist
    visit = getattr(appointment, 'visit', None)
    prescription = None
    if visit:
        prescription = visit.prescriptions.select_related('doctor').prefetch_related('items').first()

    # Inline form for Visit notes/diagnosis
    class VisitNoteForm(django_forms.Form):
        notes = django_forms.CharField(
            widget=django_forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Clinical notes...'}),
            required=False,
        )
        diagnosis = django_forms.CharField(
            widget=django_forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Diagnosis...'}),
            required=False,
        )

    if request.method == 'POST':
        if prescription:
            messages.info(request, "Prescription already exists for this appointment.")
            return redirect('doctor_appointment_detail', appointment_id=appointment.id)

        visit_form = VisitNoteForm(request.POST)
        medicine_formset = MedicineFormSet(request.POST, prefix='medicine')

        if visit_form.is_valid() and medicine_formset.is_valid():
            with transaction.atomic():
                # Create (or reuse) the Visit record for this appointment
                visit, _ = Visit.objects.get_or_create(
                    appointment=appointment,
                    defaults={
                        'patient': appointment.patient,
                        'doctor': request.user,
                        'visit_date': appointment.scheduled_time,
                        'notes': visit_form.cleaned_data.get('notes', ''),
                        'diagnosis': visit_form.cleaned_data.get('diagnosis', ''),
                    },
                )
                if not _:
                    # Visit already existed — update notes
                    visit.notes = visit_form.cleaned_data.get('notes', visit.notes)
                    visit.diagnosis = visit_form.cleaned_data.get('diagnosis', visit.diagnosis)
                    visit.save(update_fields=['notes', 'diagnosis'])

                from prescriptions.models import Prescription
                new_prescription = Prescription(
                    visit=visit,
                    patient=appointment.patient,
                    doctor=request.user,
                    appointment=appointment,
                )
                new_prescription.save()

                medicine_formset.instance = new_prescription
                medicine_formset.save()

                appointment.status = 'COMPLETED'
                appointment.save(update_fields=['status'])

            messages.success(
                request,
                "Visit recorded, prescription issued, appointment marked completed.",
            )
            return redirect('doctor_appointments')
    else:
        visit_form = VisitNoteForm(initial={
            'notes': visit.notes if visit else '',
            'diagnosis': visit.diagnosis if visit else '',
        })
        medicine_formset = MedicineFormSet(prefix='medicine')

    context = {
        'appointment': appointment,
        'visit': visit,
        'prescription': prescription,
        'prescription_form': visit_form,
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


import datetime
from django.http import JsonResponse
from accounts.models import CustomUser

def get_available_slots(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    if not doctor_id or not date_str:
        return JsonResponse({'slots': []})
    
    try:
        query_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        doctor = CustomUser.objects.get(pk=doctor_id, role='DOCTOR')
    except (ValueError, CustomUser.DoesNotExist):
        return JsonResponse({'slots': []})

    # Generate 30 min slots from 09:00 to 17:00
    slots = []
    start_time = datetime.datetime.combine(query_date, datetime.time(9, 0))
    start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
    
    end_time = datetime.datetime.combine(query_date, datetime.time(17, 0))
    end_time = timezone.make_aware(end_time, timezone.get_current_timezone())
    
    current = start_time
    while current < end_time:
        slots.append(current)
        current += datetime.timedelta(minutes=30)
    
    busy_dr = Appointment.objects.filter(
        doctor=doctor,
        status='SCHEDULED',
        scheduled_time__gte=start_time,
        scheduled_time__lt=end_time
    ).values_list('scheduled_time', flat=True)
    
    # Filter patient unavailabilities if patient portal
    patient_busy_slots = []
    if request.user.is_authenticated and request.user.role == 'PATIENT':
        patient_profile = _patient_profile_for_user(request.user)
        if patient_profile:
            patient_busy_slots = Appointment.objects.filter(
                patient=patient_profile,
                status='SCHEDULED',
                scheduled_time__gte=start_time,
                scheduled_time__lt=end_time
            ).values_list('scheduled_time', flat=True)
    
    # Filter unavailabilities
    blocks = DoctorUnavailability.objects.filter(
        doctor=doctor,
        end_time__gt=start_time,
        start_time__lt=end_time
    )

    available = []
    now = timezone.now()
    
    for slot in slots:
        if slot < now:
            continue
            
        is_conflict = False
        conflict_details = ""
        
        if slot in busy_dr:
            is_conflict = True
            conflict_details = "Doctor already has an appointment scheduled."
        elif slot in patient_busy_slots:
            is_conflict = True
            conflict_details = "You already have an appointment scheduled at this exact time."
        
        if not is_conflict:
            slot_end = slot + datetime.timedelta(minutes=30)
            for b in blocks:
                # Overlap condition
                if max(slot, b.start_time) < min(slot_end, b.end_time):
                    is_conflict = True
                    conflict_details = b.reason or "Doctor is unavailable during this time."
                    break
        
        available.append({
            'iso': slot.isoformat(),
            'label': timezone.localtime(slot).strftime('%I:%M %p'),
            'is_conflict': is_conflict,
            'conflict_details': conflict_details,
        })
            
    return JsonResponse({'slots': available})
