from django.urls import path
from .views import (
    create_prescription,
    pharmacist_prescription_list,
    pharmacist_prescription_detail,
    dispense_prescription,
)

urlpatterns = [
    # Doctor
    path('add/', create_prescription, name='create_prescription'),

    # Pharmacist
    path('dispense/', pharmacist_prescription_list, name='pharmacist_prescriptions'),
    path('dispense/<int:pk>/', pharmacist_prescription_detail, name='pharmacist_prescription_detail'),
    path('dispense/<int:pk>/mark-dispensed/', dispense_prescription, name='dispense_prescription'),
]