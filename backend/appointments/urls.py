from django.urls import path
from .views import (
    book_appointment,
    doctor_appointment_detail,
    doctor_appointments,
    doctor_unavailability,
    delete_doctor_unavailability,
    get_available_slots,
    receptionist_appointments,
    receptionist_cancel_appointment,
    receptionist_reschedule_appointment,
    receptionist_mark_noshow,
    receptionist_checkin_appointment,
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
    # Receptionist / Admin appointment management
    path('manage/', receptionist_appointments, name='receptionist_appointments'),
    path('manage/<int:pk>/cancel/', receptionist_cancel_appointment, name='receptionist_cancel_appointment'),
    path('manage/<int:pk>/reschedule/', receptionist_reschedule_appointment, name='receptionist_reschedule_appointment'),
    path('manage/<int:pk>/noshow/', receptionist_mark_noshow, name='receptionist_mark_noshow'),
    path('manage/<int:pk>/checkin/', receptionist_checkin_appointment, name='receptionist_checkin_appointment'),
]
