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
            prescription.doctor = request.user
            if prescription.appointment.doctor_id != request.user.id:
                form.add_error('appointment', 'You can only prescribe for your own appointments.')
                return render(request, 'prescriptions/create_prescription.html', {
                    'form': form,
                    'formset': formset
                })
            prescription.save()
            
            formset.instance = prescription
            formset.save()
            prescription.appointment.status = 'COMPLETED'
            prescription.appointment.save(update_fields=['status'])
            messages.success(request, "Prescription issued and appointment marked completed.")
            return redirect('doctor_appointments')
    else:
        form = PrescriptionForm(doctor=request.user)
        formset = MedicineFormSet()
        
    return render(request, 'prescriptions/create_prescription.html', {
        'form': form,
        'formset': formset
    })
