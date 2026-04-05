from django.urls import path
from .views import generate_invoice, patient_invoices

urlpatterns = [
    path('new/', generate_invoice, name='generate_invoice'),
    path('my-invoices/', patient_invoices, name='patient_invoices'),
]