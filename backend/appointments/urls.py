from django.urls import path
from .views import (
    book_appointment,
    doctor_appointment_detail,
    doctor_appointments,
    doctor_unavailability,
    delete_doctor_unavailability,
    get_available_slots,
)

urlpatterns = [
    path('book/', book_appointment, name='book_appointment'),
    path('api/slots/', get_available_slots, name='api_available_slots'),
    path('doctor/', doctor_appointments, name='doctor_appointments'),
    path('doctor/<int:appointment_id>/', doctor_appointment_detail, name='doctor_appointment_detail'),
    path('doctor/unavailability/', doctor_unavailability, name='doctor_unavailability'),
    path(
        'doctor/unavailability/<int:block_id>/delete/',
        delete_doctor_unavailability,
        name='delete_doctor_unavailability',
    ),
]
