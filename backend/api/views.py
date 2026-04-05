from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils.dateparse import parse_datetime


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
from .permissions import IsStaff


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsStaff]

    @action(detail=True, methods=['post', 'patch'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        
        if not appointment.is_cancellable:
            return Response(
                {"detail": f"Cannot cancel an appointment with status '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        reason = request.data.get('reason', '')
        appointment.cancel(user=request.user, reason=reason)
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'patch'])
    def reschedule(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.status in ['COMPLETED', 'CANCELLED']:
            return Response(
                {"detail": f"Cannot reschedule an appointment with status '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        new_time_str = request.data.get('new_time')
        if not new_time_str:
            return Response({"new_time": "New time is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        parsed_time = parse_datetime(new_time_str)
        if not parsed_time:
            return Response({"new_time": "Invalid datetime format."}, status=status.HTTP_400_BAD_REQUEST)
            
        appointment.reschedule(parsed_time)
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, IsStaff]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsStaff]


class PublicationViewSet(viewsets.ModelViewSet):
    queryset = Publication.objects.all()
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated, IsStaff]