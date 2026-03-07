from rest_framework import viewsets
from .models import Patient
from .serializers import PatientSerializer
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

@login_required
def patient_list(request):
    if request.user.role not in {'ADMIN', 'RECEPTIONIST'}:
        return redirect('dashboard')
    patients = Patient.objects.all().order_by('first_name', 'last_name')
    return render(request, 'patients/patient_list.html', {'patients': patients})

@login_required
def patient_detail(request, pk):
    if request.user.role not in {'ADMIN', 'DOCTOR', 'RECEPTIONIST'}:
        return redirect('dashboard')
    # This function now correctly uses get_object_or_404
    patient = get_object_or_404(Patient, pk=pk)

    if request.user.role == 'DOCTOR':
        has_access = patient.appointments.filter(doctor=request.user).exists()
        if not has_access:
            return redirect('dashboard')
    
    # Fetching related data through Reverse Relations
    appointments = patient.appointments.all().order_by('-scheduled_time')
    prescriptions = patient.prescriptions.all().order_by('-created_at')
    invoices = patient.invoices.all().order_by('-created_at')
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'prescriptions': prescriptions,
        'invoices': invoices,
    }
    return render(request, 'patients/patient_detail.html', context)
