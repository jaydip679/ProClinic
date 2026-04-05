from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from appointments.models import Appointment
from billing.models import Invoice
from patients.models import LabReport, Patient
from prescriptions.models import Prescription
from publications.models import Publication

from .filters import (
    AppointmentFilter,
    InvoiceFilter,
    LabReportFilter,
    PatientFilter,
    PrescriptionFilter,
    PublicationFilter,
)
from .pagination import LargeResultsSetPagination, StandardResultsSetPagination
from .permissions import IsStaff
from .serializers import (
    AppointmentSerializer,
    InvoiceSerializer,
    PrescriptionSerializer,
    PublicationSerializer,
)

# Import PatientViewSet from patients app (registered separately in urls.py)
from patients.views import PatientViewSet  # noqa: F401 – re-exported for router


# ─── Appointments ─────────────────────────────────────────────────────────────

class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Staff-facing appointment management.

    Filtering:  ?status=  ?doctor_id=  ?patient_id=  ?date=  ?date_from=  ?date_to=
    Search:     ?search=  (patient name, doctor name)
    Ordering:   ?ordering=scheduled_time | -scheduled_time | status | created_at
    Pagination: ?page=  ?page_size=  (default 20, max 100)
    """
    queryset = Appointment.objects.select_related(
        'patient', 'doctor', 'created_by', 'cancelled_by',
    ).order_by('-scheduled_time')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AppointmentFilter
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
        'reason',
    ]
    ordering_fields = ['scheduled_time', 'status', 'created_at']
    ordering = ['-scheduled_time']

    # ── Cancel action ─────────────────────────────────────────────────────────

    @action(detail=True, methods=['post', 'patch'])
    def cancel(self, request, pk=None):
        """POST /api/appointments/{id}/cancel/  — cancel with optional reason."""
        appointment = self.get_object()

        if not appointment.is_cancellable:
            return Response(
                {"detail": f"Cannot cancel an appointment with status '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason', '')
        appointment.cancel(user=request.user, reason=reason)

        return Response(self.get_serializer(appointment).data, status=status.HTTP_200_OK)

    # ── Reschedule action ─────────────────────────────────────────────────────

    @action(detail=True, methods=['post', 'patch'])
    def reschedule(self, request, pk=None):
        """POST /api/appointments/{id}/reschedule/  — body: {new_time: <iso8601>}."""
        appointment = self.get_object()

        if appointment.status in ['COMPLETED', 'CANCELLED']:
            return Response(
                {"detail": f"Cannot reschedule an appointment with status '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_time_str = request.data.get('new_time')
        if not new_time_str:
            return Response({"new_time": "New time is required."}, status=status.HTTP_400_BAD_REQUEST)

        parsed_time = parse_datetime(new_time_str)
        if not parsed_time:
            return Response({"new_time": "Invalid datetime format. Use ISO 8601."}, status=status.HTTP_400_BAD_REQUEST)

        appointment.reschedule(parsed_time)
        return Response(self.get_serializer(appointment).data, status=status.HTTP_200_OK)


# ─── Prescriptions ────────────────────────────────────────────────────────────

class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    Staff-facing prescription management.

    Filtering:  ?patient_id=  ?doctor_id=  ?created_from=  ?created_to=
    Search:     ?search=  (patient name, doctor name, medicine name)
    Ordering:   ?ordering=created_at | -created_at
    Pagination: ?page=  ?page_size=
    """
    queryset = Prescription.objects.select_related(
        'patient', 'doctor', 'visit', 'appointment',
    ).prefetch_related('items').order_by('-created_at')
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PrescriptionFilter
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
        'items__medicine_name',
    ]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    # ── PDF actions ───────────────────────────────────────────────────────────

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """GET /api/prescriptions/{id}/pdf/ — download as PDF."""
        from prescriptions.utils import prescription_pdf_response
        prescription = self.get_object()
        try:
            return prescription_pdf_response(prescription)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='html-preview')
    def html_preview(self, request, pk=None):
        """GET /api/prescriptions/{id}/html-preview/ — preview template HTML."""
        from django.http import HttpResponse
        from prescriptions.utils import render_prescription_html
        prescription = self.get_object()
        return HttpResponse(render_prescription_html(prescription), content_type='text/html')


# ─── Invoices ─────────────────────────────────────────────────────────────────

class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Staff-facing invoice management.

    Filtering:  ?patient_id=  ?status=  ?created_from=  ?created_to=
    Search:     ?search=  (patient name, service name)
    Ordering:   ?ordering=created_at | -created_at | total_amount
    Pagination: ?page=  ?page_size=
    """
    queryset = Invoice.objects.select_related('patient').prefetch_related('items').order_by('-created_at')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InvoiceFilter
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'items__service_name',
    ]
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']


# ─── Publications ─────────────────────────────────────────────────────────────

class PublicationViewSet(viewsets.ModelViewSet):
    """
    Research publication management.

    Filtering:  ?authors=  ?status=  ?year=
    Search:     ?search=  (title, authors, abstract)
    Ordering:   ?ordering=created_at | -created_at | title
    Pagination: ?page=  ?page_size=  (default 50, max 200)
    """
    queryset = Publication.objects.all().order_by('-created_at')
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = LargeResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PublicationFilter
    search_fields = ['title', 'authors', 'abstract']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
