from rest_framework import serializers
from appointments.models import Appointment
from prescriptions.models import Prescription, PrescriptionItem
from billing.models import Invoice, InvoiceItem
from publications.models import Publication

# Appointment Serializer
class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'

# Prescription Serializers
class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = '__all__'

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    class Meta:
        model = Prescription
        fields = '__all__'

# Billing Serializers
class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    class Meta:
        model = Invoice
        fields = '__all__'

# Publication Serializer
class PublicationSerializer(serializers.ModelSerializer):
    doctor_name   = serializers.CharField(source='doctor.get_full_name', read_only=True)
    approver_name = serializers.SerializerMethodField(read_only=True)
    status_label  = serializers.CharField(source='get_status_display', read_only=True)
    is_public     = serializers.BooleanField(read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'doctor', 'doctor_name',
            'title', 'abstract', 'authors', 'pdf_file',
            'status', 'status_label', 'is_public',
            'admin_notes', 'rejection_reason',
            'approved_by', 'approver_name', 'approved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'status', 'approved_by', 'approved_at',
            'doctor_name', 'approver_name', 'status_label', 'is_public',
        ]

    def get_approver_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None


class PublicPublicationSerializer(serializers.ModelSerializer):
    """Minimal serializer for unauthenticated public listing."""
    doctor_name  = serializers.CharField(source='doctor.get_full_name', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Publication
        fields = [
            'id', 'title', 'abstract', 'authors',
            'doctor_name', 'pdf_file',
            'approved_at', 'status_label',
        ]


# ── Audit Serializer ──────────────────────────────────────────────────────────

from audit.models import AuditLog  # noqa: E402 — avoids circular import at top


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for AuditLog. ADMIN-only via AuditLogViewSet."""
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    actor_email    = serializers.EmailField(source='actor.email',    read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor', 'actor_username', 'actor_email',
            'action_type',
            'entity_type', 'entity_id',
            'changes',
            'timestamp',
        ]