"""Patient-facing API URL configuration."""

from django.urls import path

from .patient_views import (
    PatientAppointmentCancelView,
    PatientAppointmentListCreateView,
    PatientAppointmentRescheduleView,
    PatientInvoiceListView,
    PatientLabReportListCreateView,
    PatientPrescriptionDetailView,
    PatientPrescriptionListView,
    PatientProfileView,
    PatientVisitListView,
)

urlpatterns = [
    # Profile
    path('profile/', PatientProfileView.as_view(), name='patient_api_profile'),

    # EHR / Visits
    path('visits/', PatientVisitListView.as_view(), name='patient_api_visits'),

    # Appointments
    path('appointments/', PatientAppointmentListCreateView.as_view(), name='patient_api_appointments'),
    path(
        'appointments/<int:appointment_id>/reschedule/',
        PatientAppointmentRescheduleView.as_view(),
        name='patient_api_appointment_reschedule',
    ),
    path(
        'appointments/<int:appointment_id>/cancel/',
        PatientAppointmentCancelView.as_view(),
        name='patient_api_appointment_cancel',
    ),

    # Prescriptions
    path('prescriptions/', PatientPrescriptionListView.as_view(), name='patient_api_prescriptions'),
    path('prescriptions/<int:pk>/', PatientPrescriptionDetailView.as_view(), name='patient_api_prescription_detail'),

    # Invoices
    path('invoices/', PatientInvoiceListView.as_view(), name='patient_api_invoices'),

    # Lab Reports
    path('lab-reports/', PatientLabReportListCreateView.as_view(), name='patient_api_lab_reports'),
]
