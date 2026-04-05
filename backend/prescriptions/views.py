from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PrescriptionForm, MedicineFormSet


@login_required
def create_prescription(request):
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

            messages.success(request, "Prescription issued successfully.")
            return redirect('doctor_appointments')
    else:
        form = PrescriptionForm(doctor=request.user)
        formset = MedicineFormSet()

    return render(request, 'prescriptions/create_prescription.html', {
        'form': form,
        'formset': formset,
    })

