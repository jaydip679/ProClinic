from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django import forms as django_forms

from audit.utils import log_action
from prescriptions.forms import MedicineFormSet
from .forms import AppointmentForm, DoctorUnavailabilityForm, VisitNoteForm
from .models import Appointment, DoctorUnavailability
from patients.models import Patient, Visit
from core.utils import send_appointment_notification


BOOKING_ALLOWED_ROLES = {'ADMIN', 'RECEPTIONIST', 'PATIENT'}


from patients.utils import get_patient_profile

@login_required
def book_appointment(request):
    if request.user.role == 'DOCTOR':
        return redirect('doctor_appointments')

    if request.user.role not in BOOKING_ALLOWED_ROLES:
        return redirect('dashboard')

    patient_profile = None
    if request.user.role == 'PATIENT':
        patient_profile = get_patient_profile(request.user)

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
            send_appointment_notification(appointment, 'created')
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


    if request.method == 'POST':
        if appointment.status in ['CANCELLED', 'NOSHOW']:
            messages.error(request, "Cannot write prescriptions for cancelled or no-show appointments.")
            return redirect('doctor_appointment_detail', appointment_id=appointment.id)

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
    patient_id = request.GET.get('patient_id')
    
    if not doctor_id or not date_str:
        return JsonResponse({'slots': []})
    
    try:
        query_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Explicit Boundary Check
        now_local = timezone.localtime(timezone.now())
        if query_date < now_local.date():
            return JsonResponse({'slots': [], 'error': 'Selected date is in the past. Clean your calendar fields.'})
            
        max_future_date = (now_local + datetime.timedelta(days=7)).date()
        if query_date > max_future_date:
            return JsonResponse({'slots': [], 'error': 'Cannot book more than 7 days in advance.'})

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
        status__in=['SCHEDULED', 'RESCHEDULED'],
        scheduled_time__gte=start_time,
        scheduled_time__lt=end_time
    ).values_list('scheduled_time', flat=True)
    
    # Filter patient unavailabilities
    patient_busy_slots = []
    if patient_id and patient_id.isdigit():
        patient_busy_slots = Appointment.objects.filter(
            patient_id=patient_id,
            status__in=['SCHEDULED', 'RESCHEDULED'],
            scheduled_time__gte=start_time,
            scheduled_time__lt=end_time
        ).values_list('scheduled_time', flat=True)
    elif request.user.is_authenticated and request.user.role == 'PATIENT':
        patient_profile = get_patient_profile(request.user)
        if patient_profile:
            patient_busy_slots = Appointment.objects.filter(
                patient=patient_profile,
                status__in=['SCHEDULED', 'RESCHEDULED'],
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
            
        if slot in busy_dr or slot in patient_busy_slots:
            continue
        
        is_conflict = False
        slot_end = slot + datetime.timedelta(minutes=30)
        for b in blocks:
            # Overlap condition
            if max(slot, b.start_time) < min(slot_end, b.end_time):
                is_conflict = True
                break
                
        if not is_conflict:
            local_slot = timezone.localtime(slot)
            available.append({
                'iso': local_slot.strftime('%Y-%m-%dT%H:%M'),
                'label': local_slot.strftime('%I:%M %p')
            })
            
    return JsonResponse({'slots': available})


# ─── Receptionist Appointment Management ─────────────────────────────────────

RECEPTIONIST_ROLES = {'ADMIN', 'RECEPTIONIST'}


@login_required
def receptionist_appointments(request):
    """Full appointment management view for Receptionist and Admin."""
    if request.user.role not in RECEPTIONIST_ROLES:
        return redirect('dashboard')

    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('q', '').strip()

    qs = Appointment.objects.select_related(
        'patient', 'doctor', 'created_by'
    ).order_by('-scheduled_time')

    if status_filter in ('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NOSHOW', 'RESCHEDULED'):
        qs = qs.filter(status=status_filter)

    if date_filter:
        try:
            import datetime
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            qs = qs.filter(scheduled_time__date=filter_date)
        except ValueError:
            pass

    if search_query:
        qs = qs.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(doctor__first_name__icontains=search_query) |
            Q(doctor__last_name__icontains=search_query)
        )

    counts = {
        'all':         Appointment.objects.count(),
        'SCHEDULED':   Appointment.objects.filter(status='SCHEDULED').count(),
        'COMPLETED':   Appointment.objects.filter(status='COMPLETED').count(),
        'CANCELLED':   Appointment.objects.filter(status='CANCELLED').count(),
        'NOSHOW':      Appointment.objects.filter(status='NOSHOW').count(),
        'RESCHEDULED': Appointment.objects.filter(status='RESCHEDULED').count(),
    }

    return render(request, 'appointments/receptionist_appointments.html', {
        'appointments': qs,
        'current_status': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'counts': counts,
    })


