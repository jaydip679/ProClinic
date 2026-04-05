"""
Serializers used exclusively by the patient-facing API endpoints.
"""

from rest_framework import serializers

from appointments.models import Appointment, DoctorUnavailability
from billing.models import Invoice, InvoiceItem
from patients.models import LabReport, Patient, Visit
from prescriptions.models import Prescription, PrescriptionItem


# ─── Profile ───────────────────────────────────────────────────────────────────

class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'blood_group', 'contact_number', 'email', 'address', 'allergies',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ─── Visits / EHR ─────────────────────────────────────────────────────────────

class PatientVisitSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = [
            'id', 'doctor', 'doctor_name', 'appointment', 'visit_date',
            'notes', 'diagnosis', 'created_at',
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username


# ─── Appointments ──────────────────────────────────────────────────────────────

class PatientAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'scheduled_time', 'reason',
            'status', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username


class PatientAppointmentBookSerializer(serializers.ModelSerializer):
    """Used when a patient books a new appointment."""

    class Meta:
        model = Appointment
        fields = ['doctor', 'scheduled_time', 'reason']

    def validate_doctor(self, value):
        if value.role != 'DOCTOR':
            raise serializers.ValidationError("Selected user is not a doctor.")
        return value


class PatientAppointmentRescheduleSerializer(serializers.Serializer):
    """Used when a patient reschedules an existing appointment."""
    scheduled_time = serializers.DateTimeField()
    doctor = serializers.IntegerField(required=False)

    def validate_doctor(self, value):
        from accounts.models import CustomUser
        try:
            doctor = CustomUser.objects.get(pk=value, role='DOCTOR', is_active=True)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Selected doctor does not exist or is inactive.")
        return doctor


# ─── Prescriptions ────────────────────────────────────────────────────────────

class PatientPrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ['id', 'medicine_name', 'dosage', 'instructions', 'duration']


class PatientPrescriptionSerializer(serializers.ModelSerializer):
    items = PatientPrescriptionItemSerializer(many=True, read_only=True)
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'doctor', 'doctor_name', 'visit', 'appointment',
            'pdf_file', 'created_at', 'items',
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username


# ─── Billing / Invoices ───────────────────────────────────────────────────────

class PatientInvoiceItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ['id', 'service_name', 'unit_cost', 'quantity', 'line_total']


class PatientInvoiceSerializer(serializers.ModelSerializer):
    items = PatientInvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'appointment', 'total_amount', 'status',
            'created_at', 'updated_at', 'items',
        ]


# ─── Lab Reports ──────────────────────────────────────────────────────────────

class LabReportSerializer(serializers.ModelSerializer):
    """Serializer for patient-facing lab report access and upload."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LabReport
        fields = [
            'id',
            'test_name',
            'report_date',
            'pdf_file',
            'status',
            'status_display',
            'uploaded_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'status_display', 'uploaded_at', 'updated_at']
