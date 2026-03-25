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
    class Meta:
        model = Publication
        fields = '__all__'