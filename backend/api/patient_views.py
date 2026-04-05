"""
Patient-facing API views.

Every view enforces:
  1. IsAuthenticated (from DRF default)
  2. IsPatient (role check)
  3. Object-level ownership (patient can only see/modify own data)
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, parsers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment, DoctorUnavailability
from audit.utils import log_action
from billing.models import Invoice
from patients.models import LabReport, Patient, Visit
from prescriptions.models import Prescription

from .patient_serializers import (
    LabReportSerializer,
    PatientAppointmentBookSerializer,
    PatientAppointmentRescheduleSerializer,
    PatientAppointmentSerializer,
    PatientInvoiceSerializer,
    PatientPrescriptionSerializer,
    PatientProfileSerializer,
    PatientVisitSerializer,
)
from .permissions import IsPatient


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_patient_for_user(user):
    """Return the Patient record linked to the authenticated user.

    Tries the direct FK first, then falls back to legacy email/phone matching.
    """
    # Direct FK lookup
    patient = getattr(user, 'patient_profile', None)
    if patient is not None:
        return patient

    # Legacy fallback
    patient = Patient.objects.filter(
        Q(email=user.email) | Q(contact_number=user.phone_number)
    ).first()

    # Repair: attach FK for future lookups
    if patient and patient.user_id is None:
        patient.user = user
        patient.save(update_fields=['user'])

    return patient


def _require_patient(user):
    """Return Patient or raise 404."""
    patient = _get_patient_for_user(user)
    if patient is None:
        raise NotFound("Patient profile not found. Please contact reception.")
    return patient


# ─── Profile ──────────────────────────────────────────────────────────────────

class PatientProfileView(APIView):
    """GET / PUT own patient profile."""
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        patient = _require_patient(request.user)
        serializer = PatientProfileSerializer(patient)
        return Response(serializer.data)

    def put(self, request):
        patient = _require_patient(request.user)
        serializer = PatientProfileSerializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Patient',
            entity_id=patient.pk,
            changes={'updated_fields': list(serializer.validated_data.keys())},
        )
        return Response(serializer.data)

    # Support PATCH as alias for partial update
    def patch(self, request):
        return self.put(request)


# ─── Visits / EHR ────────────────────────────────────────────────────────────

class PatientVisitListView(generics.ListAPIView):
    """GET own visit history (newest first)."""
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = PatientVisitSerializer

    def get_queryset(self):
        patient = _require_patient(self.request.user)
        return Visit.objects.filter(patient=patient).select_related('doctor').order_by('-visit_date')


# ─── Appointments ─────────────────────────────────────────────────────────────

class PatientAppointmentListCreateView(APIView):
    """
    GET  — list own appointments (supports ?status=upcoming|past).
    POST — book a new appointment.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        patient = _require_patient(request.user)
        qs = Appointment.objects.filter(patient=patient).select_related('doctor').order_by('-scheduled_time')

        status_filter = request.query_params.get('status')
        now = timezone.now()
        if status_filter == 'upcoming':
            qs = qs.filter(scheduled_time__gte=now, status='SCHEDULED')
        elif status_filter == 'past':
            qs = qs.filter(Q(scheduled_time__lt=now) | ~Q(status='SCHEDULED'))

        serializer = PatientAppointmentSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        patient = _require_patient(request.user)
        serializer = PatientAppointmentBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment = Appointment(
            patient=patient,
            doctor=serializer.validated_data['doctor'],
            scheduled_time=serializer.validated_data['scheduled_time'],
            reason=serializer.validated_data.get('reason', ''),
            created_by=request.user,
        )

        try:
            appointment.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)

        appointment.save()

        log_action(
            actor=request.user,
            action_type='CREATE',
            entity_type='Appointment',
            entity_id=appointment.pk,
            changes={
                'doctor_id': appointment.doctor_id,
                'scheduled_time': str(appointment.scheduled_time),
            },
        )
        return Response(
            PatientAppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class PatientAppointmentRescheduleView(APIView):
    """PUT — reschedule own appointment to a new time (and optionally new doctor)."""
    permission_classes = [IsAuthenticated, IsPatient]

    def put(self, request, appointment_id):
        patient = _require_patient(request.user)
        appointment = self._get_own_appointment(patient, appointment_id)

        if appointment.status != 'SCHEDULED':
            raise ValidationError(
                {"status": "Only SCHEDULED appointments can be rescheduled."},
            )

        serializer = PatientAppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_time = appointment.scheduled_time
        old_doctor_id = appointment.doctor_id

        appointment.scheduled_time = serializer.validated_data['scheduled_time']
        if 'doctor' in serializer.validated_data:
            appointment.doctor = serializer.validated_data['doctor']

        try:
            appointment.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict)

        appointment.save()

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Appointment',
            entity_id=appointment.pk,
            changes={
                'action': 'reschedule',
                'old_time': str(old_time),
                'new_time': str(appointment.scheduled_time),
                'old_doctor_id': old_doctor_id,
                'new_doctor_id': appointment.doctor_id,
            },
        )
        return Response(PatientAppointmentSerializer(appointment).data)

    @staticmethod
    def _get_own_appointment(patient, appointment_id):
        try:
            return Appointment.objects.select_related('doctor').get(
                pk=appointment_id, patient=patient,
            )
        except Appointment.DoesNotExist:
            raise NotFound("Appointment not found.")