@require_POST
@login_required
def receptionist_cancel_appointment(request, pk):
    """POST – cancel any appointment. Receptionist / Admin only."""
    if request.user.role not in RECEPTIONIST_ROLES:
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)

    if not appointment.is_cancellable:
        messages.error(
            request,
            f"Appointment #{pk} cannot be cancelled (status: {appointment.get_status_display()})."
        )
        return redirect('receptionist_appointments')

    reason = request.POST.get('reason', '').strip()
    appointment.cancel(user=request.user, reason=reason)
    send_appointment_notification(appointment, 'cancelled')

    log_action(
        actor=request.user,
        action_type='UPDATE',
        entity_type='Appointment',
        entity_id=pk,
        changes={'action': 'cancel', 'patient': str(appointment.patient), 'reason': reason or '(none)'},
    )
    messages.success(
        request,
        f"Appointment #{pk} for {appointment.patient} successfully cancelled."
    )
    return redirect('receptionist_appointments')


@require_POST
@login_required
def receptionist_reschedule_appointment(request, pk):
    """POST – reschedule any appointment to a new datetime. Receptionist / Admin only."""
    if request.user.role not in RECEPTIONIST_ROLES:
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)

    BLOCKED_STATUSES = {'CANCELLED', 'COMPLETED', 'NOSHOW'}
    if appointment.status in BLOCKED_STATUSES:
        messages.error(
            request,
            f"Cannot reschedule a {appointment.get_status_display()} appointment."
        )
        return redirect('receptionist_appointments')

    new_time_str = request.POST.get('new_time', '').strip()
    if not new_time_str:
        messages.error(request, "Please provide a new date and time.")
        return redirect('receptionist_appointments')

    try:
        from django.utils.dateparse import parse_datetime
        new_time = parse_datetime(new_time_str)
        if new_time is None:
            raise ValueError("unparseable")
        if timezone.is_naive(new_time):
            new_time = timezone.make_aware(new_time, timezone.get_current_timezone())
    except (ValueError, TypeError):
        messages.error(request, "Invalid date/time format. Please use the date picker.")
        return redirect('receptionist_appointments')

    if new_time <= timezone.now():
        messages.error(request, "New appointment time must be in the future.")
        return redirect('receptionist_appointments')

    old_time = appointment.scheduled_time
    appointment.override_conflict = True   # staff can override slot conflicts
    appointment.reschedule(new_time)
    send_appointment_notification(appointment, 'rescheduled')

    log_action(
        actor=request.user,
        action_type='UPDATE',
        entity_type='Appointment',
        entity_id=pk,
        changes={
            'action': 'reschedule',
            'patient': str(appointment.patient),
            'old_time': old_time.isoformat(),
            'new_time': new_time.isoformat(),
        },
    )
    messages.success(
        request,
        f"Appointment #{pk} rescheduled from {timezone.localtime(old_time):%b %d, %H:%M} "
        f"to {timezone.localtime(new_time):%b %d, %H:%M}."
    )
    return redirect('receptionist_appointments')


@require_POST
@login_required
def receptionist_mark_noshow(request, pk):
    """POST – mark an appointment as NOSHOW. Receptionist / Admin only."""
    if request.user.role not in RECEPTIONIST_ROLES:
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)

    if appointment.status != 'SCHEDULED':
        messages.error(
            request,
            f"Only scheduled appointments can be marked as No Show "
            f"(current status: {appointment.get_status_display()})."
        )
        return redirect('receptionist_appointments')

    appointment.status = 'NOSHOW'
    appointment.save(update_fields=['status'])

    log_action(
        actor=request.user,
        action_type='UPDATE',
        entity_type='Appointment',
        entity_id=pk,
        changes={'action': 'mark_noshow', 'patient': str(appointment.patient)},
    )
    messages.success(
        request,
        f"Appointment #{pk} for {appointment.patient} marked as No Show."
    )
    return redirect('receptionist_appointments')

@require_POST
@login_required
def receptionist_checkin_appointment(request, pk):
    """POST – mark an appointment as CHECKED_IN. Receptionist / Admin only."""
    if request.user.role not in RECEPTIONIST_ROLES:
        return redirect('dashboard')

    appointment = get_object_or_404(Appointment, pk=pk)

    if appointment.status not in ('SCHEDULED', 'RESCHEDULED'):
        messages.error(
            request,
            f"Only scheduled appointments can be checked in "
            f"(current status: {appointment.get_status_display()})."
        )
        return redirect('receptionist_appointments')

    room = request.POST.get('room_assignment', '').strip()
    
    appointment.status = 'CHECKED_IN'
    if room:
        appointment.room_assignment = room
        appointment.save(update_fields=['status', 'room_assignment'])
        msg = f"Patient {appointment.patient} checked in to {room} for Appointment #{pk}."
    else:
        appointment.save(update_fields=['status'])
        msg = f"Patient {appointment.patient} checked in for Appointment #{pk}."

    log_action(
        actor=request.user,
        action_type='UPDATE',
        entity_type='Appointment',
        entity_id=pk,
        changes={'action': 'checkin', 'room': room, 'patient': str(appointment.patient)},
    )
    messages.success(request, msg)
    return redirect('receptionist_appointments')
