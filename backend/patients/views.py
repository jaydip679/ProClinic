from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from api.filters import PatientFilter
from api.pagination import StandardResultsSetPagination
from api.permissions import IsStaff

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    Staff-facing patient management.

    Filtering:  ?first_name=  ?last_name=  ?blood_group=  ?gender=
    Search:     ?search=  (first_name, last_name, contact_number, email)
    Ordering:   ?ordering=first_name | last_name | created_at
    Pagination: ?page=  ?page_size=  (default 20, max 100)
    """
    queryset = Patient.objects.all().order_by('last_name', 'first_name')
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PatientFilter
    search_fields = ['first_name', 'last_name', 'contact_number', 'email']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    ordering = ['last_name', 'first_name']


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