class PatientAppointmentCancelView(APIView):
    """POST — cancel own appointment.

    Accepts an optional JSON body: {"reason": "..."}
    """
    permission_classes = [IsAuthenticated, IsPatient]

    def post(self, request, appointment_id):
        patient = _require_patient(request.user)
        try:
            appointment = Appointment.objects.get(pk=appointment_id, patient=patient)
        except Appointment.DoesNotExist:
            raise NotFound("Appointment not found.")

        if not appointment.is_cancellable:
            raise ValidationError(
                {"status": f"Cannot cancel an appointment with status '{appointment.get_status_display()}'."},
            )

        reason = request.data.get('reason', '')
        appointment.cancel(user=request.user, reason=reason)

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Appointment',
            entity_id=appointment.pk,
            changes={
                'action': 'cancel',
                'old_status': 'SCHEDULED',
                'new_status': 'CANCELLED',
                'reason': reason,
            },
        )
        return Response(
            {"detail": "Appointment cancelled."},
            status=status.HTTP_200_OK,
        )



# ─── Prescriptions ───────────────────────────────────────────────────────────

class PatientPrescriptionListView(generics.ListAPIView):
    """GET own prescriptions (read-only)."""
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = PatientPrescriptionSerializer

    def get_queryset(self):
        patient = _require_patient(self.request.user)
        return (
            Prescription.objects.filter(patient=patient)
            .select_related('doctor')
            .prefetch_related('items')
            .order_by('-created_at')
        )


class PatientPrescriptionDetailView(generics.RetrieveAPIView):
    """GET single prescription detail (read-only)."""
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = PatientPrescriptionSerializer

    def get_object(self):
        patient = _require_patient(self.request.user)
        try:
            return (
                Prescription.objects.filter(patient=patient)
                .select_related('doctor')
                .prefetch_related('items')
                .get(pk=self.kwargs['pk'])
            )
        except Prescription.DoesNotExist:
            raise NotFound("Prescription not found.")


# ─── Invoices ─────────────────────────────────────────────────────────────────

class PatientInvoiceListView(generics.ListAPIView):
    """GET own invoices (read-only)."""
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = PatientInvoiceSerializer

    def get_queryset(self):
        patient = _require_patient(self.request.user)
        return (
            Invoice.objects.filter(patient=patient)
            .prefetch_related('items')
            .order_by('-created_at')
        )


# ─── Lab Reports ─────────────────────────────────────────────────────────────

class PatientLabReportListCreateView(APIView):
    """
    GET  — list own lab reports.
    POST — upload a new lab report (multipart/form-data).
    """
    permission_classes = [IsAuthenticated, IsPatient]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get(self, request):
        patient = _require_patient(request.user)
        reports = LabReport.objects.filter(patient=patient)
        serializer = LabReportSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        patient = _require_patient(request.user)
        serializer = LabReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(patient=patient, uploaded_by=request.user)

        log_action(
            actor=request.user,
            action_type='CREATE',
            entity_type='LabReport',
            entity_id=report.pk,
            changes={'test_name': report.test_name, 'filename': report.pdf_file.name},
        )
        return Response(
            LabReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )
