from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone

from audit.utils import log_action
from .forms import PrescriptionForm, MedicineFormSet
from .models import Prescription


# ─── Doctor Views ─────────────────────────────────────────────────────────────

@login_required
def create_prescription(request):
    """Doctor: create a new prescription linked to a clinical Visit."""
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, doctor=request.user)
        formset = MedicineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            prescription = form.save(commit=False)

            # Derive patient and doctor from the linked Visit
            visit = prescription.visit
            if visit and visit.doctor_id != request.user.id:
                form.add_error('visit', 'You can only prescribe for your own visits.')
                return render(request, 'prescriptions/create_prescription.html', {
                    'form': form,
                    'formset': formset,
                })

            prescription.doctor = request.user
            if visit:
                prescription.patient = visit.patient
                # Link the associated appointment if the visit has one
                if visit.appointment_id:
                    prescription.appointment = visit.appointment

            prescription.save()

            formset.instance = prescription
            formset.save()

            # Mark the linked appointment as completed if present
            if prescription.appointment_id:
                prescription.appointment.status = 'COMPLETED'
                prescription.appointment.save(update_fields=['status'])

            log_action(
                actor=request.user,
                action_type='CREATE',
                entity_type='Prescription',
                entity_id=prescription.pk,
                changes={
                    'patient_id': prescription.patient_id,
                    'item_count': prescription.items.count(),
                },
            )

            messages.success(request, "Prescription issued successfully.")
            return redirect('doctor_appointments')
    else:
        form = PrescriptionForm(doctor=request.user)
        formset = MedicineFormSet()

    return render(request, 'prescriptions/create_prescription.html', {
        'form': form,
        'formset': formset,
    })


# ─── Pharmacist Views ─────────────────────────────────────────────────────────

@login_required
def pharmacist_prescription_list(request):
    """
    Pharmacist dispense queue.

    Supports ?status=PENDING|DISPENSED|all   (default: PENDING)
    Supports ?q=<name>  to search by patient name
    """
    if request.user.role != 'PHARMACIST':
        return redirect('dashboard')

    status_filter = request.GET.get('status', 'PENDING')
    if status_filter not in ('PENDING', 'DISPENSED', 'all'):
        status_filter = 'PENDING'

    search_query = request.GET.get('q', '').strip()

    qs = (
        Prescription.objects
        .select_related('patient', 'doctor')
        .prefetch_related('items')
        .order_by('-created_at')
    )

    if status_filter != 'all':
        qs = qs.filter(dispense_status=status_filter)

    if search_query:
        qs = qs.filter(
            patient__first_name__icontains=search_query
        ) | qs.filter(
            patient__last_name__icontains=search_query
        )

    pending_count = Prescription.objects.filter(dispense_status='PENDING').count()
    dispensed_count = Prescription.objects.filter(dispense_status='DISPENSED').count()

    return render(request, 'prescriptions/pharmacist_prescriptions.html', {
        'prescriptions': qs,
        'current_filter': status_filter,
        'search_query': search_query,
        'pending_count': pending_count,
        'dispensed_count': dispensed_count,
        'total_count': pending_count + dispensed_count,
    })


@login_required
def pharmacist_prescription_detail(request, pk):
    """
    Pharmacist: detailed view of a single prescription.
    Shows full medicine table, patient info, doctor info, and dispense controls.
    """
    if request.user.role != 'PHARMACIST':
        return redirect('dashboard')

    prescription = get_object_or_404(
        Prescription.objects
        .select_related('patient', 'doctor', 'visit', 'appointment')
        .prefetch_related('items'),
        pk=pk,
    )

    return render(request, 'prescriptions/pharmacist_prescription_detail.html', {
        'rx': prescription,
        'items': prescription.items.all(),
        'pending_count': Prescription.objects.filter(dispense_status='PENDING').count(),
    })


@require_POST
@login_required
def dispense_prescription(request, pk):
    """
    Pharmacist: flip a prescription from PENDING → DISPENSED.
    Records who dispensed it and when, and writes an audit log entry.
    """
    if request.user.role != 'PHARMACIST':
        return redirect('dashboard')

    prescription = get_object_or_404(Prescription, pk=pk)

    if prescription.dispense_status == Prescription.DISPENSE_DISPENSED:
        messages.warning(request, "Prescription was already marked as dispensed.")
    else:
        prescription.dispense_status = Prescription.DISPENSE_DISPENSED
        prescription.dispensed_at = timezone.now()
        prescription.save(update_fields=['dispense_status', 'dispensed_at'])

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Prescription',
            entity_id=prescription.pk,
            changes={
                'action': 'dispense',
                'patient': str(prescription.patient),
                'dispensed_at': prescription.dispensed_at.isoformat(),
            },
        )

        messages.success(
            request,
            f"Prescription #{prescription.pk} for "
            f"{prescription.patient} marked as dispensed.",
        )

    # If request came from the detail page, go back there
    next_url = request.POST.get('next', '')
    if next_url and 'detail' in next_url:
        return redirect('pharmacist_prescription_detail', pk=pk)
    return redirect('pharmacist_prescriptions')
