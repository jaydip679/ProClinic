"""
api/filters.py
──────────────
django-filter FilterSet definitions for all staff-facing API viewsets.
"""
import django_filters
from django_filters import rest_framework as filters

from appointments.models import Appointment
from billing.models import Invoice
from patients.models import LabReport, Patient
from prescriptions.models import Prescription
from publications.models import Publication


class PatientFilter(filters.FilterSet):
    """
    Supported query params:
      ?first_name=<str>     — case-insensitive partial match on first name
      ?last_name=<str>      — case-insensitive partial match on last name
      ?blood_group=<str>    — exact match (e.g. A+, O-)
      ?gender=<str>         — exact match (Male | Female | Other)
    """
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name  = django_filters.CharFilter(lookup_expr='icontains')
    blood_group = django_filters.CharFilter(lookup_expr='iexact')
    gender = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'blood_group', 'gender']


class AppointmentFilter(filters.FilterSet):
    """
    Supported query params:
      ?status=SCHEDULED|COMPLETED|CANCELLED|NOSHOW|RESCHEDULED
      ?doctor_id=<int>
      ?patient_id=<int>
      ?date=YYYY-MM-DD          — appointments on this exact calendar day
      ?date_from=YYYY-MM-DD     — appointments on or after this date
      ?date_to=YYYY-MM-DD       — appointments on or before this date
    """
    status     = django_filters.CharFilter(lookup_expr='iexact')
    doctor_id  = django_filters.NumberFilter(field_name='doctor__id')
    patient_id = django_filters.NumberFilter(field_name='patient__id')

    # Date helpers — filter against the date part of scheduled_time
    date      = django_filters.DateFilter(field_name='scheduled_time', lookup_expr='date')
    date_from = django_filters.DateFilter(field_name='scheduled_time', lookup_expr='date__gte')
    date_to   = django_filters.DateFilter(field_name='scheduled_time', lookup_expr='date__lte')

    class Meta:
        model = Appointment
        fields = ['status', 'doctor_id', 'patient_id', 'date', 'date_from', 'date_to']


class PrescriptionFilter(filters.FilterSet):
    """
    Supported query params:
      ?patient_id=<int>
      ?doctor_id=<int>
      ?created_from=YYYY-MM-DD
      ?created_to=YYYY-MM-DD
    """
    patient_id   = django_filters.NumberFilter(field_name='patient__id')
    doctor_id    = django_filters.NumberFilter(field_name='doctor__id')
    created_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_to   = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = Prescription
        fields = ['patient_id', 'doctor_id', 'created_from', 'created_to']


class LabReportFilter(filters.FilterSet):
    """
    Supported query params:
      ?patient_id=<int>
      ?status=pending|verified|archived
      ?report_date_from=YYYY-MM-DD
      ?report_date_to=YYYY-MM-DD
    """
    patient_id       = django_filters.NumberFilter(field_name='patient__id')
    status           = django_filters.CharFilter(lookup_expr='iexact')
    report_date_from = django_filters.DateFilter(field_name='report_date', lookup_expr='gte')
    report_date_to   = django_filters.DateFilter(field_name='report_date', lookup_expr='lte')

    class Meta:
        model = LabReport
        fields = ['patient_id', 'status', 'report_date_from', 'report_date_to']


class InvoiceFilter(filters.FilterSet):
    """
    Supported query params:
      ?patient_id=<int>
      ?status=UNPAID|PAID|CANCELLED
      ?created_from=YYYY-MM-DD
      ?created_to=YYYY-MM-DD
    """
    patient_id   = django_filters.NumberFilter(field_name='patient__id')
    status       = django_filters.CharFilter(lookup_expr='iexact')
    created_from = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_to   = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = Invoice
        fields = ['patient_id', 'status', 'created_from', 'created_to']


class PublicationFilter(filters.FilterSet):
    """
    Supported query params:
      ?authors=<str>    — case-insensitive partial match
      ?status=<str>     — exact match (e.g. PUBLISHED, DRAFT)
      ?year=<int>       — year of creation
    """
    authors = django_filters.CharFilter(lookup_expr='icontains')
    status  = django_filters.CharFilter(lookup_expr='iexact')
    year    = django_filters.NumberFilter(field_name='created_at', lookup_expr='year')

    class Meta:
        model = Publication
        fields = ['authors', 'status', 'year']
