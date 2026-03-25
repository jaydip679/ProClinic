from rest_framework import viewsets
from appointments.models import Appointment
from prescriptions.models import Prescription
from billing.models import Invoice
from publications.models import Publication
from .serializers import (
    AppointmentSerializer, 
    PrescriptionSerializer, 
    InvoiceSerializer, 
    PublicationSerializer
)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

class PublicationViewSet(viewsets.ModelViewSet):
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer